from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.engine.risk import (
    RiskAssessment,
    RiskCheckIssue,
    RiskDecisionStatus,
    RiskLimits,
)


class RiskEngine:
    EPSILON = 1e-9

    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    def assess(self, target: PortfolioTarget) -> RiskAssessment:
        issues = self._collect_issues(target)

        if not issues:
            return RiskAssessment(
                status=RiskDecisionStatus.APPROVED,
                approved_target=target,
                original_target=target,
                issues=[],
                reason="Portfolio target approved by risk engine.",
            )

        reduced_target = self._try_reduce(target)

        reduced_issues = self._collect_issues(reduced_target)

        if not reduced_issues:
            return RiskAssessment(
                status=RiskDecisionStatus.REDUCED,
                approved_target=reduced_target,
                original_target=target,
                issues=issues,
                reason="Portfolio target was reduced to satisfy risk limits.",
            )

        return RiskAssessment(
            status=RiskDecisionStatus.REJECTED,
            approved_target=None,
            original_target=target,
            issues=issues,
            reason="Portfolio target rejected because risk limits could not be satisfied.",
        )

    def _collect_issues(self, target: PortfolioTarget) -> list[RiskCheckIssue]:
        issues: list[RiskCheckIssue] = []

        if len(target.target_positions) > self.limits.max_positions:
            issues.append(
                RiskCheckIssue(
                    code="MAX_POSITIONS_EXCEEDED",
                    message=(
                        f"Target has {len(target.target_positions)} positions, "
                        f"limit is {self.limits.max_positions}."
                    ),
                )
            )

        if target.gross_exposure > self.limits.max_gross_exposure + self.EPSILON:
            issues.append(
                RiskCheckIssue(
                    code="MAX_GROSS_EXPOSURE_EXCEEDED",
                    message=(
                        f"Gross exposure {target.gross_exposure:.4f} exceeds "
                        f"limit {self.limits.max_gross_exposure:.4f}."
                    ),
                )
            )

        if target.cash_weight < self.limits.min_cash_weight - self.EPSILON:
            issues.append(
                RiskCheckIssue(
                    code="MIN_CASH_WEIGHT_VIOLATED",
                    message=(
                        f"Cash weight {target.cash_weight:.4f} is below "
                        f"minimum {self.limits.min_cash_weight:.4f}."
                    ),
                )
            )

        for position in target.target_positions:
            if position.target_weight > self.limits.max_position_weight + self.EPSILON:
                issues.append(
                    RiskCheckIssue(
                        code="MAX_POSITION_WEIGHT_EXCEEDED",
                        message=(
                            f"{position.symbol} target weight {position.target_weight:.4f} "
                            f"exceeds limit {self.limits.max_position_weight:.4f}."
                        ),
                    )
                )

        return issues

    def _try_reduce(self, target: PortfolioTarget) -> PortfolioTarget:
        selected_positions = target.target_positions[: self.limits.max_positions]

        reduced_positions = [
            TargetPosition(
                symbol=position.symbol,
                target_weight=min(position.target_weight, self.limits.max_position_weight),
                confidence=position.confidence,
                final_score=position.final_score,
                reason=f"{position.reason} Risk-adjusted.",
            )
            for position in selected_positions
        ]

        gross_exposure = sum(position.target_weight for position in reduced_positions)

        if gross_exposure > self.limits.max_gross_exposure:
            scale = self.limits.max_gross_exposure / gross_exposure

            reduced_positions = [
                TargetPosition(
                    symbol=position.symbol,
                    target_weight=round(position.target_weight * scale, 10),
                    confidence=position.confidence,
                    final_score=position.final_score,
                    reason=f"{position.reason} Scaled by risk engine.",
                )
                for position in reduced_positions
            ]

        gross_exposure = round(sum(position.target_weight for position in reduced_positions), 10)
        cash_weight = round(max(0.0, 1.0 - gross_exposure), 10)

        if cash_weight < self.limits.min_cash_weight:
            allowed_exposure = 1.0 - self.limits.min_cash_weight

            if gross_exposure > 0:
                scale = allowed_exposure / gross_exposure

                reduced_positions = [
                    TargetPosition(
                        symbol=position.symbol,
                        target_weight=round(position.target_weight * scale, 10),
                        confidence=position.confidence,
                        final_score=position.final_score,
                        reason=f"{position.reason} Scaled for minimum cash.",
                    )
                    for position in reduced_positions
                ]

        gross_exposure = round(sum(position.target_weight for position in reduced_positions), 10)
        cash_weight = round(max(0.0, 1.0 - gross_exposure), 10)

        return PortfolioTarget(
            exchange=target.exchange,
            timeframe=target.timeframe,
            target_positions=reduced_positions,
            cash_weight=cash_weight,
            gross_exposure=gross_exposure,
            reason=f"{target.reason} Risk-adjusted target.",
            created_at=target.created_at,
        )
