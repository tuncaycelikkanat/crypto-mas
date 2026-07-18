import pytest
from datetime import datetime, UTC
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from crypto_mas.domain.models import *  # noqa
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.brokers.mock_adapter.market_data import MockMarketDataProvider
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    yield db
    db.close()

@pytest.mark.asyncio
async def test_run_full_trading_cycle(db_session):
    account_repo = PaperAccountRepository(db_session)
    account_repo.create_if_not_exists(
        name="test-account",
        exchange="MOCK",
        base_currency="USDT",
        initial_balance=Decimal("10000"),
    )
    
    provider = MockMarketDataProvider()
    
    service = TradingCycleService(
        db=db_session,
        market_provider=provider,
        strategy_mode="scalping",
    )
    
    cycle = await service.run_cycle(
        account_name="test-account",
        symbols=["BTCUSDT"],
        timeframe=Timeframe.FIFTEEN_MINUTES,
        strategy_name="multi_agent",
        trigger="TEST",
    )
    
    assert cycle is not None
    assert cycle.status == "COMPLETED"
    assert cycle.symbols_processed == 1
