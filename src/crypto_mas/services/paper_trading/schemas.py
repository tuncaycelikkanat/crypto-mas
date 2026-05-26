from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from crypto_mas.services.market_data_service.schemas import Exchange


class PaperOrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class PaperExecutionStatus(StrEnum):
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"
    REJECTED = "REJECTED"


class PaperExecutionItem(BaseModel):
    symbol: str
    side: PaperOrderSide
    status: PaperExecutionStatus
    target_weight: float = Field(ge=0.0, le=1.0)
    notional: float
    price: float | None = None
    quantity: float | None = None
    reason: str


class PaperExecutionReport(BaseModel):
    account_name: str
    exchange: Exchange
    starting_cash: float
    ending_cash: float
    starting_equity: float
    ending_equity: float
    executed: list[PaperExecutionItem]
    skipped: list[PaperExecutionItem]
    created_at: datetime
