from datetime import datetime, UTC
from decimal import Decimal

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.strategy.ema_golden_cross import EMAGoldenCrossStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

def test_ema_golden_cross_buy_signal():
    strategy = EMAGoldenCrossStrategy()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1d",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9000.0, "ema_50": 9500.0, "rsi_14": 60.0} # 50 < 200
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1d",
            timestamp=datetime(2023, 1, 2, 0, 0, tzinfo=UTC),
            features_json={"close": 10200.0, "ema_20": 9600.0, "ema_50": 9550.0, "rsi_14": 60.0} # 50 > 200
        )
    ] * 5
    
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_DAY, snapshots)
    assert decision is not None
    assert decision.action == DecisionAction.CONSIDER_LONG
    assert decision.confidence > 0.5

def test_ema_death_cross_sell_signal():
    strategy = EMAGoldenCrossStrategy()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1d",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9500.0, "ema_50": 9000.0, "rsi_14": 40.0} # 50 > 200
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1d",
            timestamp=datetime(2023, 1, 2, 0, 0, tzinfo=UTC),
            features_json={"close": 8000.0, "ema_20": 8900.0, "ema_50": 9050.0, "rsi_14": 40.0} # 50 < 200
        )
    ] * 5
    
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_DAY, snapshots)
    assert decision is not None
    assert decision.action == DecisionAction.HOLD

def test_ema_golden_cross_no_signal():
    strategy = EMAGoldenCrossStrategy()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1d",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9000.0, "ema_50": 9500.0, "rsi_14": 50.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1d",
            timestamp=datetime(2023, 1, 2, 0, 0, tzinfo=UTC),
            features_json={"close": 9800.0, "ema_20": 9100.0, "ema_50": 9400.0, "rsi_14": 50.0} # still below
        )
    ] * 5
    
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_DAY, snapshots)
    assert decision is not None
    assert decision.action == DecisionAction.HOLD

def test_ema_golden_cross_missing_features():
    strategy = EMAGoldenCrossStrategy()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1d",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_50": 9000.0} # missing ema_200
        )
    ] * 5
    
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_DAY, snapshots)
    assert decision is None
