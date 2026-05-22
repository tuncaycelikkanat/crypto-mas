from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from crypto_mas.agents.portfolio_manager_agent.portfolio_manager import PortfolioManagerAgent
from crypto_mas.agents.regime_agent.regime_agent import RegimeAgent
from crypto_mas.agents.scoring_agent.scoring_agent import ScoringAgent
from crypto_mas.agents.signal_agent.trend_agent import TrendSignalAgent
from crypto_mas.domain.events import InMemoryEventPublisher, create_event
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.infrastructure.cache.redis_client import check_redis_connection
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import check_db_connection, get_db_session
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider
from crypto_mas.services.decision_orchestrator.multi_symbol_runner import (
    MultiSymbolDecisionRunner,
)
from crypto_mas.services.decision_orchestrator.orchestrator import DecisionOrchestrator
from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

settings = get_settings()

app = FastAPI(
    title="Crypto MAS API",
    version=settings.app_version,
)


# region Health & Metadata Endpoints


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


# endregion


# region Mock Market Data Endpoints


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


# endregion


# region Mock Data Persistence Endpoints


@app.post("/market/candles/mock/save-all")
async def save_all_mock_candles(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)

    time_provider = SystemTimeProvider()
    end_time = time_provider.now()
    start_time = end_time - timedelta(days=30)

    fetcher = HistoricalFetcherService(provider=provider, db=db)

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    results: list[dict[str, object]] = []

    for symbol in symbols:
        try:
            result = await fetcher.fetch_and_store(
                symbol=symbol,
                timeframe=Timeframe.FOUR_HOURS,
                start_time=start_time,
                end_time=end_time,
                limit=1000,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        results.append(result.model_dump(mode="json"))

    return {
        "exchange": Exchange.MOCK.value,
        "symbols": symbols,
        "results": results,
    }


# endregion


# region Feature Pipeline Endpoints


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

@app.post("/features/mock/calculate-all")
def calculate_all_mock_features(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    service = FeaturePipelineService(db)

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    results: list[dict[str, object]] = []

    for symbol in symbols:
        result = service.calculate_and_store(
            exchange=Exchange.MOCK,
            symbol=symbol,
            timeframe=Timeframe.FOUR_HOURS,
            limit=200,
        )
        results.append(result)

    return {
        "exchange": Exchange.MOCK.value,
        "symbols": symbols,
        "results": results,
    }


# endregion


# region Signal, Score & Regime Endpoints


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

    publisher = InMemoryEventPublisher()

    event = create_event(
        event_type="signal.generated",
        source="trend_signal_agent",
        payload=signal.model_dump(mode="json"),
    )

    publisher.publish(event)

    return {
        "signal": signal.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in publisher.events],
    }


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


@app.get("/regime/mock")
def detect_mock_regime(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object] | None:
    repository = FeatureSnapshotRepository(db)

    snapshots = repository.list_by_symbol(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS.value,
        limit=200,
    )

    regime = RegimeAgent().detect(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=snapshots,
    )

    if regime is None:
        return None

    return regime.model_dump(mode="json")


# endregion


# region Binance Market Data Endpoints


@app.get("/market/binance/time")
async def binance_time_test() -> dict[str, object]:
    url = f"{settings.binance_base_url.rstrip('/')}/api/v3/time"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return {
                "status": "ok",
                "url": url,
                "data": response.json(),
            }
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Binance unavailable: {type(exc).__name__}",
        ) from exc


@app.get("/market/binance/symbols/sample")
async def binance_symbols_sample() -> dict[str, object]:
    provider = get_market_data_provider(Exchange.BINANCE)

    try:
        symbols = await provider.fetch_symbols()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Binance market data unavailable: {type(exc).__name__}",
        ) from exc

    return {
        "exchange": Exchange.BINANCE.value,
        "count": len(symbols),
        "sample": [symbol.model_dump(mode="json") for symbol in symbols[:10]],
    }


@app.get("/market/binance/candles/sample")
async def binance_candles_sample() -> dict[str, object]:
    provider = get_market_data_provider(Exchange.BINANCE)

    time_provider = SystemTimeProvider()
    end_time = time_provider.now()
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
            detail=f"Binance market data unavailable: {type(exc).__name__}",
        ) from exc

    return {
        "exchange": Exchange.BINANCE.value,
        "symbol": "BTCUSDT",
        "timeframe": Timeframe.FOUR_HOURS.value,
        "count": len(candles),
        "sample": [candle.model_dump(mode="json") for candle in candles[:3]],
    }


@app.post("/market/binance/candles/save")
async def save_binance_candles(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    provider = get_market_data_provider(Exchange.BINANCE)

    time_provider = SystemTimeProvider()
    end_time = time_provider.now()
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
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Binance market data unavailable: {type(exc).__name__}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result.model_dump(mode="json")


# endregion


# region Decision Orchestrator Endpoints


@app.get("/decision/mock/run")
def run_mock_decision(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object] | None:
    repository = FeatureSnapshotRepository(db)

    snapshots = repository.list_by_symbol(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS.value,
        limit=200,
    )

    decision = DecisionOrchestrator().run(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=snapshots,
    )

    if decision is None:
        return None

    return decision.model_dump(mode="json")

@app.get("/decision/mock/run-all")
def run_all_mock_decisions(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    runner = MultiSymbolDecisionRunner(db)

    result = runner.run(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        quote_asset="USDT",
        symbol_limit=10,
        snapshot_limit=200,
    )

    return result.model_dump(mode="json")

# endregion

# region Portfolio Manager Endpoints


@app.get("/portfolio/mock/target")
def build_mock_target_portfolio(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    runner = MultiSymbolDecisionRunner(db)

    decision_result = runner.run(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        quote_asset="USDT",
        symbol_limit=10,
        snapshot_limit=200,
    )

    portfolio_target = PortfolioManagerAgent(
        max_positions=3,
        max_gross_exposure=0.90,
        min_confidence=0.35,
    ).build_target_portfolio(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        decisions=decision_result.decisions,
    )

    return portfolio_target.model_dump(mode="json")


# endregion