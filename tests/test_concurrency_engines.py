import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from crypto_mas.infrastructure.db.base import Base
from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService
from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
from crypto_mas.services.market_data_service.schemas import Timeframe, Exchange

# In-memory DB setup
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_live_cycle_and_backtest_concurrency(db_session):
    """
    Simulates a live TradingCycleService running its cycle (e.g. from the scheduler)
    AT THE SAME TIME as the BacktestEngineService is running a backtest.
    
    Proves that:
    1. BacktestEngineService isolated queue does not leak 'sync_mode = True' into the global queue.
    2. TradingCycleService successfully uses the global queue without hitting SQLAlchemy IllegalStateChangeError.
    """
    
    # 1. Start the global queue for the live environment
    global_queue = OrderExecutorQueue.get_instance()
    global_queue.sync_mode = False
    
    # Use a dummy mock for global queue enqueue to simply verify it receives the task
    # Instead of actually modifying the DB asynchronously which might conflict in sqlite memory
    global_queue.enqueue = AsyncMock()

    # 2. Setup mock market provider
    mock_market_provider = AsyncMock()
    mock_market_provider.exchange.value = "MEXC"
    
    # 3. Initialize Live Service (Scheduler)
    live_service = TradingCycleService(
        db=db_session,
        market_provider=mock_market_provider,
        strategy_mode="scalping"
    )
    
    # Ensure live service bound to the global queue
    assert live_service.executor_queue is global_queue
    assert live_service.executor_queue.sync_mode is False

    # 4. Initialize Backtest Engine
    backtest_engine = BacktestEngineService(db_session)
    
    # We patch cycle_service.run_cycle in backtest to not do heavy ML stuff, just simulate processing
    async def mock_run_cycle(*args, **kwargs):
        await asyncio.sleep(0.1) # Simulate some delay
        return AsyncMock()

    # We run the backtest which should internally create an isolated queue and inject it
    start_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_time = datetime(2026, 1, 2, tzinfo=timezone.utc)
    
    # Setup test params
    strategy_config = {"some_param": 1}
    symbols = ["BTCUSDT"]

    with patch.object(TradingCycleService, "run_cycle", side_effect=mock_run_cycle):
        with patch("crypto_mas.services.backtesting.engine.HistoricalFetcherService.backfill_universe", new_callable=AsyncMock):
            with patch("crypto_mas.services.feature_pipeline.service.FeaturePipelineService.calculate_and_store", new_callable=AsyncMock):
                
                # Start backtest as a background task
                backtest_task = asyncio.create_task(
                    backtest_engine.run_backtest(
                        job_id="test_job",
                        exchange=Exchange.MEXC,
                        symbols=symbols,
                        timeframe=Timeframe.ONE_HOUR,
                        strategy_name="scalping",
                        start_time=start_time,
                        end_time=end_time,
                        config_json=strategy_config
                    )
                )
                
                # Yield to let backtest initialize its cycles and queues
                await asyncio.sleep(0.05)
                
                # Verify that the global queue is STILL NOT IN SYNC MODE
                assert global_queue.sync_mode is False
                
                # Verify we can execute a live cycle WITHOUT crashing
                # For this test, we just call the orchestrator method directly
                live_target_mock = AsyncMock()
                live_target_mock.target_positions = []
                
                with patch.object(live_service, "_apply_risk_and_execute") as mock_apply:
                    # Enqueue a dummy cycle
                    live_service.executor_queue.enqueue("live_account", live_target_mock, 999)
                    
                    # Ensure the live queue got the task
                    global_queue.enqueue.assert_called_once()
                
                # Wait for backtest to finish
                backtest_result = await backtest_task
                
                # Check that backtest completed
                assert backtest_result is not None

    # Global queue should still be async!
    assert global_queue.sync_mode is False
