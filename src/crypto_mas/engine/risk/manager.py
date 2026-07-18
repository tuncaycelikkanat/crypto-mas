from typing import Any
from crypto_mas.engine.risk.base import BaseRiskModel
from crypto_mas.engine.strategy.schemas import TradingDecision

class RiskManager:
    """
    Orchestrates all risk models to evaluate a trading decision.
    """
    def __init__(self, models: list[BaseRiskModel] | None = None) -> None:
        self.models = models or []

    def evaluate_decision(self, decision: TradingDecision, context: dict[str, Any]) -> TradingDecision:
        """
        Pass the decision through all configured Risk/Shield models.
        """
        for model in self.models:
            decision = model.evaluate(decision, context)
            
            # If any shield completely blocks the trade, we can optionally short-circuit,
            # but letting it pass through all allows chaining (though HOLD usually stays HOLD).
        return decision
