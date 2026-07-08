from datetime import datetime, UTC

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.services.reporting_service.analytics import PerformanceAnalytics

@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_performance_analytics(db_session: Session) -> None:
    # Seed mock cycles
    account_name = "test-account-1"
    
    cycle1 = TradingCycle(
        account_name=account_name,
        exchange="MOCK",
        timeframe="1h",
        status="COMPLETED",
        trigger="TEST",
        started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
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
        trades_executed=3,
        cycle_pnl=700.0,
        ending_equity=11000.0,
    )
    
    db_session.add_all([cycle1, cycle2, cycle3])
    db_session.commit()
    
    analytics = PerformanceAnalytics(db_session)
    metrics = analytics.calculate_for_account(account_name, 10000.0)
    
    assert metrics.total_cycles == 3
    assert metrics.total_trades == 6
    assert metrics.winning_cycles == 2
    assert metrics.losing_cycles == 1
    assert metrics.win_rate == 2 / 3
    assert metrics.total_pnl == 1000.0
    assert metrics.peak_equity == 11000.0
    
    # Peak equity drops from 10500 to 10300 during cycle2
    # Drawdown = (10500 - 10300) / 10500 = 200 / 10500 ≈ 0.019
    expected_dd = 200.0 / 10500.0
    assert abs(metrics.max_drawdown - expected_dd) < 0.001

def test_performance_analytics_empty(db_session: Session) -> None:
    analytics = PerformanceAnalytics(db_session)
    metrics = analytics.calculate_for_account("empty-account", 10000.0)
    
    assert metrics.total_cycles == 0
    assert metrics.total_trades == 0
    assert metrics.win_rate == 0.0
    assert metrics.total_pnl == 0.0
    assert metrics.max_drawdown == 0.0
    assert metrics.peak_equity == 10000.0
