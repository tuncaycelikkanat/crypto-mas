import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from crypto_mas.apps.api.main import app
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.infrastructure.db.session import get_db_session

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_auth_dependencies():
    app.dependency_overrides[get_db_session] = override_get_db_session
    yield
    app.dependency_overrides.clear()

client = TestClient(app)


from unittest.mock import patch
from crypto_mas.infrastructure.config.settings import Settings

def test_api_auth_bypass_when_key_not_configured():
    with patch("crypto_mas.apps.api.security.get_settings") as mock_get_settings:
        mock_get_settings.return_value = Settings(api_security_key="", app_env="development")
        response = client.post("/api/v1/paper/mock/account/init")
        assert response.status_code == 200


def test_api_auth_enforces_key_when_configured():
    with patch("crypto_mas.apps.api.security.get_settings") as mock_get_settings:
        mock_get_settings.return_value = Settings(api_security_key="super-secret-test-key", app_env="production")

        # Missing header -> 401
        response_missing = client.post("/api/v1/paper/mock/account/init")
        assert response_missing.status_code == 401
        assert "Invalid or missing API Key" in response_missing.text

        # Incorrect header -> 401
        response_wrong = client.post(
            "/api/v1/paper/mock/account/init",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response_wrong.status_code == 401

        # Correct header -> 200
        response_correct = client.post(
            "/api/v1/paper/mock/account/init",
            headers={"X-API-Key": "super-secret-test-key"},
        )
        assert response_correct.status_code == 200
