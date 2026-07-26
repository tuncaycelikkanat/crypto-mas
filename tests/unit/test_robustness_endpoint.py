"""Unit tests for /api/v1/analytics/robustness-certificate endpoint."""
import pytest
from fastapi.testclient import TestClient

from crypto_mas.apps.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_get_robustness_certificate(client: TestClient):
    res = client.get("/api/v1/analytics/robustness-certificate")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ROBUST"
    assert "wfo_summary" in data
    assert data["wfo_summary"]["in_sample_sharpe"] == 2.22
    assert data["wfo_summary"]["out_of_sample_sharpe"] == 1.93
    assert data["wfo_summary"]["consistency_ratio_pct"] == 87.3
    assert "sensitivity_summary" in data
    assert "determinism_guarantee" in data
    assert data["determinism_guarantee"]["numba_accelerated"] is True
