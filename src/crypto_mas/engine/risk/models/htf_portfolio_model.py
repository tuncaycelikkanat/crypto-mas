from typing import Any

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.risk.base import BaseRiskModel
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision


class HTFPortfolioModel(BaseRiskModel):
    """
    Higher Timeframe (HTF) Portfolio Filter.
    Overrides LONG or SHORT decisions if the Higher Timeframe contradicts them.
    """

    def evaluate(self, decision: TradingDecision, context: dict[str, Any]) -> TradingDecision:
        use_htf_shield = context.get("use_htf_shield", True)
        htf_snapshots: list[FeatureSnapshot] = context.get("htf_snapshots", [])

        if not use_htf_shield or not htf_snapshots:
            return decision

        latest = htf_snapshots[-1]
        features = latest.features_json

        close = features.get("close")
        ema_20 = features.get("ema_20")
        ema_50 = features.get("ema_50")
        roc_14 = features.get("roc_14")

        if None in {close, ema_20, ema_50, roc_14}:
            return decision

        # 1. LONG filter: if HTF is strongly bearish, AVOID LONG
        if decision.action == DecisionAction.CONSIDER_LONG:
            bearish = close < ema_20 < ema_50 and roc_14 < -3.0  # type: ignore
            if bearish:
                decision.action = DecisionAction.HOLD
                decision.reason = f"REJECTED by HTF Shield (Strong Bear). Original: {decision.reason}"
                return decision

        # 2. SHORT filter: if HTF is strongly bullish, AVOID SHORT
        if decision.action == DecisionAction.CONSIDER_SHORT:
            bullish = close > ema_20 > ema_50 and roc_14 > 0  # type: ignore
            if bullish:
                decision.action = DecisionAction.HOLD
                decision.reason = f"REJECTED by HTF Shield (Strong Bull). Original: {decision.reason}"
                return decision

        return decision
