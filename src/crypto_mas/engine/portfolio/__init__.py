from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class TargetPosition(BaseModel):
    symbol: str
    side: str = "LONG"
    target_weight: float = Field(ge=0.0, le=1.0)
    confidence: float
    final_score: float
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PortfolioTarget(BaseModel):
    exchange: Exchange
    timeframe: Timeframe
    strategy_id: str | None = None
    target_positions: list[TargetPosition]
    cash_weight: float = Field(ge=0.0, le=1.0)
    gross_exposure: float = Field(ge=0.0, le=1.0)
    reason: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
