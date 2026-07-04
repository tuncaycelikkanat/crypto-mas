from contextlib import asynccontextmanager

from fastapi import FastAPI

from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.domain.models.config_version import ConfigVersion
from crypto_mas.services.config_service.config_service import ConfigService
from crypto_mas.services.config_service.schemas import TradingConfig
from crypto_mas.apps.api.routers import (
    health_router,
    market_router,
    features_router,
    signals_router,
    decision_router,
    portfolio_router,
    risk_router,
    paper_router,
)

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
            config_service.repository.add(new_version)
            db.commit()

    yield
    # Shutdown
    pass

app = FastAPI(
    title="Crypto MAS API",
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(market_router)
app.include_router(features_router)
app.include_router(signals_router)
app.include_router(decision_router)
app.include_router(portfolio_router)
app.include_router(risk_router)
app.include_router(paper_router)

