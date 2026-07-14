import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from crypto_mas.apps.api.main import app
from crypto_mas.infrastructure.db.session import get_db_session
from crypto_mas.domain.models import *  # noqa
from crypto_mas.infrastructure.db.base import Base

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

def test_build_mock_target_portfolio():
    response = client.get("/portfolio/mock/target")
    assert response.status_code == 200
    data = response.json()
    assert "target_positions" in data
    assert "exchange" in data
    assert data["exchange"] == "MOCK"
