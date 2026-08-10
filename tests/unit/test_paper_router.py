from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from crypto_mas.apps.api.main import app
from crypto_mas.domain.models import *  # noqa
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.infrastructure.db.session import get_db_session

import pytest

@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db_session] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_initialize_mock_paper_account(client):
    response = client.post("/api/v1/paper/mock/account/init")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "default-paper"
    assert data["exchange"] == "MOCK"
    assert data["base_currency"] == "USDT"
    assert "initial_balance" in data

def test_get_mock_paper_account(client):
    client.post("/api/v1/paper/mock/account/init")
    
    response = client.get("/api/v1/paper/mock/account")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "main"
