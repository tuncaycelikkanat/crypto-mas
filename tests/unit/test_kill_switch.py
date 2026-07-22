from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.models.paper_account import PaperAccount
from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()



@pytest.fixture
def test_account(db_session):
    account = PaperAccount(
        name="kill_switch_account",
        exchange=Exchange.MOCK.value,
        base_currency="USDT",
        initial_balance=10000.0,
        cash_balance=10000.0,
        equity=10000.0,
    )
    db_session.add(account)
    db_session.commit()
    return account

@pytest.mark.asyncio
async def test_kill_switch_triggered_on_stale_data(db_session, test_account):
    now_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_provider = FixedTimeProvider(fixed_time=now_time)
    
    provider = MagicMock()
    provider.exchange = Exchange.MOCK
    provider.fetch_ohlcv = AsyncMock(return_value=[])
    
    service = TradingCycleService(
        db=db_session,
        market_provider=provider,
        time_provider=time_provider,
    )
    
    service.market_data_orchestrator.feature_service = MagicMock()
    
    # Simulate a stale snapshot
    stale_time = now_time - timedelta(minutes=90) # 1h timeframe + 15m delay = 75m max. 90m is stale.
    stale_snapshot = FeatureSnapshot(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.ONE_HOUR.value,
        timestamp=stale_time,
        available_at=stale_time,
        features_json={"close": 50000}
    )
    
    service.feature_snapshot_repository = MagicMock()
    service.feature_snapshot_repository.list_by_symbol.return_value = [stale_snapshot]
    service.strategy_orchestrator.feature_snapshot_repository = service.feature_snapshot_repository
    service.market_data_orchestrator.feature_snapshot_repository = service.feature_snapshot_repository
    
    with pytest.raises(Exception, match="STALE DATA DETECTED"):
        await service.run_cycle(
            account_name=test_account.name,
            symbols=["BTCUSDT"],
            timeframe=Timeframe.ONE_HOUR,
            trigger="TEST",
        )
        
    db_cycle = db_session.query(TradingCycle).order_by(TradingCycle.id.desc()).first()
    assert db_cycle is not None
    assert db_cycle.status == "FAILED"

@pytest.mark.asyncio
async def test_kill_switch_passes_on_fresh_data(db_session, test_account):
    now_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_provider = FixedTimeProvider(fixed_time=now_time)
    
    provider = MagicMock()
    provider.exchange = Exchange.MOCK
    provider.fetch_ohlcv = AsyncMock(return_value=[])
    
    service = TradingCycleService(
        db=db_session,
        market_provider=provider,
        time_provider=time_provider,
    )
    
    service.market_data_orchestrator.feature_service = MagicMock()
    
    # Simulate fresh snapshot
    fresh_time = now_time - timedelta(minutes=30) # 1h timeframe + 15m = 75m max. 30m is fresh.
    fresh_snapshot = FeatureSnapshot(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.ONE_HOUR.value,
        timestamp=fresh_time,
        available_at=fresh_time,
        features_json={"close": 50000}
    )
    
    service.feature_snapshot_repository = MagicMock()
    service.feature_snapshot_repository.list_by_symbol.return_value = [fresh_snapshot]
    service.strategy_orchestrator.feature_snapshot_repository = service.feature_snapshot_repository
    service.market_data_orchestrator.feature_snapshot_repository = service.feature_snapshot_repository
    
    # We also need to mock multi_agent to prevent errors later in the cycle
    service.multi_agent = MagicMock()
    service.multi_agent.evaluate.return_value = []
    
    from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
    from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
    queue = OrderExecutorQueue.get_instance()
    queue.sync_mode = True
    queue.set_broker_factory(lambda: PaperBrokerService(db_session))
    
    cycle = await service.run_cycle(
        account_name=test_account.name,
        symbols=["BTCUSDT"],
        timeframe=Timeframe.ONE_HOUR,
        trigger="TEST",
    )
    
    assert cycle.status == "COMPLETED"
