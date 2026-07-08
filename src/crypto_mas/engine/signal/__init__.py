from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class SignalDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalType(StrEnum):
    TREND_FOLLOWING = "TREND_FOLLOWING"
    MEAN_REVERSION = "MEAN_REVERSION"


class TradingSignal(BaseModel):
    exchange: Exchange
    symbol: str
    timeframe: Timeframe
    signal_type: SignalType
    direction: SignalDirection
    strength: float
    reason: str
    timestamp: datetime
