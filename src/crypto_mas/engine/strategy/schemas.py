from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from crypto_mas.engine.regime import RegimeSnapshot
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.signal import TradingSignal
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class DecisionAction(StrEnum):
    CONSIDER_LONG = "CONSIDER_LONG"
    CONSIDER_SHORT = "CONSIDER_SHORT"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"
    HOLD = "HOLD"
    AVOID = "AVOID"


class TradingDecision(BaseModel):
    exchange: Exchange
    symbol: str
    timeframe: Timeframe
    action: DecisionAction
    confidence: float
    signal: TradingSignal
    score: AssetScore
    regime: RegimeSnapshot | None = None
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
