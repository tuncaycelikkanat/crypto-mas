from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class MarketRegime(StrEnum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    UNKNOWN = "UNKNOWN"


class RegimeSnapshot(BaseModel):
    exchange: Exchange
    symbol: str
    timeframe: Timeframe
    regime: MarketRegime
    confidence: float
    risk_multiplier: float
    reason: str
    timestamp: datetime
