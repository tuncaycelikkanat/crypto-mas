from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

# BTC-correlated asset group for concentration risk control
BTC_CORRELATED = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT"}


class PortfolioEngine:
    def __init__(
        self,
        max_positions: int = 10,
        max_gross_exposure: float = 0.85,
        min_confidence: float = 0.5,
        max_correlated_group_weight: float = 0.40,
        time_provider: TimeProvider | None = None,
    ) -> None:
        self.max_positions = max_positions
        self.max_gross_exposure = max_gross_exposure
        self.min_confidence = min_confidence
        self.max_correlated_group_weight = max_correlated_group_weight
        self.time_provider = time_provider or SystemTimeProvider()

    def build_target_portfolio(
        self,
        exchange: Exchange,
        timeframe: Timeframe,
        decisions: list[TradingDecision],
    ) -> PortfolioTarget:
        candidates = [
            decision
            for decision in decisions
            if decision.action in (DecisionAction.CONSIDER_LONG, DecisionAction.CONSIDER_SHORT)
            and decision.confidence >= self.min_confidence
            and decision.score.final_score > 0
        ]

        candidates = sorted(
            candidates,
            key=lambda decision: (decision.confidence, decision.score.final_score),
            reverse=True,
        )

        selected = candidates[: self.max_positions]

        if not selected:
            return PortfolioTarget(
                exchange=exchange,
                timeframe=timeframe,
                target_positions=[],
                cash_weight=1.0,
                gross_exposure=0.0,
                reason="No eligible candidates found.",
                created_at=self.time_provider.now(),
            )

        total_score = sum(decision.score.final_score for decision in selected)

        risk_per_trade = 0.01   # 1% of portfolio per position
        stop_loss_mult = 2.0

        positions = []
        for decision in selected:
            # Approximate ATR% from volatility_penalty (which = atr/close * 2)
            atr_pct = decision.score.volatility_penalty / 2.0

            # ATR-based weight
            if atr_pct > 0:
                atr_weight = risk_per_trade / (atr_pct * stop_loss_mult)
            else:
                atr_weight = self.max_gross_exposure / len(selected)

            # Score-proportional weight
            if total_score > 0:
                score_weight = self.max_gross_exposure * decision.score.final_score / total_score
            else:
                score_weight = self.max_gross_exposure / len(selected)

            # Blend: 60% score-proportional, 40% ATR-based, hard cap per position
            target_weight = 0.60 * score_weight + 0.40 * atr_weight
            target_weight = min(target_weight, 0.25)

            positions.append(
                self._to_target_position(
                    decision=decision,
                    target_weight=target_weight,
                    reason="Weight: 60% score-proportional + 40% ATR-based, capped at 0.25.",
                )
            )

        # Correlation group control: scale down BTC-correlated group if overweight
        corr_total = sum(
            p.target_weight for p in positions if p.symbol in BTC_CORRELATED
        )
        if corr_total > self.max_correlated_group_weight and corr_total > 0:
            scale = self.max_correlated_group_weight / corr_total
            positions = [
                self._to_target_position(
                    decision=decision,
                    target_weight=p.target_weight * scale
                    if p.symbol in BTC_CORRELATED
                    else p.target_weight,
                    reason=(
                        f"Weight scaled by {scale:.3f} due to BTC-correlated group cap."
                        if p.symbol in BTC_CORRELATED
                        else p.reason
                    ),
                )
                for p, decision in zip(positions, selected, strict=False)
            ]

        gross_exposure = round(sum(position.target_weight for position in positions), 6)
        cash_weight = round(max(0.0, 1.0 - gross_exposure), 10)

        return PortfolioTarget(
            exchange=exchange,
            timeframe=timeframe,
            target_positions=positions,
            cash_weight=cash_weight,
            gross_exposure=gross_exposure,
            reason=(
                f"Selected {len(positions)} positions from {len(decisions)} decisions. "
                f"Max gross exposure={self.max_gross_exposure:.2f}."
            ),
            created_at=self.time_provider.now(),
        )

    @staticmethod
    def _to_target_position(
        decision: TradingDecision,
        target_weight: float,
        reason: str,
    ) -> TargetPosition:
        side = "LONG" if decision.action == DecisionAction.CONSIDER_LONG else "SHORT"
        return TargetPosition(
            symbol=decision.symbol,
            side=side,
            target_weight=round(max(0.0, min(target_weight, 1.0)), 6),
            confidence=decision.confidence,
            final_score=decision.score.final_score,
            reason=reason,
            metadata=decision.metadata or {},
        )
