import pytest
from unittest.mock import patch, MagicMock
from crypto_mas.services.auto_optimizer_service import AutoOptimizerService
from crypto_mas.services.market_data_service.schemas import Timeframe
from crypto_mas.domain.models.optimization_history import OptimizationHistory
from sqlalchemy.orm import Session


@pytest.fixture
def mock_optuna_study():
    mock_study = MagicMock()
    mock_study.best_params = {
        "tp_mult": 2.0,
        "sl_mult": 1.0,
        "breakdown_tp_mult": 1.5,
        "breakdown_sl_mult": 0.9,
        "max_dist_ema": 0.03
    }
    return mock_study

@patch('crypto_mas.services.auto_optimizer_service.optuna.create_study')
@patch('crypto_mas.services.auto_optimizer_service.AutoOptimizerService._run_async')
def test_run_optimization_job_success(mock_run_async, mock_create_study, mock_optuna_study, db_session: Session):
    mock_create_study.return_value = mock_optuna_study
    # Mock the internal asyncio runners so it doesn't actually try to fetch or backtest
    mock_run_async.return_value = {"composite_score": 100.0}
    
    service = AutoOptimizerService(db_session)
    best_params = service.run_optimization_job(
        symbols=["BTCUSDT"],
        timeframe=Timeframe.ONE_HOUR,
        strategy_name="test_strat",
        lookback_months=1,
        n_trials=1,
        triggered_by="TEST"
    )
    
    # Assert return value
    assert best_params["tp_mult"] == 2.0
    
    # Check DB
    history = db_session.query(OptimizationHistory).first()
    assert history is not None
    assert history.status == "COMPLETED"
    assert history.triggered_by == "TEST"
    assert history.strategy_name == "test_strat"
    assert history.best_params_json["tp_mult"] == 2.0
    assert history.error_message is None

@patch('crypto_mas.services.auto_optimizer_service.optuna.create_study')
@patch('crypto_mas.services.auto_optimizer_service.AutoOptimizerService._run_async')
def test_run_optimization_job_failure(mock_run_async, mock_create_study, db_session: Session):
    # Simulate optuna failing
    mock_create_study.side_effect = Exception("Optuna crashed!")
    mock_run_async.return_value = None
    
    service = AutoOptimizerService(db_session)
    
    with pytest.raises(Exception, match="Optuna crashed!"):
        service.run_optimization_job(
            symbols=["BTCUSDT"],
            timeframe=Timeframe.ONE_HOUR,
            strategy_name="test_strat",
            lookback_months=1,
            n_trials=1,
            triggered_by="TEST_ERR"
        )
        
    # Check DB
    history = db_session.query(OptimizationHistory).first()
    assert history is not None
    assert history.status == "FAILED"
    assert history.triggered_by == "TEST_ERR"
    assert "Optuna crashed!" in history.error_message
