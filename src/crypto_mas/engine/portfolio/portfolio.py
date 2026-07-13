from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class PortfolioEngine:
    def __init__(
        self,
        max_positions: int = 10,
        max_gross_exposure: float = 0.85,
        min_confidence: float = 0.5,
        time_provider: TimeProvider | None = None,
    ) -> None:
        self.max_positions = max_positions
        self.max_gross_exposure = max_gross_exposure
        self.min_confidence = min_confidence
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
            if decision.action == DecisionAction.CONSIDER_LONG
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
                reason="No eligible long candidates found.",
                created_at=self.time_provider.now(),
            )

        total_score = sum(decision.score.final_score for decision in selected)

        if total_score <= 0:
            equal_weight = self.max_gross_exposure / len(selected)
            positions = [
                self._to_target_position(
                    decision=decision,
                    target_weight=equal_weight,
                    reason="Equal weighted because total score is zero.",
                )
                for decision in selected
            ]
        else:
            positions = [
                self._to_target_position(
                    decision=decision,
                    target_weight=(
                        self.max_gross_exposure * decision.score.final_score / total_score
                    ),
                    reason="Weight allocated proportionally to final_score.",
                )
                for decision in selected
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
        return TargetPosition(
            symbol=decision.symbol,
            target_weight=round(max(0.0, min(target_weight, 1.0)), 6),
            confidence=decision.confidence,
            final_score=decision.score.final_score,
            reason=reason,
        )
