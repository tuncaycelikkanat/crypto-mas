"""
tests/unit/test_whipsaw_cooldown_and_liquidity.py — Dedicated unit tests for
Regime-Adaptive Whipsaw Cooldown and Liquidity / Extreme Spread protection.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from crypto_mas.infrastructure.db.base import Base
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.services.backtesting.memory_cache import InMemoryPositionRepository
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_position_repository_whipsaw_cooldown(db_session: Session):
    repo = PositionRepository(db_session)
    now = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)

    # 1. Create two open positions and close both with STOP_LOSS within 2 hours
    pos1 = repo.create_open_position(
        account_name="test",
        exchange="BINANCE",
        symbol="BTCUSDT",
        quantity=Decimal("1"),
        entry_price=Decimal("50000"),
        notional_value=Decimal("50000"),
        opened_at=now - timedelta(hours=3),
    )
    repo.close_position(pos1, Decimal("49000"), now - timedelta(hours=2), "STOP_LOSS")

    pos2 = repo.create_open_position(
        account_name="test",
        exchange="BINANCE",
        symbol="BTCUSDT",
        quantity=Decimal("1"),
        entry_price=Decimal("49000"),
        notional_value=Decimal("49000"),
        opened_at=now - timedelta(hours=1, minutes=30),
    )
    repo.close_position(pos2, Decimal("48000"), now - timedelta(hours=1), "STOP_LOSS")

    # Check whipsaw cooldown with min_stop_count=2 and 48 hours (2880 mins)
    symbols = repo.get_whipsaw_cooldown_symbols(
        account_name="test",
        exchange="BINANCE",
        time_now=now,
        min_stop_count=2,
        cooldown_minutes=2880,
    )
    assert "BTCUSDT" in symbols

    # If we require min_stop_count=3, it should not be in cooldown yet
    symbols_3 = repo.get_whipsaw_cooldown_symbols(
        account_name="test",
        exchange="BINANCE",
        time_now=now,
        min_stop_count=3,
        cooldown_minutes=2880,
    )
    assert "BTCUSDT" not in symbols_3


def test_memory_cache_whipsaw_cooldown():
    cache = InMemoryPositionRepository()
    now = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    
    # Create mock position object
    class MockPos:
        symbol = "ETHUSDT"
        side = "LONG"
        entry_price = Decimal("3000")
        quantity = Decimal("1")
    
    pos1 = MockPos()
    cache._open["ETHUSDT"] = pos1
    cache.close_position(pos1, Decimal("2900"), now - timedelta(hours=2), "STOP_LOSS")
    
    pos2 = MockPos()
    cache._open["ETHUSDT"] = pos2
    cache.close_position(pos2, Decimal("2850"), now - timedelta(hours=1), "STOP_LOSS")
    
    symbols = cache.get_whipsaw_cooldown_symbols(
        account_name="test",
        exchange="BINANCE",
        time_now=now,
        min_stop_count=2,
        cooldown_minutes=2880,
    )
    assert "ETHUSDT" in symbols


def test_thin_liquidity_and_excessive_spread():
    # Normal snapshot (liquid, small spread)
    normal_snap = FeatureSnapshot(
        id=1,
        exchange="BINANCE",
        symbol="SOLUSDT",
        timeframe="1h",
        timestamp=datetime.now(UTC),
        features_json={
            "close": 150.0,
            "high": 152.0,
            "low": 149.0,
            "volume": 100000.0,  # 15M USDT volume
        },
        created_at=datetime.now(UTC),
    )
    is_risky, reason = PaperBrokerService._is_thin_liquidity_or_excessive_spread(normal_snap)
    assert not is_risky
    assert reason == ""
    
    # Excessive spread snapshot (>8% range)
    wick_snap = FeatureSnapshot(
        id=2,
        exchange="BINANCE",
        symbol="MEMEUSDT",
        timeframe="1h",
        timestamp=datetime.now(UTC),
        features_json={
            "close": 1.0,
            "high": 1.15,
            "low": 0.95,
            "volume": 50000.0,
        },
        created_at=datetime.now(UTC),
    )
    is_risky, reason = PaperBrokerService._is_thin_liquidity_or_excessive_spread(wick_snap)
    assert is_risky
    assert "Excessive bar spread/range" in reason
    
    # Thin liquidity snapshot (<$1,000 USDT volume)
    illiquid_snap = FeatureSnapshot(
        id=3,
        exchange="BINANCE",
        symbol="LOWUSDT",
        timeframe="1h",
        timestamp=datetime.now(UTC),
        features_json={
            "close": 2.0,
            "high": 2.02,
            "low": 1.99,
            "volume": 200.0,  # $400 USDT volume
        },
        created_at=datetime.now(UTC),
    )
    is_risky, reason = PaperBrokerService._is_thin_liquidity_or_excessive_spread(illiquid_snap)
    assert is_risky
    assert "Thin liquidity bar volume" in reason
