from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert "env" in data
    assert "mode" in data


def test_version_endpoint() -> None:
    response = client.get("/version")

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "crypto-mas"
    assert data["version"] == "0.1.0"


def test_config_endpoint_does_not_expose_secrets() -> None:
    response = client.get("/config")

    assert response.status_code == 200

    data = response.json()

    assert "app_env" in data
    assert "trading_mode" in data
    assert "log_level" in data

    assert "database_url" not in data
    assert "redis_url" not in data
    assert "binance_api_secret" not in data
