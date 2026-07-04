from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.symbol_repository import SymbolRepository
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import get_db_session
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

settings = get_settings()
router = APIRouter(prefix="/market", tags=["Market Data"])

@router.get("/symbols/sample")
async def market_symbols_sample() -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)
    try:
        symbols = await provider.fetch_symbols()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Market data provider unavailable: {type(exc).__name__}") from exc
    return {"exchange": Exchange.MOCK.value, "count": len(symbols), "sample": [symbol.model_dump(mode="json") for symbol in symbols[:10]]}

@router.get("/candles/sample")
async def market_candles_sample() -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=7)
    try:
        candles = await provider.fetch_ohlcv("BTCUSDT", Timeframe.FOUR_HOURS, start_time, end_time, 100)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Market data provider unavailable: {type(exc).__name__}") from exc
    return {"exchange": Exchange.MOCK.value, "symbol": "BTCUSDT", "timeframe": Timeframe.FOUR_HOURS.value, "count": len(candles), "sample": [candle.model_dump(mode="json") for candle in candles[:3]]}

@router.post("/symbols/mock/save")
async def save_mock_symbols(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)
    symbols = await provider.fetch_symbols()
    repository = SymbolRepository(db)
    processed_rows = repository.bulk_upsert(symbols)
    return {"exchange": Exchange.MOCK.value, "fetched": len(symbols), "processed_rows": processed_rows}

@router.post("/candles/mock/save-all")
async def save_all_mock_candles(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, object]:
    provider = get_market_data_provider(Exchange.MOCK)
    time_provider = SystemTimeProvider()
    end_time = time_provider.now()
    start_time = end_time - timedelta(days=30)
    fetcher = HistoricalFetcherService(provider=provider, db=db)
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    results: list[dict[str, object]] = []
    for symbol in symbols:
        try:
            result = await fetcher.fetch_and_store_range(symbol, Timeframe.FOUR_HOURS, start_time, end_time, 1000)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        results.append(result.model_dump(mode="json"))
    return {"exchange": Exchange.MOCK.value, "symbols": symbols, "results": results}

@router.get("/binance/time")
async def binance_time_test() -> dict[str, object]:
    url = f"{settings.binance_base_url.rstrip('/')}/api/v3/time"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return {"status": "ok", "url": url, "data": response.json()}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Binance unavailable: {type(exc).__name__}") from exc

@router.get("/binance/symbols/sample")
async def binance_symbols_sample() -> dict[str, object]:
    provider = get_market_data_provider(Exchange.BINANCE)
    try:
        symbols = await provider.fetch_symbols()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Binance market data unavailable: {type(exc).__name__}") from exc
    return {"exchange": Exchange.BINANCE.value, "count": len(symbols), "sample": [symbol.model_dump(mode="json") for symbol in symbols[:10]]}

@router.get("/binance/candles/sample")
async def binance_candles_sample() -> dict[str, object]:
    provider = get_market_data_provider(Exchange.BINANCE)
    time_provider = SystemTimeProvider()
    end_time = time_provider.now()
    start_time = end_time - timedelta(days=7)
    try:
        candles = await provider.fetch_ohlcv("BTCUSDT", Timeframe.FOUR_HOURS, start_time, end_time, 100)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Binance market data unavailable: {type(exc).__name__}") from exc
    return {"exchange": Exchange.BINANCE.value, "symbol": "BTCUSDT", "timeframe": Timeframe.FOUR_HOURS.value, "count": len(candles), "sample": [candle.model_dump(mode="json") for candle in candles[:3]]}

@router.post("/binance/candles/save")
async def save_binance_candles(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, object]:
    provider = get_market_data_provider(Exchange.BINANCE)
    time_provider = SystemTimeProvider()
    end_time = time_provider.now()
    start_time = end_time - timedelta(days=30)
    fetcher = HistoricalFetcherService(provider=provider, db=db)
    try:
        result = await fetcher.fetch_and_store_range("BTCUSDT", Timeframe.FOUR_HOURS, start_time, end_time, 1000)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Binance market data unavailable: {type(exc).__name__}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.model_dump(mode="json")
