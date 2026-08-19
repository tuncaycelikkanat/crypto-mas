"""
Top Gainers / Scanner Service

Fetches real-time top gainers from Binance 24h ticker and provides:
  - Top movers by % change
  - Top by volume spike (RVOL) - highest volume relative to normal
  - Active pumpwatch: coins with high RVOL AND positive price change
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger("crypto_mas.gainers")

from crypto_mas.brokers.base_market_data import DEFAULT_MARKET_HEADERS

BINANCE_TICKER_URLS = [
    "https://data-api.binance.vision/api/v3/ticker/24hr",
    "https://api1.binance.com/api/v3/ticker/24hr",
    "https://api2.binance.com/api/v3/ticker/24hr",
    "https://api.binance.com/api/v3/ticker/24hr",
    "https://api.mexc.com/api/v3/ticker/24hr",
]
MEXC_TICKER_URLS = [
    "https://api.mexc.com/api/v3/ticker/24hr",
]


async def fetch_gainers(
    exchange: str = "BINANCE",
    limit: int = 20,
    min_volume_usdt: float = 500_000,   # Minimum 24h volume ($500k) to filter out dust
    quote_asset: str = "USDT",
    only_pump: bool = False,             # If True, only return positive movers
    max_drop_from_high_pct: float = 12.0, # Max allowed drop from 24h high (filters exhausted pumps)
) -> dict[str, Any]:
    """
    Returns top gainers sorted by 24h price change %.
    Includes computed RVOL proxy, 24h range proximity, and pump score.
    """
    urls = BINANCE_TICKER_URLS if exchange.upper() == "BINANCE" else MEXC_TICKER_URLS
    tickers = None
    last_exc = None

    async with httpx.AsyncClient(headers=DEFAULT_MARKET_HEADERS, timeout=12.0) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    tickers = resp.json()
                    break
            except Exception as exc:
                last_exc = exc
                continue

    if tickers is None:
        logger.error(f"Failed to fetch tickers from {exchange}: {last_exc}")
        return {"error": str(last_exc), "gainers": [], "losers": [], "pumpwatch": []}

    # Filter to USDT pairs with sufficient volume
    usdt_tickers = []
    for t in tickers:
        symbol = t.get("symbol", "")
        if not symbol.endswith(quote_asset):
            continue
        try:
            vol_usdt = float(t.get("quoteVolume", 0))
            change_pct = float(t.get("priceChangePercent", 0))
            last_price = float(t.get("lastPrice", 0))
            high_24h   = float(t.get("highPrice", 0))
            low_24h    = float(t.get("lowPrice", 0))
            volume     = float(t.get("volume", 0))
        except (ValueError, TypeError):
            continue

        if vol_usdt < min_volume_usdt or last_price == 0:
            continue

        if only_pump and change_pct <= 0:
            continue

        # ── 1. Calculate drop from 24h high (Exhaustion / Dump Filter) ────────
        drop_from_high_pct = ((high_24h - last_price) / high_24h * 100) if high_24h > 0 else 0.0
        if only_pump and drop_from_high_pct > max_drop_from_high_pct:
            # Exclude coins that have already dumped significantly from their 24h high
            continue

        # ── 2. Calculate range proximity (0.0 = at low, 1.0 = at high) ────────
        range_span = high_24h - low_24h
        range_pos = ((last_price - low_24h) / range_span) if range_span > 0 else 0.5

        # ── 3. Pump score: rewards strong breakout near highs + high volume ──
        # Coins holding near high (range_pos >= 0.70) get higher multiplier
        proximity_mult = max(0.2, range_pos) ** 1.2
        pump_score = abs(change_pct) * ((vol_usdt / 1_000_000) ** 0.3) * proximity_mult

        usdt_tickers.append({
            "symbol":             symbol,
            "last_price":         last_price,
            "change_pct":         round(change_pct, 2),
            "volume_usdt":        round(vol_usdt, 0),
            "volume_coins":       round(volume, 4),
            "high_24h":           high_24h,
            "low_24h":            low_24h,
            "range_pct":          round((high_24h - low_24h) / low_24h * 100, 2) if low_24h > 0 else 0,
            "drop_from_high_pct": round(drop_from_high_pct, 2),
            "range_pos":          round(range_pos, 2),
            "pump_score":         round(pump_score, 2),
        })

    # Sort by change %
    gainers = sorted(usdt_tickers, key=lambda x: x["change_pct"], reverse=True)[:limit]
    losers  = sorted(usdt_tickers, key=lambda x: x["change_pct"])[:limit]

    # Pumpwatch: top by pump_score (positive change only)
    pumpwatch = sorted(
        [t for t in usdt_tickers if t["change_pct"] > 0],
        key=lambda x: x["pump_score"],
        reverse=True
    )[:limit]

    return {
        "exchange":  exchange.upper(),
        "total_pairs_scanned": len(usdt_tickers),
        "gainers":   gainers,
        "losers":    losers,
        "pumpwatch": pumpwatch,
    }


async def fetch_hidden_gems(
    exchange: str = "BINANCE",
    limit: int = 50,
    min_volume_usdt: float = 50_000,     # Don't want complete dust
    max_volume_usdt: float = 5_000_000,  # Don't want huge caps where whales hide
    quote_asset: str = "USDT",
) -> dict[str, Any]:
    """
    Returns top "hidden gems" sorted by gem_score.
    Criteria:
      - Price change is flat (-3% to +3%)
      - Volume is relatively high for the low price change
    """
    url = BINANCE_TICKER_URL if exchange.upper() == "BINANCE" else MEXC_TICKER_URL

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            tickers = resp.json()
    except Exception as exc:
        logger.error(f"Failed to fetch tickers for hidden gems from {exchange}: {exc}")
        return {"error": str(exc), "hidden_gems": []}

    usdt_tickers = []
    for t in tickers:
        symbol = t.get("symbol", "")
        if not symbol.endswith(quote_asset):
            continue
        try:
            vol_usdt = float(t.get("quoteVolume", 0))
            change_pct = float(t.get("priceChangePercent", 0))
            last_price = float(t.get("lastPrice", 0))
        except (ValueError, TypeError):
            continue

        if vol_usdt < min_volume_usdt or vol_usdt > max_volume_usdt or last_price == 0:
            continue

        # Sleeping criteria: price hasn't moved much
        if change_pct < -3.0 or change_pct > 3.0:
            continue

        # Gem score: High volume despite being flat
        # Add 0.1 to avoid division by zero
        gem_score = (vol_usdt / 1_000) / (abs(change_pct) + 0.1)

        usdt_tickers.append({
            "symbol":        symbol,
            "last_price":    last_price,
            "change_pct":    round(change_pct, 2),
            "volume_usdt":   round(vol_usdt, 0),
            "gem_score":     round(gem_score, 2),
        })

    hidden_gems = sorted(usdt_tickers, key=lambda x: x["gem_score"], reverse=True)[:limit]

    return {
        "exchange":  exchange.upper(),
        "total_pairs_scanned": len(usdt_tickers),
        "hidden_gems": hidden_gems,
    }
