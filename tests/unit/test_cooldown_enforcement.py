from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from crypto_mas.domain.models.paper_account import PaperAccount
from crypto_mas.domain.models.position import Position
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.value_objects.enums import PositionSide, PositionStatus
from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.paper_trading.execution_reporter import ExecutionReporter
from crypto_mas.services.paper_trading.mark_to_market import MarkToMarket
from crypto_mas.services.paper_trading.position_manager import PositionManager
from crypto_mas.services.paper_trading.risk_calculator import RiskCalculator
from crypto_mas.services.paper_trading.schemas import PaperExecutionStatus


@pytest.fixture
def cooldown_account(db_session: Session) -> PaperAccount:
    account = PaperAccount(
        name="cooldown_test_account",
        exchange=Exchange.MOCK.value,
        base_currency="USDT",
        initial_balance=Decimal("10000.00"),
        cash_balance=Decimal("10000.00"),
        equity=Decimal("10000.00"),
    )
    db_session.add(account)
    db_session.commit()
    return account


def test_position_manager_rejects_symbol_in_stop_loss_cooldown(db_session: Session, cooldown_account: PaperAccount):
    now = datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC)
    time_provider = FixedTimeProvider(fixed_time=now)
    
    # Create a position closed via STOP_LOSS 15 minutes ago (within 120 min cooldown)
    closed_pos = Position(
        account_name=cooldown_account.name,
        exchange=Exchange.MOCK.value,
        symbol="ALPINEUSDT",
        side=PositionSide.LONG.value,
        status=PositionStatus.CLOSED.value,
        quantity=Decimal("1000"),
        entry_price=Decimal("0.38"),
        current_price=Decimal("0.36"),
        notional_value=Decimal("360"),
        realized_pnl=Decimal("-20"),
        opened_at=now - timedelta(minutes=45),
        closed_at=now - timedelta(minutes=15),
        close_reason="STOP_LOSS",
    )
    db_session.add(closed_pos)
    
    # Add snapshot for current price
    snap = FeatureSnapshot(
        exchange=Exchange.MOCK.value,
        symbol="ALPINEUSDT",
        timeframe=Timeframe.FIFTEEN_MINUTES.value,
        timestamp=now,
        available_at=now,
        features_json={"close": 0.36, "volume": 1000000},
    )
    db_session.add(snap)
    db_session.commit()

    risk_calculator = RiskCalculator()
    reporter = ExecutionReporter(db_session, time_provider=time_provider, is_backtest=True)
    mark_to_market = MarkToMarket(db_session, risk_calculator, reporter, time_provider, is_backtest=True)
    manager = PositionManager(
        db=db_session,
        risk_calculator=risk_calculator,
        reporter=reporter,
        mark_to_market=mark_to_market,
        time_provider=time_provider,
        is_backtest=True,
    )

    # Attempt to buy ALPINEUSDT
    target = PortfolioTarget(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        target_positions=[
            TargetPosition(
                symbol="ALPINEUSDT",
                side="LONG",
                target_weight=0.2,
                confidence=0.8,
                final_score=0.85,
                reason="Test signal"
            )
        ],
        cash_weight=0.8,
        gross_exposure=0.2,
        reason="Test buy target",
        created_at=now,
    )

    report = manager.execute_target_portfolio(cooldown_account, target)

    assert len(report.executed) == 0
    assert len(report.skipped) == 1
    assert report.skipped[0].symbol == "ALPINEUSDT"
    assert report.skipped[0].status == PaperExecutionStatus.SKIPPED
    assert "Stop-Loss Cooldown" in report.skipped[0].reason
