from datetime import UTC, datetime

from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.engine.risk.risk import RiskEngine
from crypto_mas.engine.risk import RiskDecisionStatus, RiskLimits
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def _make_target(weights: list[float]) -> PortfolioTarget:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)

    positions = [
        TargetPosition(
            symbol=f"COIN{index}USDT",
            target_weight=weight,
            confidence=0.5,
            final_score=0.5,
            reason="test",
        )
        for index, weight in enumerate(weights)
    ]

    gross_exposure = round(sum(weights), 6)

    return PortfolioTarget(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        target_positions=positions,
        cash_weight=round(max(0.0, 1.0 - gross_exposure), 6),
        gross_exposure=gross_exposure,
        reason="test",
        created_at=created_at,
    )


def test_risk_engine_approves_valid_target() -> None:
    target = _make_target([0.30, 0.30, 0.30])

    assessment = RiskEngine(
        limits=RiskLimits(
            max_positions=3,
            max_gross_exposure=0.90,
            max_position_weight=0.35,
            min_cash_weight=0.10,
        )
    ).assess(target)

    assert assessment.status == RiskDecisionStatus.APPROVED
    assert assessment.approved_target is not None
    assert assessment.issues == []


def test_risk_engine_reduces_position_weights() -> None:
    target = _make_target([0.50, 0.30, 0.20])

    assessment = RiskEngine(
        limits=RiskLimits(
            max_positions=3,
            max_gross_exposure=0.90,
            max_position_weight=0.35,
            min_cash_weight=0.10,
        )
    ).assess(target)

    assert assessment.status == RiskDecisionStatus.REDUCED
    assert assessment.approved_target is not None
    assert assessment.approved_target.gross_exposure <= 0.90
    assert all(
        position.target_weight <= 0.35 for position in assessment.approved_target.target_positions
    )


def test_risk_engine_reduces_when_too_many_positions_are_requested() -> None:
    target = _make_target([0.25, 0.25, 0.25, 0.15])

    assessment = RiskEngine(
        limits=RiskLimits(
            max_positions=2,
            max_gross_exposure=0.90,
            max_position_weight=0.35,
            min_cash_weight=0.10,
        )
    ).assess(target)

    assert assessment.status == RiskDecisionStatus.REDUCED
    assert assessment.approved_target is not None
    assert len(assessment.approved_target.target_positions) <= 2
    assert assessment.approved_target.gross_exposure <= 0.90
    assert assessment.approved_target.cash_weight >= 0.10
