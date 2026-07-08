from datetime import datetime, UTC
from decimal import Decimal

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime.regime import MarketRegime, RegimeSnapshot, RegimeEngine
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

def test_compute_regime_insufficient_snapshots():
    snapshots = []
    result = RegimeEngine().detect(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert result is None

def test_compute_regime_bull_trend():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9800.0, "ema_50": 9500.0, "roc_14": 5.0, "atr_14": 100.0, "bb_upper": 10500.0, "bb_middle": 10000.0, "bb_lower": 9500.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 15, tzinfo=UTC),
            features_json={"close": 10200.0, "ema_20": 9900.0, "ema_50": 9600.0, "roc_14": 6.0, "atr_14": 120.0, "bb_upper": 10500.0, "bb_middle": 10000.0, "bb_lower": 9500.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 30, tzinfo=UTC),
            features_json={"close": 10500.0, "ema_20": 10000.0, "ema_50": 9700.0, "roc_14": 7.0, "atr_14": 150.0, "bb_upper": 10500.0, "bb_middle": 10000.0, "bb_lower": 9500.0}
        )
    ]
    
    result = RegimeEngine().detect(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert result is not None
    assert result.regime == MarketRegime.BULL_TREND
    assert result.risk_multiplier == 1.0

def test_compute_regime_bear_trend():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 10200.0, "ema_50": 10500.0, "roc_14": -5.0, "atr_14": 100.0, "bb_upper": 10500.0, "bb_middle": 10000.0, "bb_lower": 9500.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 15, tzinfo=UTC),
            features_json={"close": 9800.0, "ema_20": 10100.0, "ema_50": 10400.0, "roc_14": -6.0, "atr_14": 120.0, "bb_upper": 10500.0, "bb_middle": 10000.0, "bb_lower": 9500.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 30, tzinfo=UTC),
            features_json={"close": 9500.0, "ema_20": 10000.0, "ema_50": 10300.0, "roc_14": -7.0, "atr_14": 150.0, "bb_upper": 10500.0, "bb_middle": 10000.0, "bb_lower": 9500.0}
        )
    ]
    
    result = RegimeEngine().detect(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert result is not None
    assert result.regime == MarketRegime.BEAR_TREND

def test_compute_regime_high_volatility():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 10000.0, "ema_50": 10000.0, "roc_14": 0.0, "atr_14": 1000.0, "bb_upper": 11000.0, "bb_middle": 10000.0, "bb_lower": 9000.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 15, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 10000.0, "ema_50": 10000.0, "roc_14": 0.0, "atr_14": 1000.0, "bb_upper": 11000.0, "bb_middle": 10000.0, "bb_lower": 9000.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 30, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 10000.0, "ema_50": 10000.0, "roc_14": 0.0, "atr_14": 1000.0, "bb_upper": 11000.0, "bb_middle": 10000.0, "bb_lower": 9000.0}
        )
    ]
    
    result = RegimeEngine().detect(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert result is not None
    assert result.regime == MarketRegime.HIGH_VOLATILITY

def test_compute_regime_sideways():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9990.0, "ema_50": 10010.0, "roc_14": 0.1, "atr_14": 50.0, "bb_upper": 10100.0, "bb_middle": 10000.0, "bb_lower": 9900.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 15, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9990.0, "ema_50": 10010.0, "roc_14": 0.1, "atr_14": 50.0, "bb_upper": 10100.0, "bb_middle": 10000.0, "bb_lower": 9900.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 30, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9990.0, "ema_50": 10010.0, "roc_14": 0.1, "atr_14": 50.0, "bb_upper": 10100.0, "bb_middle": 10000.0, "bb_lower": 9900.0}
        )
    ]
    
    result = RegimeEngine().detect(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert result is not None
    assert result.regime == MarketRegime.SIDEWAYS

def test_compute_regime_missing_features():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": None}
        )
    ] * 3
    
    result = RegimeEngine().detect(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    assert result.regime == MarketRegime.UNKNOWN
