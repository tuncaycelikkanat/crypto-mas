from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crypto_mas.apps.scheduler.main import main, scheduled_trading_cycle


@pytest.mark.asyncio
async def test_scheduled_trading_cycle_success():
    with patch("crypto_mas.apps.scheduler.main.SessionLocal") as mock_session_class, \
         patch("crypto_mas.apps.scheduler.main.get_market_data_provider") as _, \
         patch("crypto_mas.apps.scheduler.main.TradingCycleService") as mock_service_class, \
         patch("crypto_mas.apps.scheduler.main.settings") as mock_settings:
        
        mock_settings.trading_mode = "PAPER"
        mock_settings.scheduled_timeframe = "15m"
        mock_settings.scheduled_symbols = ["BTCUSDT"]
        
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_service = AsyncMock()
        mock_cycle = MagicMock()
        mock_cycle.id = 1
        mock_cycle.status = "COMPLETED"
        mock_cycle.cycle_pnl = 10.0
        mock_service.run_cycle.return_value = mock_cycle
        mock_service_class.return_value = mock_service
        
        await scheduled_trading_cycle()
        
        mock_session.close.assert_called_once()
        mock_service.run_cycle.assert_called_once()

@pytest.mark.asyncio
async def test_scheduled_trading_cycle_failure():
    with patch("crypto_mas.apps.scheduler.main.SessionLocal") as mock_session_class, \
         patch("crypto_mas.apps.scheduler.main.get_market_data_provider"), \
         patch("crypto_mas.apps.scheduler.main.TradingCycleService") as mock_service_class:
        
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_service_class.side_effect = Exception("DB Error")
        
        await scheduled_trading_cycle()
        
        mock_session.close.assert_called_once()

def test_main():
    with patch("crypto_mas.apps.scheduler.main.AsyncIOScheduler") as mock_scheduler_class, \
         patch("crypto_mas.apps.scheduler.main.asyncio.get_event_loop") as mock_get_loop, \
         patch("crypto_mas.apps.scheduler.main.settings") as mock_settings:
        
        mock_settings.schedule_cron = "* * * * *"
        
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        mock_loop = MagicMock()
        # Simulate KeyboardInterrupt to break the infinite loop
        mock_loop.run_forever.side_effect = KeyboardInterrupt()
        mock_get_loop.return_value = mock_loop
        
        main()
        
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
        mock_scheduler.shutdown.assert_called_once()
