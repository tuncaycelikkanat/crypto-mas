"""Unit tests for WebSocket & REST Real-Time Risk Dashboard (/api/v1/ws/risk-regime)."""
import pytest
from fastapi.testclient import TestClient

from crypto_mas.apps.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_get_risk_regime_snapshot(client: TestClient):
    res = client.get("/api/v1/ws/risk-regime/snapshot")
    assert res.status_code == 200
    data = res.json()
    assert data["system_status"] == "ACTIVE"
    assert "regime_snapshot" in data
    assert "btc_regime" in data["regime_snapshot"]
    assert "risk_snapshot" in data
    assert data["risk_snapshot"]["max_drawdown_limit_pct"] == 15.0


def test_websocket_risk_regime(client: TestClient):
    with client.websocket_connect("/api/v1/ws/risk-regime") as websocket:
        data = websocket.receive_json()
        assert data["system_status"] == "ACTIVE"
        assert "regime_snapshot" in data
        assert "risk_snapshot" in data
