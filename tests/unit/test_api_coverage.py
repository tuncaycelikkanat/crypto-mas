from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from crypto_mas.apps.api.main import app
from crypto_mas.infrastructure.db.session import get_db_session

client = TestClient(app)

# Override DB dependency
mock_db = MagicMock()
app.dependency_overrides[get_db_session] = lambda: mock_db

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    
    response = client.get("/api/v1/version")
    assert response.status_code == 200

@patch("crypto_mas.apps.api.routers.bot.SchedulerService")
def test_bot_endpoints(mock_scheduler):
    mock_instance = mock_scheduler.return_value
    mock_instance.get_status.return_value = {"bots": []}
    
    # Status
    response = client.get("/api/v1/bot/status")
    assert response.status_code == 200
    assert response.json() == {"bots": []}
    
    # Start
    mock_instance.start_bot.return_value = {"started": True}
    response = client.post("/api/v1/bot/start", json={
        "bot_id": "test_bot",
        "interval_seconds": 60,
        "symbols": ["BTCUSDT"],
        "mode": "swing",
        "exchange": "BINANCE"
    })
    assert response.status_code == 200
    
    # Stop
    mock_instance.stop_bot.return_value = {"stopped": True}
    response = client.post("/api/v1/bot/stop/test_bot")
    assert response.status_code == 200

@patch("crypto_mas.apps.api.routers.market.get_market_data_provider")
@patch("crypto_mas.apps.api.routers.market.SymbolRepository")
@patch("crypto_mas.apps.api.routers.market.HistoricalFetcherService")
@patch("crypto_mas.apps.api.routers.market.httpx.AsyncClient")
def test_market_endpoints(mock_client_class, mock_fetcher, mock_sym_repo, mock_provider):
    mock_instance = mock_provider.return_value
    mock_instance.fetch_symbols = AsyncMock(return_value=[])
    mock_instance.fetch_ohlcv = AsyncMock(return_value=[])
    
    mock_sym_repo.return_value.bulk_upsert.return_value = 0
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {}
    mock_fetcher.return_value.fetch_and_store_range = AsyncMock(return_value=mock_result)
    
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    mock_response = MagicMock()
    mock_response.json.return_value = {"serverTime": 1000}
    mock_client.get.return_value = mock_response
    
    response = client.get("/market/symbols/sample")
    assert response.status_code == 200
    
    response = client.get("/market/candles/sample")
    assert response.status_code == 200
    
    response = client.post("/market/symbols/mock/save")
    assert response.status_code == 200
    
    response = client.post("/market/candles/mock/save-all")
    assert response.status_code == 200
    
    response = client.get("/market/binance/time")
    assert response.status_code == 200
    
    response = client.get("/market/binance/symbols/sample")
    assert response.status_code == 200
    
    response = client.get("/market/binance/candles/sample")
    assert response.status_code == 200
    
    response = client.post("/market/binance/candles/save")
    assert response.status_code == 200

@patch("crypto_mas.apps.api.routers.paper.PaperBrokerService")
def test_paper_endpoints(mock_broker_service):
    mock_broker = mock_broker_service.return_value
    mock_broker.initialize_account.return_value = MagicMock(name="test_acc", initial_balance=1000)
    
    response = client.post("/api/v1/paper/mock/account/init")
    assert response.status_code == 200
    
    response = client.get("/api/v1/paper/mock/account")
    assert response.status_code == 200

def test_analytics_endpoints():
    with patch("crypto_mas.apps.api.routers.analytics.PaperAccountRepository") as mock_repo, \
         patch("crypto_mas.apps.api.routers.analytics.TradingCycleRepository") as mock_cycle_repo, \
         patch("crypto_mas.apps.api.routers.analytics.CandleRepository") as mock_candle_repo, \
         patch("crypto_mas.apps.api.routers.analytics.FeatureSnapshotRepository") as mock_feature_repo, \
         patch("crypto_mas.apps.api.routers.analytics.ExecutionLogRepository") as mock_log_repo:
        
        mock_repo.return_value.get_by_name.return_value = MagicMock(initial_balance=1000, equity=1000)
        
        response = client.get("/api/v1/analytics/summary")
        assert response.status_code == 200
        
        response = client.get("/api/v1/analytics/equity-curve")
        assert response.status_code == 200
        
        response = client.get("/api/v1/analytics/trade-history")
        assert response.status_code == 200
        
        response = client.get("/api/v1/analytics/coins")
        assert response.status_code == 200
        
        response = client.get("/api/v1/analytics/coin/BTCUSDT")
        assert response.status_code == 200
