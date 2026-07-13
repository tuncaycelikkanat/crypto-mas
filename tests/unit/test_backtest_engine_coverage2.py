from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


@pytest.mark.asyncio
async def test_run_backtest_success():
    db = MagicMock()
    service = BacktestEngineService(db)
    
    with patch("crypto_mas.services.backtesting.engine.get_market_data_provider") as mock_provider, \
         patch("crypto_mas.services.backtesting.engine.HistoricalFetcherService") as mock_fetcher, \
         patch("crypto_mas.services.backtesting.engine.PaperAccountRepository") as mock_account_repo, \
         patch("crypto_mas.services.backtesting.engine.TradingCycleService") as mock_cycle_service, \
         patch("crypto_mas.services.reporting_service.analytics.PerformanceAnalytics") as mock_analytics:
         
        # Setup mocks
        mock_fetcher.return_value.backfill_universe = AsyncMock()
        
        cycle_mock = MagicMock()
        cycle_mock.trades_executed = 2
        mock_cycle_service.return_value.run_cycle = AsyncMock(return_value=cycle_mock)
        # Mock timedelta
        mock_cycle_service._get_timedelta.return_value = __import__("datetime").timedelta(minutes=15)
        
        analytics_mock = MagicMock()
        analytics_mock.total_trades = 5
        analytics_mock.total_pnl = 100.0
        analytics_mock.win_rate = 60.0
        analytics_mock.max_drawdown = 5.0
        mock_analytics.return_value.calculate_for_account.return_value = analytics_mock
        
        # Test final equity from cycle logic
        last_cycle = MagicMock()
        last_cycle.ending_equity = 11000.0
        db.scalars.return_value.first.return_value = last_cycle
        
        start_time = datetime(2023, 1, 1, tzinfo=UTC)
        end_time = datetime(2023, 1, 1, 1, 0, 0, tzinfo=UTC) # 1 hour
        
        result = await service.run_backtest(
            job_id="test_job",
            exchange=Exchange.BINANCE,
            symbols=["BTCUSDT"],
            timeframe=Timeframe.FIFTEEN_MINUTES,
            strategy_name="macd_cross",
            start_time=start_time,
            end_time=end_time,
            initial_balance=10000.0
        )
        
        assert result.status == "COMPLETED"
        assert result.final_equity == 11000.0
        assert result.total_trades == 5
        assert result.win_rate == 60.0
        db.commit.assert_called()

@pytest.mark.asyncio
async def test_run_backtest_failure():
    db = MagicMock()
    service = BacktestEngineService(db)
    
    with patch("crypto_mas.services.backtesting.engine.get_market_data_provider", side_effect=Exception("API Error")):
        start_time = datetime(2023, 1, 1, tzinfo=UTC)
        end_time = datetime(2023, 1, 1, 1, 0, 0, tzinfo=UTC)
        
        with pytest.raises(Exception):
            await service.run_backtest(
                job_id="test_job_fail",
                exchange=Exchange.BINANCE,
                symbols=["BTCUSDT"],
                timeframe=Timeframe.FIFTEEN_MINUTES,
                strategy_name="macd_cross",
                start_time=start_time,
                end_time=end_time,
                initial_balance=10000.0
            )
