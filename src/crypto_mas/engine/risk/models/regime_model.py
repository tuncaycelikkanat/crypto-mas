from typing import Any

from crypto_mas.engine.regime import MarketRegime
from crypto_mas.engine.risk.base import BaseRiskModel
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision


class RegimeModel(BaseRiskModel):
    """
    Market Regime Filter.
    Overrides LONG or SHORT decisions if the Market Regime is too hostile.
    """

    def evaluate(self, decision: TradingDecision, context: dict[str, Any]) -> TradingDecision:
        use_regime_shield = context.get("use_regime_shield", True)

        if not use_regime_shield or decision.regime is None:
            return decision

        regime = decision.regime.regime

        # 1. Extreme Volatility Filter
        if regime == MarketRegime.HIGH_VOLATILITY:
            if decision.action in (DecisionAction.CONSIDER_LONG, DecisionAction.CONSIDER_SHORT):
                decision.action = DecisionAction.HOLD
                decision.reason = f"REJECTED by Regime Shield (HIGH_VOLATILITY). Original: {decision.reason}"
            return decision

        # 2. Bear Trend Long Filter (Strongly discouraged but let multi_agent handle scoring thresholds normally,
        # unless we want to hard reject it here. If multi_agent gave CONSIDER_LONG despite Bear Trend, we let it pass
        # because multi_agent already applied the threshold penalty. But we could add stricter rules here).

        return decision
