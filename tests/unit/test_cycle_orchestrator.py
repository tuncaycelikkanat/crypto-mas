import pytest
from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from crypto_mas.domain.models.paper_account import PaperAccount
from crypto_mas.infrastructure.db.base import Base

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

from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService
from unittest.mock import AsyncMock, MagicMock
from crypto_mas.domain.models.paper_account import PaperAccount

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
    
    cycle = await service.run_cycle(
        account_name=test_account.name,
        symbols=symbols,
        timeframe=timeframe,
        trigger="TEST",
    )
    
    assert cycle is not None
    assert cycle.status == "COMPLETED"
    assert cycle.account_name == test_account.name
    assert cycle.exchange == Exchange.MOCK.value
    assert cycle.symbols_processed == 2
    assert cycle.trigger == "TEST"
    
    # DB kontrolü
    db_cycle = db_session.get(TradingCycle, cycle.id)
    assert db_cycle is not None
    assert db_cycle.status == "COMPLETED"
