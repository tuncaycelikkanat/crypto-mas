from datetime import UTC, datetime

import pytest

from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.engine.risk import RiskDecisionStatus, RiskLimits
from crypto_mas.engine.risk.risk import RiskEngine
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


@pytest.fixture
def risk_engine():
    limits = RiskLimits(
        max_positions=3,
        max_gross_exposure=0.50,
        max_position_weight=0.10,
        min_cash_weight=0.50
    )
    return RiskEngine(limits=limits)

def create_target(positions: list[dict]) -> PortfolioTarget:
    target_positions = [
        TargetPosition(
            symbol=p["symbol"],
            target_weight=p["weight"],
            confidence=0.8,
            final_score=0.8,
            reason="test"
        )
        for p in positions
    ]
    gross = sum(p["weight"] for p in positions)
    return PortfolioTarget(
        exchange=Exchange("BINANCE"),
        timeframe=Timeframe("15m"),
        target_positions=target_positions,
        cash_weight=1.0 - gross,
        gross_exposure=gross,
        reason="test target",
        created_at=datetime.now(UTC)
    )

def test_risk_engine_approves_safe_portfolio(risk_engine):
    target = create_target([
        {"symbol": "BTCUSDT", "weight": 0.10},
        {"symbol": "ETHUSDT", "weight": 0.05}
    ])
    
    assessment = risk_engine.assess(target)
    
    assert assessment.status == RiskDecisionStatus.APPROVED
    assert len(assessment.issues) == 0
    assert assessment.approved_target.gross_exposure == pytest.approx(0.15)

def test_risk_engine_reduces_overweight_position(risk_engine):
    # One position wants 20%, but limit is 10%
    target = create_target([
        {"symbol": "BTCUSDT", "weight": 0.20}
    ])
    
    assessment = risk_engine.assess(target)
    
    assert assessment.status == RiskDecisionStatus.REDUCED
    assert len(assessment.issues) == 1
    assert assessment.issues[0].code == "MAX_POSITION_WEIGHT_EXCEEDED"
    assert assessment.approved_target.target_positions[0].target_weight == 0.10

def test_risk_engine_reduces_excess_gross_exposure(risk_engine):
    # 6 positions with 10% each = 60% gross. Limit is 50%, max positions is 3.
    target = create_target([
        {"symbol": f"COIN{i}", "weight": 0.10} for i in range(6)
    ])
    
    assessment = risk_engine.assess(target)
    
    assert assessment.status == RiskDecisionStatus.REDUCED
    # Should slice to 3 positions due to max_positions=3 limit.
    # 3 * 0.10 = 0.30, which is < 0.50 gross limit.
    assert len(assessment.approved_target.target_positions) == 3
    assert assessment.approved_target.gross_exposure == 0.30

def test_risk_engine_reduces_gross_exposure_scaling(risk_engine):
    # Set limit to max_gross = 0.15
    risk_engine.limits.max_gross_exposure = 0.15
    target = create_target([
        {"symbol": "BTCUSDT", "weight": 0.10},
        {"symbol": "ETHUSDT", "weight": 0.10}
    ])
    # Total requested is 0.20. Limit is 0.15. Needs scaling down.
    assessment = risk_engine.assess(target)
    
    assert assessment.status == RiskDecisionStatus.REDUCED
    assert assessment.approved_target.gross_exposure <= 0.15
    # Should scale down proportionally: 0.15 / 0.20 = 0.75 ratio
    assert assessment.approved_target.target_positions[0].target_weight == pytest.approx(0.075)
    assert assessment.approved_target.target_positions[1].target_weight == pytest.approx(0.075)
