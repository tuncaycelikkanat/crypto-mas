from datetime import UTC, datetime

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.services.decision_orchestrator.orchestrator import DecisionOrchestrator
from crypto_mas.services.decision_orchestrator.schemas import DecisionAction
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def test_decision_orchestrator_considers_long_when_signal_score_and_regime_align() -> None:
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

    decision = DecisionOrchestrator().run(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=[snapshot],
    )

    assert decision is not None
    assert decision.action == DecisionAction.CONSIDER_LONG
    assert decision.confidence > 0


def test_decision_orchestrator_avoids_high_volatility() -> None:
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
            "atr_14": 10.0,
        },
    )

    decision = DecisionOrchestrator().run(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=[snapshot],
    )

    assert decision is not None
    assert decision.action == DecisionAction.AVOID
