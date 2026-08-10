import pytest
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from crypto_mas.infrastructure.db.base import Base
import crypto_mas.domain.models  # noqa: F401
from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue


from crypto_mas.infrastructure.config.settings import get_settings

@pytest.fixture(autouse=True)
def reset_executor_queue_singleton():
    """
    Ensures the OrderExecutorQueue singleton is clean for each test.
    This prevents cross-test contamination where a closed DB session is kept in the broker factory,
    and prevents asyncio Queue from being bound to the wrong event loop.
    """
    OrderExecutorQueue._instance = None
    get_settings.cache_clear()
    
    yield
    
    OrderExecutorQueue._instance = None
    get_settings.cache_clear()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Provide a clean in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
