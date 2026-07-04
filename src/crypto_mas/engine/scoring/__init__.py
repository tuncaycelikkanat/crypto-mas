from datetime import datetime

from pydantic import BaseModel

from crypto_mas.engine.signal import SignalDirection
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class AssetScore(BaseModel):
    exchange: Exchange
    symbol: str
    timeframe: Timeframe
    direction: SignalDirection
    final_score: float
    trend_score: float
    momentum_score: float
    volatility_penalty: float
    reason: str
    timestamp: datetime
