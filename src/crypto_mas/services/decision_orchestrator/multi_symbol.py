from pydantic import BaseModel

from crypto_mas.services.decision_orchestrator.schemas import TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class MultiSymbolDecisionResult(BaseModel):
    exchange: Exchange
    timeframe: Timeframe
    requested_symbols: int
    processed_symbols: int
    decisions: list[TradingDecision]
