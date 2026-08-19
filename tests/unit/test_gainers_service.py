from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from crypto_mas.services.gainers_service import fetch_gainers


@pytest.mark.asyncio
async def test_fetch_gainers_filters_exhausted_pumps():
    # Mock Binance 24h ticker response with 3 coins:
    # 1. BREAKOUT: high=1.05, last=1.00 (drop=4.7%), change=+20% -> should be included
    # 2. EXHAUSTED PUMP: high=2.00, last=1.50 (drop=25.0%), change=+50% -> should be excluded (>12% drop)
    # 3. FRESH MOVER: high=10.1, last=10.0 (drop=0.99%), change=+15% -> should be included
    mock_tickers = [
        {
            "symbol": "BREAKUSDT",
            "lastPrice": "1.00",
            "highPrice": "1.05",
            "lowPrice": "0.80",
            "quoteVolume": "10000000",
            "volume": "10000000",
            "priceChangePercent": "20.0",
        },
        {
            "symbol": "DUMPUSDT",
            "lastPrice": "1.50",
            "highPrice": "2.00",
            "lowPrice": "0.90",
            "quoteVolume": "25000000",
            "volume": "15000000",
            "priceChangePercent": "50.0",
        },
        {
            "symbol": "FRESHUSDT",
            "lastPrice": "10.00",
            "highPrice": "10.10",
            "lowPrice": "8.50",
            "quoteVolume": "12000000",
            "volume": "1200000",
            "priceChangePercent": "15.0",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_tickers

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        res = await fetch_gainers(
            exchange="BINANCE",
            limit=10,
            only_pump=True,
            max_drop_from_high_pct=12.0,
        )

        symbols = [item["symbol"] for item in res["pumpwatch"]]
        assert "BREAKUSDT" in symbols
        assert "FRESHUSDT" in symbols
        # DUMPUSDT had a 25% drop from its 24h high, so it must be filtered out
        assert "DUMPUSDT" not in symbols


@pytest.mark.asyncio
async def test_pump_score_rewards_proximity_to_highs():
    # Two coins with identical change % and volume, but coin A is near high and coin B is near low
    mock_tickers = [
        {
            "symbol": "NEARTOPUSDT",
            "lastPrice": "1.95",
            "highPrice": "2.00",
            "lowPrice": "1.00",
            "quoteVolume": "5000000",
            "volume": "2500000",
            "priceChangePercent": "20.0",
        },
        {
            "symbol": "NEARLOWUSDT",
            "lastPrice": "1.80",
            "highPrice": "2.00",
            "lowPrice": "1.70",
            "quoteVolume": "5000000",
            "volume": "2500000",
            "priceChangePercent": "20.0",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_tickers

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        res = await fetch_gainers(
            exchange="BINANCE",
            limit=10,
            only_pump=False,
            max_drop_from_high_pct=50.0,
        )

        near_top = next(item for item in res["gainers"] if item["symbol"] == "NEARTOPUSDT")
        near_low = next(item for item in res["gainers"] if item["symbol"] == "NEARLOWUSDT")

        assert near_top["pump_score"] > near_low["pump_score"]
        assert near_top["range_pos"] > near_low["range_pos"]
