"""
Scanner & Gainers Router

Endpoints:
  GET /api/v1/scanner/gainers   — Live top movers from Binance/MEXC
  GET /api/v1/scanner/pumpwatch — Coins with best pump_score
"""
from typing import Any

from fastapi import APIRouter, Query

from crypto_mas.services.gainers_service import fetch_gainers

router = APIRouter(prefix="/api/v1/scanner", tags=["Scanner"])


@router.get("/gainers")
async def get_gainers(
    exchange: str = Query(default="BINANCE", description="BINANCE or MEXC"),
    limit: int = Query(default=20, ge=5, le=100),
    min_volume_usdt: float = Query(default=500_000, description="Minimum 24h USDT volume"),
    only_pump: bool = Query(default=False, description="Return only positive movers"),
) -> dict[str, Any]:
    """
    Real-time top gainers and losers from the chosen exchange.
    Includes pump_score (change% × volume factor) for prioritisation.
    """
    return await fetch_gainers(
        exchange=exchange,
        limit=limit,
        min_volume_usdt=min_volume_usdt,
        only_pump=only_pump,
    )


@router.get("/pumpwatch")
async def get_pumpwatch(
    exchange: str = Query(default="BINANCE"),
    limit: int = Query(default=10, ge=1, le=50),
    min_volume_usdt: float = Query(default=1_000_000),
) -> dict[str, Any]:
    """
    High-conviction pump candidates: positive change AND high relative volume.
    Sorted by pump_score descending.
    """
    result = await fetch_gainers(
        exchange=exchange,
        limit=limit,
        min_volume_usdt=min_volume_usdt,
        only_pump=True,
    )
    return {
        "exchange":  result.get("exchange"),
        "scanned":   result.get("total_pairs_scanned", 0),
        "pumpwatch": result.get("pumpwatch", []),
    }
