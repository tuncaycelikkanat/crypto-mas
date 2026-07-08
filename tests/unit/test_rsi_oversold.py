from decimal import Decimal
from datetime import datetime, UTC
import pytest
from crypto_mas.engine.strategy.rsi_oversold import RSIOversoldStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

@pytest.fixture
def rsi_strategy():
    return RSIOversoldStrategy()

def create_snapshots(rsi_prev: float, rsi_curr: float, close: float, bb_lower: float) -> list[FeatureSnapshot]:
    s1 = FeatureSnapshot(
        exchange="BINANCE", symbol="BTCUSDT", timeframe="15m",
        timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
        features_json={"rsi_14": 50.0, "close": close}
    )
    s2 = FeatureSnapshot(
        exchange="BINANCE", symbol="BTCUSDT", timeframe="15m",
        timestamp=datetime(2023, 1, 1, 0, 15, tzinfo=UTC),
        features_json={"rsi_14": rsi_prev, "close": close}
    )
    s3 = FeatureSnapshot(
        exchange="BINANCE", symbol="BTCUSDT", timeframe="15m",
        timestamp=datetime(2023, 1, 1, 0, 30, tzinfo=UTC),
        features_json={"rsi_14": rsi_curr, "close": close, "bb_lower": bb_lower}
    )
    return [s1, s2, s3]

def test_rsi_oversold_buy_signal(rsi_strategy):
    # RSI drops to 25, which is < 30. Prev was 24, so it's recovering (+0.2).
    # Close is 9900, bb_lower is 9950. Close < bb_lower, so bonus (+0.15).
    snapshots = create_snapshots(rsi_prev=24.0, rsi_curr=25.0, close=9900, bb_lower=9950)
    decision = rsi_strategy.decide(Exchange("BINANCE"), "BTCUSDT", Timeframe("15m"), snapshots)
    
    assert decision is not None
    assert decision.action == DecisionAction.CONSIDER_LONG
    assert decision.confidence > 0.5
    assert "recovering" in decision.reason

def test_rsi_oversold_no_signal_above_threshold(rsi_strategy):
    snapshots = create_snapshots(rsi_prev=36.0, rsi_curr=35.0, close=10000, bb_lower=9000)
    decision = rsi_strategy.decide(Exchange("BINANCE"), "BTCUSDT", Timeframe("15m"), snapshots)
    assert decision.action == DecisionAction.HOLD

def test_rsi_oversold_missing_features(rsi_strategy):
    s = FeatureSnapshot(
        exchange="BINANCE", symbol="BTCUSDT", timeframe="15m",
        timestamp=datetime.now(UTC),
        features_json={}
    )
    decision = rsi_strategy.decide(Exchange("BINANCE"), "BTCUSDT", Timeframe("15m"), [s, s, s])
    assert decision is None

def test_rsi_oversold_exact_boundary(rsi_strategy):
    snapshots = create_snapshots(rsi_prev=31.0, rsi_curr=30.0, close=10000, bb_lower=9000)
    decision = rsi_strategy.decide(Exchange("BINANCE"), "BTCUSDT", Timeframe("15m"), snapshots)
    # The code uses `rsi < self.OVERSOLD_THRESHOLD`, so exactly 30.0 should be HOLD
    assert decision.action == DecisionAction.HOLD
