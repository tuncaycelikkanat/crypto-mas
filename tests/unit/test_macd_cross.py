from datetime import UTC, datetime

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.strategy.macd_cross import MACDStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def test_macd_cross_buy_signal():
    strategy = MACDStrategy()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1h",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "macd": -10.0, "macd_signal": -5.0, "macd_hist": -5.0} # macd < signal
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1h",
            timestamp=datetime(2023, 1, 1, 1, 0, tzinfo=UTC),
            features_json={"close": 10200.0, "macd": 5.0, "macd_signal": 0.0, "macd_hist": 5.0} # macd crosses above signal
        )
    ]
    
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_HOUR, snapshots)
    assert decision is not None
    assert decision.action == DecisionAction.CONSIDER_LONG
    assert decision.confidence > 0.5

def test_macd_cross_sell_signal():
    strategy = MACDStrategy()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1h",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "macd": 10.0, "macd_signal": 5.0, "macd_hist": 5.0} # macd > signal
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1h",
            timestamp=datetime(2023, 1, 1, 1, 0, tzinfo=UTC),
            features_json={"close": 9800.0, "macd": -5.0, "macd_signal": 0.0, "macd_hist": -5.0} # macd crosses below signal
        )
    ]
    
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_HOUR, snapshots)
    assert decision is not None
    assert decision.action == DecisionAction.HOLD
    assert decision.confidence == 0.0

def test_macd_cross_no_signal():
    strategy = MACDStrategy()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1h",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "macd": -10.0, "macd_signal": -5.0, "macd_hist": -5.0}
        ),
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1h",
            timestamp=datetime(2023, 1, 1, 1, 0, tzinfo=UTC),
            features_json={"close": 9900.0, "macd": -12.0, "macd_signal": -6.0, "macd_hist": -6.0} # still below
        )
    ]
    
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_HOUR, snapshots)
    assert decision is not None
    assert decision.action == DecisionAction.HOLD

def test_macd_cross_missing_features():
    strategy = MACDStrategy()
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="1h",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "macd": -10.0} # missing signal
        )
    ] * 2
    
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_HOUR, snapshots)
    assert decision is None
