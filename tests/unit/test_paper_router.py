from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from crypto_mas.apps.api.main import app
from crypto_mas.domain.models import *  # noqa
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

app.dependency_overrides[get_db_session] = override_get_db_session

client = TestClient(app)

def test_initialize_mock_paper_account():
    response = client.post("/api/v1/paper/mock/account/init")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "default-paper"
    assert data["exchange"] == "MOCK"
    assert data["base_currency"] == "USDT"
    assert "initial_balance" in data

def test_get_mock_paper_account():
    client.post("/api/v1/paper/mock/account/init")
    
    response = client.get("/api/v1/paper/mock/account")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "default-paper"
    assert "open_positions" in data
