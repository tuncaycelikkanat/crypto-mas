from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.schemas import (
    Exchange,
    HistoricalFetchResult,
    OHLCVCandle,
    Timeframe,
)


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.exchange = Exchange.BINANCE
    provider.fetch_ohlcv = AsyncMock()
    return provider


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    return session


@pytest.mark.asyncio
async def test_fetch_and_store_range_pagination(mock_provider, mock_db_session, monkeypatch):
    # Setup fetcher with mocked repositories
    fetcher = HistoricalFetcherService(provider=mock_provider, db=mock_db_session)
    
    # Mock Repositories
    fetcher.candle_repository.bulk_upsert = MagicMock(return_value=1000)
    
    mock_state_repo = MagicMock()
    mock_state_repo.get_state.return_value = None  # No previous state
    fetcher.state_repository = mock_state_repo
    
    # Mock Integrity Checker to always pass
    mock_integrity_report = MagicMock()
    mock_integrity_report.is_valid = True
    fetcher.integrity_checker.validate = MagicMock(return_value=mock_integrity_report)

    start_time = datetime(2023, 1, 1, tzinfo=UTC)
    end_time = datetime(2023, 1, 3, tzinfo=UTC)  # 2 days

    # Mock provider.fetch_ohlcv to return 1000 candles per call
    def mock_fetch_side_effect(symbol, timeframe, start_time, end_time, limit):
        candles = []
        # Truncate to hour
        current_time = start_time.replace(minute=0, second=0, microsecond=0)
        if current_time < start_time:
            current_time += timedelta(hours=1)
            
        for i in range(limit):
            candles.append(
                OHLCVCandle(
                    exchange=Exchange.BINANCE,
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=current_time,
                    open=Decimal("1.0"),
                    high=Decimal("2.0"),
                    low=Decimal("0.5"),
                    close=Decimal("1.5"),
                    volume=Decimal("100"),
                    close_time=current_time + timedelta(hours=1) - timedelta(milliseconds=1),
                    quote_volume=Decimal("150"),
                    trade_count=10,
                    source="BINANCE_REST"
                )
            )
            current_time += timedelta(hours=1)
            if current_time >= end_time:
                break
        return candles

    mock_provider.fetch_ohlcv.side_effect = mock_fetch_side_effect

    # Run backfill
    result = await fetcher.fetch_and_store_range(
        symbol="BTCUSDT",
        timeframe=Timeframe.ONE_HOUR,
        start_time=start_time,
        end_time=end_time,
        limit=10  # use small limit to force pagination
    )

    assert result.fetched == 48  # 2 days * 24 hours
    assert mock_provider.fetch_ohlcv.call_count == 5  # 48 / 10 = 5 calls (10, 10, 10, 10, 8)
    assert mock_state_repo.upsert_state.call_count == 5

@pytest.mark.asyncio
async def test_fetch_exception(mock_provider, mock_db_session):
    fetcher = HistoricalFetcherService(provider=mock_provider, db=mock_db_session)
    mock_state_repo = MagicMock()
    mock_state_repo.get_state.return_value = None
    fetcher.state_repository = mock_state_repo
    mock_provider.fetch_ohlcv.side_effect = Exception("API limit")
    
    result = await fetcher.fetch_and_store_range(
        symbol="BTCUSDT",
        timeframe=Timeframe.ONE_HOUR,
        start_time=datetime(2023, 1, 1, tzinfo=UTC),
        end_time=datetime(2023, 1, 2, tzinfo=UTC),
    )
    
    assert result.fetched == 0

@pytest.mark.asyncio
async def test_integrity_failure(mock_provider, mock_db_session):
    fetcher = HistoricalFetcherService(provider=mock_provider, db=mock_db_session)
    
    mock_state_repo = MagicMock()
    mock_state_repo.get_state.return_value = None
    fetcher.state_repository = mock_state_repo
    
    mock_provider.fetch_ohlcv.return_value = [
        OHLCVCandle(
            exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.ONE_HOUR,
            open_time=datetime(2023, 1, 1, tzinfo=UTC), open=Decimal("1"), high=Decimal("2"), low=Decimal("0.5"), close=Decimal("1.5"),
            volume=Decimal("100"), close_time=datetime(2023, 1, 1, 1, tzinfo=UTC), quote_volume=Decimal("150"), trade_count=10, source="BINANCE"
        )
    ]
    
    mock_integrity = MagicMock()
    mock_integrity.is_valid = False
    mock_integrity.model_dump.return_value = {"error": "gap"}
    fetcher.integrity_checker.validate = MagicMock(return_value=mock_integrity)
    
    result = await fetcher.fetch_and_store_range(
        symbol="BTCUSDT", timeframe=Timeframe.ONE_HOUR,
        start_time=datetime(2023, 1, 1, tzinfo=UTC), end_time=datetime(2023, 1, 2, tzinfo=UTC),
    )
    
    assert result.fetched == 0

@pytest.mark.asyncio
async def test_backfill_universe_exception(mock_provider, mock_db_session):
    fetcher = HistoricalFetcherService(provider=mock_provider, db=mock_db_session)
    
    # First symbol passes, second raises exception
    async def mock_fetch_range(symbol, **kwargs):
        if symbol == "FAILUSDT":
            raise ValueError("Test error")
        return HistoricalFetchResult(
            exchange=Exchange.BINANCE, symbol=symbol, timeframe=Timeframe.ONE_HOUR,
            fetched=10, processed_rows=10, start_time=datetime.now(UTC), end_time=datetime.now(UTC)
        )
        
    fetcher.fetch_and_store_range = AsyncMock(side_effect=mock_fetch_range)
    
    results = await fetcher.backfill_universe(
        symbols=["BTCUSDT", "FAILUSDT"],
        timeframe=Timeframe.ONE_HOUR,
        start_time=datetime(2023, 1, 1, tzinfo=UTC),
        end_time=datetime(2023, 1, 2, tzinfo=UTC),
    )
    
    assert len(results) == 1
    assert results[0].symbol == "BTCUSDT"
