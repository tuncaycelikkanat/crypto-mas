from fastapi import APIRouter

from crypto_mas.apps.api.routers.analytics import router as analytics_router
from crypto_mas.apps.api.routers.backtest import router as backtest_router
from crypto_mas.apps.api.routers.bot import router as bot_router
from crypto_mas.apps.api.routers.cycle import router as cycle_router
from crypto_mas.apps.api.routers.decision import router as decision_router
from crypto_mas.apps.api.routers.features import router as features_router
from crypto_mas.apps.api.routers.health import router as health_router
from crypto_mas.apps.api.routers.logs import router as logs_router
from crypto_mas.apps.api.routers.market import router as market_router
from crypto_mas.apps.api.routers.paper import router as paper_router
from crypto_mas.apps.api.routers.portfolio import router as portfolio_router
from crypto_mas.apps.api.routers.risk import router as risk_router
from crypto_mas.apps.api.routers.scanner import router as scanner_router
from crypto_mas.apps.api.routers.signals import router as signals_router

__all__ = [
    "health_router",
    "market_router",
    "features_router",
    "signals_router",
    "decision_router",
    "portfolio_router",
    "risk_router",
    "paper_router",
    "cycle_router",
    "backtest_router",
    "bot_router",
    "logs_router",
    "analytics_router",
    "scanner_router",
]
