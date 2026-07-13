from datetime import UTC, datetime, timedelta

import pytest

from crypto_mas.brokers.mock_adapter.market_data import MockMarketDataProvider
from crypto_mas.services.market_data_service.schemas import Timeframe


@pytest.mark.asyncio
async def test_mock_adapter():
    provider = MockMarketDataProvider()
    
    # Symbols
    symbols = await provider.fetch_symbols()
    assert len(symbols) == 3
    
    # OHLCV
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=1)
    candles = await provider.fetch_ohlcv("BTCUSDT", Timeframe.FIFTEEN_MINUTES, start_time, end_time, 100)
    assert len(candles) > 0
