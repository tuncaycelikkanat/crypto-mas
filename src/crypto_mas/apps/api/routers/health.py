from fastapi import APIRouter

from crypto_mas.infrastructure.cache.redis_client import check_redis_connection
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import check_db_connection

settings = get_settings()
router = APIRouter(prefix="/api/v1", tags=["Health"])

@router.api_route("/health", methods=["GET", "HEAD"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "env": settings.app_env,
        "mode": settings.trading_mode,
    }

@router.api_route("/health/db", methods=["GET", "HEAD"])
def database_health_check() -> dict[str, str]:
    is_connected = check_db_connection()
    return {
        "status": "ok" if is_connected else "error",
        "database": "connected" if is_connected else "disconnected",
    }

@router.api_route("/health/redis", methods=["GET", "HEAD"])
def redis_health_check() -> dict[str, str]:
    is_connected = check_redis_connection()
    return {
        "status": "ok" if is_connected else "error",
        "redis": "connected" if is_connected else "disconnected",
    }

@router.api_route("/version", methods=["GET", "HEAD"])
def version() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
    }

@router.api_route("/config", methods=["GET", "HEAD"])
def config() -> dict[str, str]:
    return {
        "app_env": settings.app_env,
        "trading_mode": settings.trading_mode,
        "log_level": settings.log_level,
    }
