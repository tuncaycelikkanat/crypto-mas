from datetime import UTC, datetime

import pytest

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime.htf_manager import HTFRegimeManager


@pytest.fixture
def manager():
    return HTFRegimeManager()

def create_htf_snapshot(close: float, ema20: float, ema50: float, roc: float) -> FeatureSnapshot:
    return FeatureSnapshot(
        exchange="BINANCE", symbol="BTCUSDT", timeframe="4h",
        timestamp=datetime.now(UTC),
        features_json={"close": close, "ema_20": ema20, "ema_50": ema50, "roc_14": roc}
    )

def test_htf_bear_trend_rejects_longs(manager):
    # Bear trend: Close < EMA20 < EMA50 and ROC < 0
    snapshot = create_htf_snapshot(close=9000, ema20=9500, ema50=10000, roc=-2.5)
    snapshots = [snapshot, snapshot]
    
    assert manager.is_long_allowed(snapshots) is False
    assert manager.is_short_allowed(snapshots) is True

def test_htf_bull_trend_rejects_shorts(manager):
    # Bull trend: Close > EMA20 > EMA50 and ROC > 0
    snapshot = create_htf_snapshot(close=11000, ema20=10500, ema50=10000, roc=2.5)
    snapshots = [snapshot, snapshot]
    
    assert manager.is_long_allowed(snapshots) is True
    assert manager.is_short_allowed(snapshots) is False

def test_htf_sideways_allows_both(manager):
    # Mixed signals
    snapshot = create_htf_snapshot(close=10200, ema20=10500, ema50=10000, roc=0.5)
    snapshots = [snapshot, snapshot]
    
    assert manager.is_long_allowed(snapshots) is True
    assert manager.is_short_allowed(snapshots) is True

def test_htf_missing_data_allows_both(manager):
    snapshot = FeatureSnapshot(
        exchange="BINANCE", symbol="BTCUSDT", timeframe="4h",
        timestamp=datetime.now(UTC),
        features_json={"close": 10000} # missing emas
    )
    snapshots = [snapshot, snapshot]
    assert manager.is_long_allowed(snapshots) is True
    assert manager.is_short_allowed(snapshots) is True
