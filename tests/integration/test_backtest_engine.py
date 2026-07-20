from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from crypto_mas.infrastructure.db.base import Base
from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


@pytest.fixture
def db_session() -> AsyncGenerator[Session, None]:  # type: ignore
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.mark.asyncio
async def test_run_backtest(db_session: Session) -> None:
    # Setup test parameters
    job_id = "test-job-123"
    exchange = Exchange.MOCK
    symbols = ["BTCUSDT"]
    timeframe = Timeframe.ONE_HOUR
    
    # 4 hours of test
    start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    end_time = start_time + timedelta(hours=4)
    
    service = BacktestEngineService(db=db_session)
    
    result = await service.run_backtest(
        job_id=job_id,
        exchange=exchange,
        symbols=symbols,
        timeframe=timeframe,
        strategy_name="macd_cross",
        start_time=start_time,
        end_time=end_time,
        initial_balance=1000.0,
    )
    
    assert result is not None
    assert result.status == "COMPLETED"
    assert result.job_id == job_id
    assert result.total_trades >= 0
    assert result.final_equity is not None
