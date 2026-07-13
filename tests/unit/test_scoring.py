from datetime import UTC, datetime

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.scoring.scoring import ScoringEngine
from crypto_mas.engine.signal import SignalDirection, TradingSignal
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def get_dummy_signal(direction: SignalDirection) -> TradingSignal:
    return TradingSignal(
        exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.FIFTEEN_MINUTES,
        signal_type="TREND_FOLLOWING", direction=direction, strength=1.0,
        indicators={}, reason="Mock", timestamp=datetime.now(UTC)
    )

def test_calculate_score_bullish():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9500.0, "ema_50": 9000.0, "rsi_14": 60.0, "roc_14": 5.0, "atr_14": 100.0, "macd": 50.0, "macd_signal": 40.0}
        )
    ] * 3
    
    score = ScoringEngine().score(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, get_dummy_signal(SignalDirection.LONG), snapshots)
    assert score is not None
    assert score.direction == SignalDirection.LONG
    assert score.trend_score > 0
    assert score.momentum_score > 0
    assert score.final_score > 0

def test_calculate_score_bearish():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 8000.0, "ema_20": 8500.0, "ema_50": 9000.0, "rsi_14": 40.0, "roc_14": -5.0, "atr_14": 100.0, "macd": -50.0, "macd_signal": -40.0}
        )
    ] * 3
    
    score = ScoringEngine().score(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, get_dummy_signal(SignalDirection.SHORT), snapshots)
    assert score is not None
    assert score.direction == SignalDirection.SHORT
    assert score.trend_score > 0
    assert score.momentum_score > 0
    assert score.final_score > 0

def test_calculate_score_neutral():
    score = ScoringEngine().score(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, get_dummy_signal(SignalDirection.NEUTRAL), [])
    assert score is None

def test_calculate_score_missing_features():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0} # missing ema_50, roc_14, atr_14
        )
    ] * 3
    score = ScoringEngine().score(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, get_dummy_signal(SignalDirection.LONG), snapshots)
    # The Scoring engine will return a score with reason="Not enough feature data." and 0s.
    assert score is not None
    assert score.final_score == 0.0
    assert score.reason == "Not enough feature data."

def test_calculate_score_high_volatility_penalty():
    snapshots = [
        FeatureSnapshot(
            exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe="15m",
            timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            features_json={"close": 10000.0, "ema_20": 9500.0, "ema_50": 9000.0, "rsi_14": 60.0, "roc_14": 5.0, "atr_14": 1000.0, "macd": 50.0, "macd_signal": 40.0} # ATR is 10%
        )
    ] * 3
    score = ScoringEngine().score(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, get_dummy_signal(SignalDirection.LONG), snapshots)
    assert score is not None
    assert score.volatility_penalty > 0
    assert score.final_score < score.trend_score + score.momentum_score
