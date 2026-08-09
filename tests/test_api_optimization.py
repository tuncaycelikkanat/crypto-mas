import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crypto_mas.apps.api.main import app
from crypto_mas.domain.models.optimization_history import OptimizationHistory
from crypto_mas.infrastructure.db.session import get_db_session

client = TestClient(app)



def test_get_optimization_history_empty(db_session: Session):
    app.dependency_overrides[get_db_session] = lambda: db_session
    response = client.get("/api/v1/optimization/history")
    assert response.status_code == 200
    assert response.json() == []

def test_get_optimization_history_with_data(db_session: Session):
    record = OptimizationHistory(
        status="COMPLETED",
        triggered_by="MANUAL",
        strategy_name="regime_adaptive",
        symbols_json=["BTCUSDT", "ETHUSDT"],
        lookback_months=3,
        best_params_json={"tp_mult": 2.0, "sl_mult": 1.0},
        completed_at=datetime.now(timezone.utc)
    )
    db_session.add(record)
    db_session.commit()

    app.dependency_overrides[get_db_session] = lambda: db_session
    response = client.get("/api/v1/optimization/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "COMPLETED"
    assert data[0]["triggered_by"] == "MANUAL"
    assert data[0]["strategy_name"] == "regime_adaptive"
    assert data[0]["lookback_months"] == 3
    assert data[0]["best_params_json"]["tp_mult"] == 2.0

def test_force_optimization_endpoint(db_session: Session):
    app.dependency_overrides[get_db_session] = lambda: db_session
    # This should return a 200 and a queued message
    # And background task should be added, but TestClient doesn't actually run BackgroundTasks immediately unless configured to wait.
    response = client.post("/api/v1/optimization/force")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Optimization job queued" in data["message"]
