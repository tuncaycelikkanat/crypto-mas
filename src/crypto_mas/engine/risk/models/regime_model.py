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

        # 2. Timeframe Filter for Bear and Sideways (Noise Reduction)
        if regime in (MarketRegime.BEAR_TREND, MarketRegime.SIDEWAYS):
            from crypto_mas.services.market_data_service.schemas import Timeframe
            if decision.timeframe == Timeframe.FIFTEEN_MINUTES:
                if decision.action in (DecisionAction.CONSIDER_LONG, DecisionAction.CONSIDER_SHORT):
                    decision.action = DecisionAction.HOLD
                    decision.reason = f"REJECTED by Regime Shield (15m is too noisy for {regime.name}). Use 1h/4h. Original: {decision.reason}"
                return decision

        # 3. Bear Trend Long Filter
        # Let multi_agent handle scoring thresholds normally.

        return decision
