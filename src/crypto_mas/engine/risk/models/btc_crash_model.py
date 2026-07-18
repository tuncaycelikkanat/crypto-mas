from typing import Any
from crypto_mas.engine.risk.base import BaseRiskModel
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision

class BTCCrashModel(BaseRiskModel):
    """
    Overrides LONG decisions if BTC is crashing.
    Leaves SHORT decisions intact as they might be profitable during a crash.
    """

    def evaluate(self, decision: TradingDecision, context: dict[str, Any]) -> TradingDecision:
        use_btc_shield = context.get("use_btc_shield", True)
        btc_is_crashing = context.get("btc_is_crashing", False)

        if not use_btc_shield or not btc_is_crashing:
            return decision

        if decision.action == DecisionAction.CONSIDER_LONG:
            decision.action = DecisionAction.HOLD
            decision.reason = f"REJECTED by BTC Crash Filter. Original: {decision.reason}"

        return decision
