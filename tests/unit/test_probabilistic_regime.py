from datetime import UTC, datetime
import pytest

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime import MarketRegime
from crypto_mas.engine.regime.probabilistic_regime import MarkovRegimeEngine


def test_markov_regime_engine_bull_trend():
    engine = MarkovRegimeEngine()
    now = datetime.now(UTC)

    # Bullish features: EMA20 > EMA50, high ADX, low BB width
    snap = FeatureSnapshot(
        exchange="BINANCE",
        symbol="BTCUSDT",
        timeframe="4h",
        timestamp=now,
        available_at=now,
        features_json={
            "close": 60000.0,
            "ema_20": 59000.0,
            "ema_50": 56000.0,
            "adx_14": 35.0,
            "atr_14": 1200.0,
            "bb_upper": 62000.0,
            "bb_middle": 59000.0,
            "bb_lower": 56000.0,
        },
    )

    state = engine.evaluate_probabilities(
        snapshots=[snap],
        previous_regime=MarketRegime.BULL_TREND,
    )

    assert state.primary_regime == MarketRegime.BULL_TREND
    assert state.probabilities[MarketRegime.BULL_TREND] > 0.50
    assert pytest.approx(sum(state.probabilities.values()), 0.01) == 1.0
    assert state.entropy >= 0.0


def test_markov_regime_engine_high_volatility_transition():
    engine = MarkovRegimeEngine(entropy_threshold=0.8)
    now = datetime.now(UTC)

    # Very wide BB and huge ATR
    snap = FeatureSnapshot(
        exchange="BINANCE",
        symbol="BTCUSDT",
        timeframe="4h",
        timestamp=now,
        available_at=now,
        features_json={
            "close": 50000.0,
            "ema_20": 50000.0,
            "ema_50": 50000.0,
            "adx_14": 15.0,
            "atr_14": 5000.0,  # 10% ATR
            "bb_upper": 60000.0,
            "bb_middle": 50000.0,
            "bb_lower": 40000.0,
        },
    )

    state = engine.evaluate_probabilities(
        snapshots=[snap],
        previous_regime=MarketRegime.SIDEWAYS,
    )

    assert state.probabilities[MarketRegime.HIGH_VOLATILITY] > 0.30
