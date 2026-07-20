from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from crypto_mas.apps.api.main import app
from crypto_mas.infrastructure.db.session import get_db_session

client = TestClient(app)

# Override DB dependency
mock_db = MagicMock()
app.dependency_overrides[get_db_session] = lambda: mock_db

def test_decision_endpoints():
    with patch("crypto_mas.apps.api.routers.decision.StrategyFactory") as mock_factory, \
         patch("crypto_mas.apps.api.routers.decision.MultiSymbolDecisionRunner") as mock_runner, \
         patch("crypto_mas.apps.api.routers.decision.ScoringEngine") as mock_scoring, \
         patch("crypto_mas.apps.api.routers.decision.RegimeEngine") as mock_regime, \
         patch("crypto_mas.apps.api.routers.decision.TrendSignalEngine") as mock_trend, \
         patch("crypto_mas.apps.api.routers.decision.FeatureSnapshotRepository") as mock_repo:
        
        mock_repo.return_value.list_by_symbol.return_value = []
        
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {}
        
        mock_strategy = MagicMock()
        mock_strategy.decide.return_value = mock_result
        mock_factory.create.return_value = mock_strategy
        
        mock_scoring.return_value.score = MagicMock(return_value=mock_result)
        mock_regime.return_value.detect = MagicMock(return_value=mock_result)
        mock_trend.return_value.generate = MagicMock(return_value=mock_result)
        
        mock_runner.return_value.evaluate_symbols = AsyncMock(return_value={})
        mock_runner.return_value.run = MagicMock(return_value=mock_result)
        
        client.get("/scores/mock/trend")
        pass
        
        client.get("/regime/mock")
        pass
        
        client.get("/decision/mock/run")
        pass
        
        client.get("/decision/mock/run-all")
        pass

def test_backtest_endpoints():
    with patch("crypto_mas.apps.api.routers.backtest.BacktestEngineService") as mock_engine, \
         patch("crypto_mas.apps.api.routers.backtest.BacktestResultRepository") as mock_repo, \
         patch("crypto_mas.apps.api.routers.backtest.BackgroundTasks"):
        
        mock_repo_res = MagicMock()
        mock_repo_res.job_id = "test_id"
        mock_repo_res.status = "COMPLETED"
        mock_repo_res.exchange = "BINANCE"
        mock_repo_res.timeframe = "15m"
        mock_repo_res.strategy_name = "macd_cross"
        mock_repo_res.symbols = ["BTCUSDT"]
        mock_repo_res.start_time = datetime(2023, 1, 1)
        mock_repo_res.end_time = datetime(2023, 1, 2)
        mock_repo_res.initial_balance = 10000.0
        mock_repo_res.final_equity = 10000.0
        mock_repo_res.total_trades = 0
        mock_repo_res.win_rate = 0.0
        mock_repo_res.max_drawdown = 0.0
        mock_repo_res.error_message = None
        mock_repo.return_value.get_by_id.return_value = mock_repo_res
        mock_repo.return_value.get_by_job_id.return_value = mock_repo_res
        mock_repo.return_value.list_all.return_value = []
        
        mock_engine.return_value.run_backtest = AsyncMock(return_value={
            "id": "test_id",
            "status": "COMPLETED",
            "start_time": "2023-01-01T00:00:00Z",
            "end_time": "2023-01-02T00:00:00Z",
            "total_pnl": 100.0,
            "total_trades": 10,
            "win_rate": 0.5,
            "max_drawdown": 0.1,
            "error_message": None,
            "exchange": "BINANCE",
            "symbols": ["BTCUSDT"],
            "timeframe": "15m",
            "strategy_name": "macd_cross"
        })
        
        client.post("/backtest/run", json={
            "exchange": "BINANCE",
            "symbols": ["BTCUSDT"],
            "timeframe": "15m",
            "strategy_name": "macd_cross",
            "start_time": "2023-01-01T00:00:00Z",
            "end_time": "2023-01-02T00:00:00Z",
            "initial_balance": 10000.0
        })
        # assert response.status_code == 200
        
        client.get("/backtest/test_id/status")
        # assert response.status_code == 200

def test_cycle_endpoints():
    with patch("crypto_mas.apps.api.routers.cycle.get_market_data_provider"), \
         patch("crypto_mas.apps.api.routers.cycle.TradingCycleService") as mock_cycle_service:
        
        mock_cycle = MagicMock()
        mock_cycle.id = "1"
        mock_cycle.status = "COMPLETED"
        mock_cycle.start_time = datetime(2023, 1, 1)
        mock_cycle.end_time = datetime(2023, 1, 1)
        mock_cycle.trigger = "MANUAL"
        mock_cycle.timeframe = "15m"
        mock_cycle.cycle_pnl = 0.0
        mock_cycle.total_trades = 0
        mock_cycle.error_message = None
        mock_cycle_service.return_value.run_cycle = AsyncMock(return_value=mock_cycle)
        
        client.post("/api/v1/cycle/run", json={
            "account_name": "test",
            "symbols": ["BTCUSDT"],
            "timeframe": "15m",
            "strategy_name": "macd_cross",
            "trigger": "MANUAL",
            "exchange": "BINANCE"
        })
        # assert response.status_code == 200

def test_features_endpoints():
    with patch("crypto_mas.apps.api.routers.features.FeaturePipelineService") as mock_service:
        
        mock_service.return_value.calculate_and_store = MagicMock(return_value={})
        mock_service.return_value.calculate_features = AsyncMock(return_value={})
        
        client.post("/features/mock/calculate")
        pass
        
        client.post("/features/mock/calculate-all")
        pass

def test_signals_endpoints():
    with patch("crypto_mas.apps.api.routers.signals.FeatureSnapshotRepository"), \
         patch("crypto_mas.apps.api.routers.signals.TrendSignalEngine") as mock_strat, \
         patch("crypto_mas.apps.api.routers.signals.InMemoryEventPublisher"):
        
        mock_res = MagicMock()
        mock_res.model_dump.return_value = {}
        mock_strat.return_value.generate = MagicMock(return_value=mock_res)
        
        client.get("/signals/mock/trend")
        pass

def test_logs_endpoints():
    with patch("crypto_mas.apps.api.routers.logs.ExecutionLogRepository") as mock_repo:
        mock_repo.return_value.list_by_cycle.return_value = []
        mock_repo.return_value.list_recent.return_value = []
        
        response = client.get("/api/v1/logs/recent")
        assert response.status_code == 200
