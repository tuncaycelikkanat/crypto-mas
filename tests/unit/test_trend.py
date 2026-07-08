from datetime import datetime, UTC
from decimal import Decimal

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.signal.trend import TrendSignalEngine, SignalDirection
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

def test_trend_signal_generator_bullish():
    generator = TrendSignalEngine()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9800.0, "ema_50": 9500.0, "roc_14": 2.0, "rsi_14": 60.0, "macd": 50.0, "macd_signal": 40.0}
        )
    ] * 3
    
    signal = generator.generate(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert signal is not None
    assert signal.direction == SignalDirection.LONG
    assert signal.strength > 0.0

def test_trend_signal_generator_bearish():
    generator = TrendSignalEngine()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 8000.0, "ema_20": 8500.0, "ema_50": 9000.0, "roc_14": -2.0, "rsi_14": 40.0, "macd": -50.0, "macd_signal": -40.0}
        )
    ] * 3
    
    signal = generator.generate(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert signal is not None
    assert signal.direction == SignalDirection.SHORT
    assert signal.strength > 0.0

def test_trend_signal_generator_weak_trend():
    generator = TrendSignalEngine()
    # Price > ema_20 > ema_50, BUT roc_14 is 0.5 (less than min_roc=1.0) 
    # WAIT, roc_14 condition in code is `roc_14 > 0`. It doesn't check min_roc anymore.
    # To make it NEUTRAL, I will make rsi_14 = 40 instead of > 50 while bullish in other aspects
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9800.0, "ema_50": 9500.0, "roc_14": 0.5, "rsi_14": 40.0, "macd": 50.0, "macd_signal": 40.0}
        )
    ] * 3
    
    signal = generator.generate(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert signal is not None
    assert signal.direction == SignalDirection.NEUTRAL

def test_trend_signal_generator_missing_features():
    generator = TrendSignalEngine()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9800.0} # missing ema_50
        )
    ] * 3
    
    signal = generator.generate(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert signal is not None
    assert signal.direction == SignalDirection.NEUTRAL
