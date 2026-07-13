from unittest.mock import MagicMock

from crypto_mas.domain.models.backtest_result import BacktestResult
from crypto_mas.domain.repositories.backtest_result_repository import BacktestResultRepository


def test_add_backtest_result():
    session_mock = MagicMock()
    repo = BacktestResultRepository(session_mock)
    
    result = BacktestResult(job_id="test_job")
    returned = repo.add(result)
    
    session_mock.add.assert_called_once_with(result)
    session_mock.flush.assert_called_once()
    assert returned == result

def test_get_by_job_id():
    session_mock = MagicMock()
    repo = BacktestResultRepository(session_mock)
    
    result_mock = MagicMock()
    session_mock.scalars.return_value.first.return_value = result_mock
    
    returned = repo.get_by_job_id("test_job")
    
    session_mock.scalars.assert_called_once()
    assert returned == result_mock

def test_update_status():
    session_mock = MagicMock()
    repo = BacktestResultRepository(session_mock)
    
    repo.update_status("test_job", "COMPLETED")
    
    session_mock.execute.assert_called_once()
    session_mock.flush.assert_called_once()

def test_list_all():
    session_mock = MagicMock()
    repo = BacktestResultRepository(session_mock)
    
    results_mock = [MagicMock(), MagicMock()]
    session_mock.scalars.return_value.all.return_value = results_mock
    
    returned = repo.list_all(limit=10)
    
    session_mock.scalars.assert_called_once()
    assert returned == results_mock
