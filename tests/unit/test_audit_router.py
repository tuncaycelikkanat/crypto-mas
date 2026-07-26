"""Unit tests for FastAPI audit_router (/api/v1/audit)."""
import pytest
from fastapi.testclient import TestClient

from crypto_mas.apps.api.main import app
from crypto_mas.services.audit_service.decision_audit_service import DecisionAuditService


@pytest.fixture
def client(tmp_path):
    DecisionAuditService.reset_instance()
    log_file = tmp_path / "test_api_audit.jsonl"
    DecisionAuditService.get_instance(log_file_path=log_file)
    with TestClient(app) as test_client:
        yield test_client
    DecisionAuditService.reset_instance()


def test_audit_endpoints(client: TestClient):
    # Log a new audit record via POST
    payload = {
        "symbol": "ETHUSDT",
        "decision": "LONG",
        "audit_trail": {"scoring": {"score": 75}},
        "exchange": "MOCK",
        "timeframe": "4h",
        "notes": "Test POST log",
    }
    post_res = client.post("/api/v1/audit/log", json=payload)
    assert post_res.status_code == 201
    data = post_res.json()
    assert data["symbol"] == "ETHUSDT"
    assert data["decision"] == "LONG"

    # Get latest
    get_latest_res = client.get("/api/v1/audit/latest?limit=10")
    assert get_latest_res.status_code == 200
    latest = get_latest_res.json()
    assert len(latest) >= 1
    assert latest[0]["symbol"] == "ETHUSDT"

    # Get by symbol
    get_sym_res = client.get("/api/v1/audit/symbol/ETHUSDT")
    assert get_sym_res.status_code == 200
    sym_records = get_sym_res.json()
    assert len(sym_records) >= 1
    assert all(r["symbol"] == "ETHUSDT" for r in sym_records)

    # Get stats
    stats_res = client.get("/api/v1/audit/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_records_in_buffer"] >= 1
    assert "LONG" in stats["decision_counts"]
