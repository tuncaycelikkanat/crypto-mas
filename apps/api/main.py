from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI, HTTPException

from infrastructure.cache.redis_client import check_redis_connection
from infrastructure.config.settings import get_settings
from infrastructure.db.session import check_db_connection
from services.market_data_service.provider_factory import get_market_data_provider
from services.market_data_service.schemas import Exchange, Timeframe

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


@app.get("/market/symbols/sample")
async def market_symbols_sample() -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)

    try:
        symbols = await provider.fetch_symbols()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Market data provider unavailable: {type(exc).__name__}",
        ) from exc

    return {
        "exchange": Exchange.MOCK.value,
        "count": len(symbols),
        "sample": [symbol.model_dump(mode="json") for symbol in symbols[:10]],
    }


@app.get("/market/candles/sample")
async def market_candles_sample() -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)

    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=7)

    try:
        candles = await provider.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe=Timeframe.FOUR_HOURS,
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Market data provider unavailable: {type(exc).__name__}",
        ) from exc

    return {
        "exchange": Exchange.MOCK.value,
        "symbol": "BTCUSDT",
        "timeframe": Timeframe.FOUR_HOURS.value,
        "count": len(candles),
        "sample": [candle.model_dump(mode="json") for candle in candles[:3]],
    }
