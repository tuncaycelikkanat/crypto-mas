from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crypto_mas.services.scheduler_service import SchedulerService


def test_is_bot_running_scheduler_not_running():
    service = SchedulerService()
    service._scheduler = MagicMock()
    service._scheduler.running = False
    
    assert service.is_bot_running("bot_1") is False

def test_start_bot_already_running():
    service = SchedulerService()
    service._scheduler = MagicMock()
    service._scheduler.running = True
    job_mock = MagicMock()
    job_mock.id = "bot_1"
    job_mock.next_run_time.isoformat.return_value = "2023-01-01T00:00:00+00:00"
    job_mock.trigger = "interval"
    job_mock.args = [["BTCUSDT"], "swing", "BINANCE"]
    
    service._scheduler.get_job.return_value = job_mock
    service._scheduler.get_jobs.return_value = [job_mock]
    
    status = service.start_bot("bot_1")
    assert status == {"bots": [{"bot_id": "bot_1", "status": "RUNNING", "next_run_time": "2023-01-01T00:00:00+00:00", "trigger": "interval", "symbols": ["BTCUSDT"], "mode": "swing", "exchange": "BINANCE", "risk_level": 50}]}

def test_start_bot_symbols_none():
    service = SchedulerService()
    service._scheduler = MagicMock()
    service._scheduler.running = True
    service._scheduler.get_job.return_value = None # Not running
    service._scheduler.get_jobs.return_value = []
    
    service._ws_client = MagicMock()
    
    service.start_bot("bot_1", symbols=None)
    
    service._ws_client.add_subscription.assert_called_once_with("BTCUSDT", "trade")

@pytest.mark.asyncio
@patch("crypto_mas.services.scheduler_service.SessionLocal")
@patch("crypto_mas.services.scheduler_service.TradingCycleService")
@patch("crypto_mas.services.scheduler_service.get_market_data_provider")
async def test_run_cycle_task_success(mock_get_provider, mock_tcs, mock_session_local):
    service = SchedulerService()
    
    mock_tcs_instance = MagicMock()
    mock_tcs_instance.run_cycle = AsyncMock()
    mock_tcs.return_value = mock_tcs_instance
    
    await service._run_cycle_task(symbols=["BTCUSDT"], mode="swing", exchange_str="BINANCE")
    
    mock_get_provider.assert_called_once()
    mock_session_local.return_value.close.assert_called_once()
    mock_tcs_instance.run_cycle.assert_called_once()

@pytest.mark.asyncio
@patch("crypto_mas.services.scheduler_service.SessionLocal")
@patch("crypto_mas.services.scheduler_service.get_market_data_provider")
async def test_run_cycle_task_failure(mock_get_provider, mock_session_local):
    service = SchedulerService()
    
    mock_get_provider.side_effect = Exception("Provider error")
    
    await service._run_cycle_task(symbols=["BTCUSDT"], mode="swing", exchange_str="BINANCE")
    
    mock_get_provider.assert_called_once()
    mock_session_local.return_value.close.assert_called_once()
