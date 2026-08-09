"""
Unit tests for PerformanceAnalytics.

The new analytics engine counts trades from the Trade table.
Tests seed both TradingCycle rows (for equity curve / win_rate) and
Trade rows (for PnL / win_rate / ratio calculations).
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from crypto_mas.domain.models.trade import Trade
from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.services.reporting_service.analytics import PerformanceAnalytics



def test_performance_analytics(db_session: Session) -> None:
    account_name = "test-account-1"

    # Seed cycles (for equity curve & winning_cycles counts)
    cycle1 = TradingCycle(
        account_name=account_name,
        exchange="MOCK",
        timeframe="1h",
        status="COMPLETED",
        trigger="TEST",
        started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
        finished_at=datetime(2023, 1, 1, 12, 30, 0, tzinfo=UTC),
        trades_executed=2,
        cycle_pnl=500.0,
        ending_equity=10500.0,
    )
    cycle2 = TradingCycle(
        account_name=account_name,
        exchange="MOCK",
        timeframe="1h",
        status="COMPLETED",
        trigger="TEST",
        started_at=datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC),
        finished_at=datetime(2023, 1, 1, 13, 30, 0, tzinfo=UTC),
        trades_executed=1,
        cycle_pnl=-200.0,
        ending_equity=10300.0,
    )
    cycle3 = TradingCycle(
        account_name=account_name,
        exchange="MOCK",
        timeframe="1h",
        status="COMPLETED",
        trigger="TEST",
        started_at=datetime(2023, 1, 1, 14, 0, 0, tzinfo=UTC),
        finished_at=datetime(2023, 1, 1, 14, 30, 0, tzinfo=UTC),
        trades_executed=3,
        cycle_pnl=700.0,
        ending_equity=11000.0,
    )
    db_session.add_all([cycle1, cycle2, cycle3])

    # Seed 6 closed trades (realized_pnl set → they count as closed)
    trade_data = [
        # Cycle 1: 2 winning trades
        ("BTCUSDT", "SELL", 200.0),
        ("ETHUSDT", "SELL", 300.0),
        # Cycle 2: 1 losing trade
        ("BTCUSDT", "SELL", -200.0),
        # Cycle 3: 3 trades
        ("BTCUSDT", "SELL", 400.0),
        ("SOLUSDT", "SELL", 150.0),
        ("ETHUSDT", "SELL", 150.0),
    ]
    for i, (sym, side, pnl) in enumerate(trade_data):
        db_session.add(Trade(
            account_name=account_name,
            exchange="MOCK",
            symbol=sym,
            side=side,
            quantity=0.1,
            price=50000.0,
            notional=5000.0,
            realized_pnl=pnl,
            executed_at=datetime(2023, 1, 1, 12 + i // 2, i % 2 * 15, 0, tzinfo=UTC),
            reason="test",
            strategy_id="test",
        ))

    db_session.commit()

    analytics = PerformanceAnalytics(db_session)
    metrics = analytics.calculate_for_account(account_name, 10000.0)

    assert metrics.total_cycles == 3
    assert metrics.total_trades == 6           # from Trade table
    assert metrics.winning_cycles == 2         # from TradingCycle.cycle_pnl
    assert metrics.losing_cycles == 1

    # win_rate = 5 winning / 6 total
    assert abs(metrics.win_rate - 5 / 6) < 0.001

    # total_pnl = sum of all realized pnl = 200+300-200+400+150+150 = 1000
    assert abs(metrics.total_pnl - 1000.0) < 0.01

    assert metrics.peak_equity == 11000.0

    # Drawdown: equity drops from 10500 → 10300 during cycle2
    expected_dd = 200.0 / 10500.0
    assert abs(metrics.max_drawdown - expected_dd) < 0.001

    # Profit factor > 1 (gross_profit > gross_loss)
    assert metrics.profit_factor > 1.0

    # Expectancy should be positive
    assert metrics.expectancy > 0


def test_performance_analytics_empty(db_session: Session) -> None:
    analytics = PerformanceAnalytics(db_session)
    metrics = analytics.calculate_for_account("empty-account", 10000.0)

    assert metrics.total_cycles == 0
    assert metrics.total_trades == 0
    assert metrics.win_rate == 0.0
    assert metrics.total_pnl == 0.0
    assert metrics.max_drawdown == 0.0
    assert metrics.peak_equity == 10000.0
