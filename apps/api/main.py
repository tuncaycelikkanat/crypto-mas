from fastapi import FastAPI

from infrastructure.cache.redis_client import check_redis_connection
from infrastructure.config.settings import get_settings
from infrastructure.db.session import check_db_connection

settings = get_settings()

app = FastAPI(
    title="Crypto MAS API",
    version=settings.app_version,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "env": settings.app_env,
        "mode": settings.trading_mode,
    }

@app.get("/health/db")
def database_health_check() -> dict[str, str]:
    is_connected = check_db_connection()

    return {
        "status": "ok" if is_connected else "error",
        "database": "connected" if is_connected else "disconnected",
    }

@app.get("/health/redis")
def redis_health_check() -> dict[str, str]:
    is_connected = check_redis_connection()

    return {
        "status": "ok" if is_connected else "error",
        "redis": "connected" if is_connected else "disconnected",
    }


@app.get("/version")
def version() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/config")
def config() -> dict[str, str]:
    return {
        "app_env": settings.app_env,
        "trading_mode": settings.trading_mode,
        "log_level": settings.log_level,
    }