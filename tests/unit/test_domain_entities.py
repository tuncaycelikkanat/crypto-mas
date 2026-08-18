from datetime import UTC, datetime
from decimal import Decimal

import pytest

from crypto_mas.domain.entities import (
    DomainPosition,
    DrawdownLimitState,
    PortfolioState,
    RankedCandidate,
    RiskShieldEvaluation,
    RiskShieldStatus,
    SignalCandidate,
)


def test_domain_position_properties():
    opened_at = datetime.now(UTC)
    long_pos = DomainPosition(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=Decimal("50000"),
        quantity=Decimal("0.5"),
        current_price=Decimal("55000"),
        target_weight=0.25,
        opened_at=opened_at,
    )

    assert long_pos.notional_value == Decimal("27500.0")
    assert long_pos.unrealized_pnl == Decimal("2500.0")
    assert pytest.approx(long_pos.return_pct, 0.01) == 10.0

    short_pos = DomainPosition(
        symbol="ETHUSDT",
        side="SHORT",
        entry_price=Decimal("3000"),
        quantity=Decimal("2.0"),
        current_price=Decimal("2700"),
        target_weight=0.20,
        opened_at=opened_at,
    )

    assert short_pos.notional_value == Decimal("5400.0")
    assert short_pos.unrealized_pnl == Decimal("600.0")
    assert pytest.approx(short_pos.return_pct, 0.01) == 10.0


def test_portfolio_state_exposure_and_limits():
    opened_at = datetime.now(UTC)
    pos1 = DomainPosition(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=Decimal("50000"),
        quantity=Decimal("0.1"),
        current_price=Decimal("50000"),
        target_weight=0.5,
        opened_at=opened_at,
    )

    state = PortfolioState(
        account_name="main_paper",
        total_equity=Decimal("10000"),
        cash_balance=Decimal("5000"),
        positions={"BTCUSDT": pos1},
    )

    assert state.open_position_count == 1
    assert pytest.approx(state.gross_exposure, 0.01) == 0.50
    assert pytest.approx(state.cash_weight, 0.01) == 0.50

    # Max positions limit
    assert state.can_open_position(max_positions=2, max_gross_exposure=0.85, proposed_weight=0.20) is True
    assert state.can_open_position(max_positions=1, max_gross_exposure=0.85, proposed_weight=0.20) is False
    # Max gross exposure limit
    assert state.can_open_position(max_positions=5, max_gross_exposure=0.60, proposed_weight=0.20) is False


def test_risk_shield_and_drawdown_entities():
    evaluation = RiskShieldEvaluation(
        symbol="BTCUSDT",
        status=RiskShieldStatus.PASS,
        btc_crash_shield_triggered=False,
    )
    assert evaluation.is_safe_to_execute is True

    blocked_eval = RiskShieldEvaluation(
        symbol="ETHUSDT",
        status=RiskShieldStatus.BLOCKED,
        btc_crash_shield_triggered=True,
        reason="BTC crash filter active",
    )
    assert blocked_eval.is_safe_to_execute is False

    dd_state = DrawdownLimitState(
        peak_equity=10000.0,
        current_equity=8800.0,
        max_drawdown_limit_pct=15.0,
    )
    assert pytest.approx(dd_state.current_drawdown_pct, 0.01) == 12.0
    assert dd_state.is_breached is False

    breached_state = DrawdownLimitState(
        peak_equity=10000.0,
        current_equity=8000.0,
        max_drawdown_limit_pct=15.0,
    )
    assert pytest.approx(breached_state.current_drawdown_pct, 0.01) == 20.0
    assert breached_state.is_breached is True


def test_signal_and_ranked_candidate():
    candidate = SignalCandidate(
        symbol="SOLUSDT",
        action="CONSIDER_LONG",
        confidence_score=0.85,
        market_regime="BULL_TREND",
        reason="Strong trend",
        suggested_weight=0.20,
    )
    assert candidate.is_actionable is True

    ranked = RankedCandidate(candidate=candidate, rank=1, group_category="L1")
    assert ranked.rank == 1
    assert ranked.group_category == "L1"
