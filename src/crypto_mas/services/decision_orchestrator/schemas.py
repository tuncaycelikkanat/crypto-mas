from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from crypto_mas.agents.regime_agent.schemas import RegimeSnapshot
from crypto_mas.agents.scoring_agent.schemas import AssetScore
from crypto_mas.agents.signal_agent.schemas import TradingSignal
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class DecisionAction(StrEnum):
    CONSIDER_LONG = "CONSIDER_LONG"
    CONSIDER_SHORT = "CONSIDER_SHORT"
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
    regime: RegimeSnapshot
    reason: str
    created_at: datetime
