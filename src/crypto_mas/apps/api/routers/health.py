from fastapi import APIRouter
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import check_db_connection
from crypto_mas.infrastructure.cache.redis_client import check_redis_connection

settings = get_settings()
router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "env": settings.app_env,
        "mode": settings.trading_mode,
    }

@router.get("/health/db")
def database_health_check() -> dict[str, str]:
    is_connected = check_db_connection()
    return {
        "status": "ok" if is_connected else "error",
        "database": "connected" if is_connected else "disconnected",
    }

@router.get("/health/redis")
def redis_health_check() -> dict[str, str]:
    is_connected = check_redis_connection()
    return {
        "status": "ok" if is_connected else "error",
        "redis": "connected" if is_connected else "disconnected",
    }

@router.get("/version")
def version() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
    }

@router.get("/config")
def config() -> dict[str, str]:
    return {
        "app_env": settings.app_env,
        "trading_mode": settings.trading_mode,
        "log_level": settings.log_level,
    }
