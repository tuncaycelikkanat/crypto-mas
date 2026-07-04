from datetime import UTC, datetime

from crypto_mas.engine.scoring.scoring import ScoringEngine
from crypto_mas.engine.signal import SignalDirection, SignalType, TradingSignal
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def test_scoring_agent_scores_long_signal() -> None:
    snapshot = FeatureSnapshot(
        exchange="MOCK",
        symbol="BTCUSDT",
        timeframe="4h",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 1, 1, tzinfo=UTC),
        features_json={
            "close": 110.0,
            "ema_20": 105.0,
            "ema_50": 100.0,
            "rsi_14": 60.0,
            "roc_14": 5.0,
            "atr_14": 2.0,
        },
    )

    signal = TradingSignal(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        signal_type=SignalType.TREND_FOLLOWING,
        direction=SignalDirection.LONG,
        strength=0.5,
        reason="test",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )

    score = ScoringEngine().score(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        signal=signal,
        snapshots=[snapshot],
    )

    assert score is not None
    assert score.direction == SignalDirection.LONG
    assert score.final_score > 0
    assert score.trend_score > 0
    assert score.momentum_score > 0


def test_scoring_agent_returns_zero_for_neutral_signal() -> None:
    snapshot = FeatureSnapshot(
        exchange="MOCK",
        symbol="BTCUSDT",
        timeframe="4h",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 1, 1, tzinfo=UTC),
        features_json={
            "close": 110.0,
            "ema_20": 105.0,
            "ema_50": 100.0,
            "rsi_14": 60.0,
            "roc_14": 5.0,
            "atr_14": 2.0,
        },
    )

    signal = TradingSignal(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        signal_type=SignalType.TREND_FOLLOWING,
        direction=SignalDirection.NEUTRAL,
        strength=0.0,
        reason="test",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )

    score = ScoringEngine().score(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        signal=signal,
        snapshots=[snapshot],
    )

    assert score is not None
    assert score.final_score == 0
