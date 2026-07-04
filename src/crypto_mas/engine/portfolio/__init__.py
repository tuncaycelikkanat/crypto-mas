from datetime import datetime

from pydantic import BaseModel, Field

from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class TargetPosition(BaseModel):
    symbol: str
    target_weight: float = Field(ge=0.0, le=1.0)
    confidence: float
    final_score: float
    reason: str


class PortfolioTarget(BaseModel):
    exchange: Exchange
    timeframe: Timeframe
    target_positions: list[TargetPosition]
    cash_weight: float = Field(ge=0.0, le=1.0)
    gross_exposure: float = Field(ge=0.0, le=1.0)
    reason: str
    created_at: datetime
