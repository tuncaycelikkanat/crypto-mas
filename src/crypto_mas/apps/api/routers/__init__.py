from fastapi import APIRouter

from crypto_mas.apps.api.routers.health import router as health_router
from crypto_mas.apps.api.routers.market import router as market_router
from crypto_mas.apps.api.routers.features import router as features_router
from crypto_mas.apps.api.routers.signals import router as signals_router
from crypto_mas.apps.api.routers.decision import router as decision_router
from crypto_mas.apps.api.routers.portfolio import router as portfolio_router
from crypto_mas.apps.api.routers.risk import router as risk_router
from crypto_mas.apps.api.routers.paper import router as paper_router
from crypto_mas.apps.api.routers.cycle import router as cycle_router

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
]
