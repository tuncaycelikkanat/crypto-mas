import asyncio
from contextlib import asynccontextmanager

import uvloop
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from crypto_mas.apps.api.routers import (
    analytics_router,
    audit_router,
    backtest_router,
    bot_router,
    cycle_router,
    decision_router,
    features_router,
    health_router,
    logs_router,
    market_router,
    optimization_router,
    paper_router,
    portfolio_router,
    risk_router,
    scanner_router,
    signals_router,
    ws_risk_router,
)
from crypto_mas.domain.models.config_version import ConfigVersion
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.infrastructure.logging.setup import setup_logging
from crypto_mas.services.config_service.config_service import ConfigService
from crypto_mas.services.config_service.schemas import TradingConfig
from crypto_mas.services.scheduler_service import SchedulerService
from crypto_mas.services.alerting.telegram_bot import TelegramService
from crypto_mas.infrastructure.db.async_compat import run_sync

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
setup_logging(env="dev")  # Production'da env var'dan okunabilir

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed default config if not exists
    with SessionLocal() as db:
        config_service = ConfigService(db)
        existing = config_service.get_config("system_default")
        
        if not existing:
            default_config = TradingConfig()
            new_version = ConfigVersion(
                name="system_default",
                version="1.0.0",
                config_json=default_config.model_dump(mode="json"),
                is_active=True,
                notes="System default configuration",
            )
            await run_sync(config_service.repository.add, new_version)
            await run_sync(db.commit)

    # Start Scheduler
    scheduler_service = SchedulerService()
    app.state.scheduler = scheduler_service
    scheduler_service.start()

    # Start Order Execution Queue Worker (New Fix)
    from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
    from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
    queue = OrderExecutorQueue.get_instance()
    def broker_factory(strategy_mode: str = "swing"):
        db = SessionLocal()
        return PaperBrokerService(db=db, strategy_mode=strategy_mode)
    queue.set_broker_factory(broker_factory)
    queue.start()

    # Start Telegram Bot & Command Center
    telegram_service = TelegramService(
        token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    app.state.telegram = telegram_service
    if settings.telegram_enabled or (settings.telegram_bot_token and settings.telegram_chat_id):
        await telegram_service.start_polling(app.state)

    yield
    # Shutdown
    telegram_service.stop_polling()
    scheduler_service.shutdown()
    queue.stop()

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(
    title="Crypto MAS API",
    version=settings.app_version,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(market_router)
app.include_router(features_router)
app.include_router(signals_router)
app.include_router(decision_router)
app.include_router(portfolio_router)
app.include_router(risk_router)
app.include_router(paper_router)
app.include_router(optimization_router)
app.include_router(cycle_router)
app.include_router(backtest_router)
app.include_router(bot_router)
app.include_router(logs_router)
app.include_router(analytics_router)
app.include_router(scanner_router)
app.include_router(audit_router)
app.include_router(ws_risk_router)

# Mount frontend static files
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../frontend/dist"))

if os.path.exists(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        # Serve API routes normally, fallback others to index.html for React Router
        if full_path.startswith("api/"):
            return None
            
        file_path = os.path.join(frontend_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        return FileResponse(os.path.join(frontend_dir, "index.html"))
