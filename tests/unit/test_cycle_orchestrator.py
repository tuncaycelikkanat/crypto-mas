from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session

from crypto_mas.domain.models.paper_account import PaperAccount




from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService
from crypto_mas.domain.value_objects.enums import CycleStatus


@pytest.fixture
def test_account(db_session: Session) -> PaperAccount:
    account = PaperAccount(
        name="test_cycle_account",
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
async def test_run_cycle_success(db_session: Session, test_account: PaperAccount) -> None:
    time_provider = FixedTimeProvider(fixed_time=datetime(2026, 1, 1, 12, 0, 0))
    
    provider = MagicMock()
    provider.exchange = Exchange.MOCK
    provider.fetch_ohlcv = AsyncMock(return_value=[])
    
    # We will simulate 60 candles in the mock provider so that feature calculator can run.
    # Actually, MockMarketDataProvider generates candles on the fly for any requested range.
    
    service = TradingCycleService(
        db=db_session,
        market_provider=provider,
        time_provider=time_provider,
    )
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = Timeframe.ONE_HOUR
    
    from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
    from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
    queue = OrderExecutorQueue.get_instance()
    queue.sync_mode = True
    queue.set_broker_factory(lambda: PaperBrokerService(db_session))

    cycle = await service.run_cycle(
        account_name=test_account.name,
        symbols=symbols,
        timeframe=timeframe,
        trigger="TEST",
    )
    
    assert cycle is not None
    assert cycle.status == CycleStatus.COMPLETED
    assert cycle.account_name == test_account.name
    assert cycle.exchange == Exchange.MOCK.value
    assert cycle.symbols_processed == 2
    assert cycle.trigger == "TEST"
    
    # DB kontrolü
    db_cycle = db_session.get(TradingCycle, cycle.id)
    assert db_cycle is not None
    assert db_cycle.status == CycleStatus.COMPLETED

@pytest.mark.asyncio
async def test_run_cycle_account_not_found(db_session: Session) -> None:
    time_provider = FixedTimeProvider(fixed_time=datetime(2026, 1, 1, 12, 0, 0))
    provider = MagicMock()
    provider.exchange = Exchange.MOCK
    service = TradingCycleService(db=db_session, market_provider=provider, time_provider=time_provider)

    from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
    from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
    queue = OrderExecutorQueue.get_instance()
    queue.sync_mode = True
    queue.set_broker_factory(lambda: PaperBrokerService(db_session))
    
    with pytest.raises(ValueError, match="Paper account not found"):
        await service.run_cycle(
            account_name="nonexistent",
            symbols=["BTCUSDT"],
            timeframe=Timeframe.ONE_HOUR,
            trigger="TEST",
        )

@pytest.mark.asyncio
async def test_run_cycle_exception_handling(db_session: Session, test_account: PaperAccount) -> None:
    time_provider = FixedTimeProvider(fixed_time=datetime(2026, 1, 1, 12, 0, 0))
    provider = MagicMock()
    provider.exchange = Exchange.MOCK
    provider.fetch_ohlcv.side_effect = Exception("Simulated crash")
    
    service = TradingCycleService(db=db_session, market_provider=provider, time_provider=time_provider)
    
    # We must mock feature_service to avoid real feature calculation
    service.market_data_orchestrator.feature_service = MagicMock()
    service.market_data_orchestrator.feature_service.calculate_and_store.side_effect = Exception("Crash inside cycle")
    
    with pytest.raises(Exception, match="Crash inside cycle"):
        await service.run_cycle(
            account_name=test_account.name,
            symbols=["BTCUSDT"],
            timeframe=Timeframe.ONE_HOUR,
        )
    
    # we have to query the latest cycle from DB since run_cycle raised
    db_cycle = db_session.query(TradingCycle).order_by(TradingCycle.id.desc()).first()
    assert db_cycle is not None
    assert db_cycle.status == CycleStatus.FAILED
