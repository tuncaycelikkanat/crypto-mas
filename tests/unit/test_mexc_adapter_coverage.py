import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, UTC

from crypto_mas.brokers.mexc_adapter.market_data import MexcMarketDataProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

@pytest.mark.asyncio
@patch("crypto_mas.brokers.mexc_adapter.market_data.httpx.AsyncClient")
async def test_mexc_fetch_symbols(mock_client_class):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "symbols": [
            {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "status": "1", "isSpotTradingAllowed": True, "permissions": ["SPOT"]},
            {"symbol": "ETHUSDT", "baseAsset": "ETH", "quoteAsset": "USDT", "status": "2", "isSpotTradingAllowed": False, "permissions": ["SPOT"]},
            {"symbol": "SOLUSDT", "baseAsset": "SOL", "quoteAsset": "USDT", "status": "TRADING", "isSpotTradingAllowed": True, "permissions": []},
            {"symbol": "BTCEUR", "baseAsset": "BTC", "quoteAsset": "EUR", "status": "1", "isSpotTradingAllowed": True, "permissions": ["SPOT"]}, # Ignored quote
            {"symbol": "BTC3LUSDT", "baseAsset": "BTC3L", "quoteAsset": "USDT", "status": "1", "isSpotTradingAllowed": True, "permissions": ["SPOT"]}, # Leveraged
            {"symbol": "USDCUSDT", "baseAsset": "USDC", "quoteAsset": "USDT", "status": "1", "isSpotTradingAllowed": True, "permissions": ["SPOT"]} # Stablecoin
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response
    
    provider = MexcMarketDataProvider()
    assert provider.exchange == Exchange.MEXC
    
    symbols = await provider.fetch_symbols()
    assert len(symbols) == 5
    
    btc = next(s for s in symbols if s.symbol == "BTCUSDT")
    assert btc.is_active is True
    assert btc.is_stablecoin is False
    assert btc.is_leveraged_token is False
    
    eth = next(s for s in symbols if s.symbol == "ETHUSDT")
    assert eth.is_active is False
    
    sol = next(s for s in symbols if s.symbol == "SOLUSDT")
    assert sol.is_active is True
    
    usdc = next(s for s in symbols if s.symbol == "USDCUSDT")
    assert usdc.is_stablecoin is True
    
    leveraged = next(s for s in symbols if s.symbol == "BTC3LUSDT")
    assert leveraged.is_leveraged_token is True

@pytest.mark.asyncio
@patch("crypto_mas.brokers.mexc_adapter.market_data.httpx.AsyncClient")
async def test_mexc_fetch_ohlcv(mock_client_class):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.json.return_value = [
        [
            1499040000000,      # Open time
            "0.01633302",       # Open
            "0.80000000",       # High
            "0.01575800",       # Low
            "0.01577100",       # Close
            "148976.11427815",  # Volume
            1499644799999,      # Close time
            "2434.19055334"     # Quote asset volume (length 8)
        ]
    ]
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response
    
    provider = MexcMarketDataProvider()
    
    start = datetime(2023, 1, 1, tzinfo=UTC)
    end = datetime(2023, 1, 2, tzinfo=UTC)
    
    candles = await provider.fetch_ohlcv("BTCUSDT", Timeframe.FIFTEEN_MINUTES, start_time=start, end_time=end)
    assert len(candles) == 1
    assert candles[0].open_time == datetime.fromtimestamp(1499040000000 / 1000, tz=UTC)
    assert float(candles[0].open) == 0.01633302
    assert candles[0].trade_count == 0
    assert candles[0].source == "MEXC_REST"
    
    # Test without timezone
    start_no_tz = datetime(2023, 1, 1)
    await provider.fetch_ohlcv("BTCUSDT", Timeframe.FIFTEEN_MINUTES, start_time=start_no_tz)
