from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from agents.scoring_agent.scoring_agent import ScoringAgent
from agents.signal_agent.trend_agent import TrendSignalAgent
from domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from domain.repositories.symbol_repository import SymbolRepository
from infrastructure.cache.redis_client import check_redis_connection
from infrastructure.config.settings import get_settings
from infrastructure.db.session import check_db_connection, get_db_session
from services.feature_pipeline.service import FeaturePipelineService
from services.market_data_service.historical_fetcher import HistoricalFetcherService
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


@app.post("/market/symbols/mock/save")
async def save_mock_symbols(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)

    symbols = await provider.fetch_symbols()

    repository = SymbolRepository(db)
    processed_rows = repository.bulk_upsert(symbols)

    return {
        "exchange": Exchange.MOCK.value,
        "fetched": len(symbols),
        "processed_rows": processed_rows,
    }


@app.post("/market/candles/mock/save")
async def save_mock_candles(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)

    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=30)

    fetcher = HistoricalFetcherService(provider=provider, db=db)

    try:
        result = await fetcher.fetch_and_store(
            symbol="BTCUSDT",
            timeframe=Timeframe.FOUR_HOURS,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.post("/features/mock/calculate")
def calculate_mock_features(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    service = FeaturePipelineService(db)

    return service.calculate_and_store(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        limit=200,
    )


@app.get("/signals/mock/trend")
def generate_mock_trend_signal(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object] | None:
    repository = FeatureSnapshotRepository(db)

    snapshots = repository.list_by_symbol(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS.value,
        limit=200,
    )

    signal = TrendSignalAgent().generate(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=snapshots,
    )

    if signal is None:
        return None

    return signal.model_dump(mode="json")


@app.get("/scores/mock/trend")
def generate_mock_trend_score(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object] | None:
    repository = FeatureSnapshotRepository(db)

    snapshots = repository.list_by_symbol(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS.value,
        limit=200,
    )

    signal = TrendSignalAgent().generate(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=snapshots,
    )

    if signal is None:
        return None

    score = ScoringAgent().score(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        signal=signal,
        snapshots=snapshots,
    )

    if score is None:
        return None

    return score.model_dump(mode="json")
