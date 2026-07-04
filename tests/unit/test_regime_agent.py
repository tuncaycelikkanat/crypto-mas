from datetime import UTC, datetime

from crypto_mas.engine.regime.regime import RegimeEngine
from crypto_mas.engine.regime import MarketRegime
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def test_regime_agent_detects_bull_trend() -> None:
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
            "atr_14": 2.0,
            "roc_14": 5.0,
        },
    )

    regime = RegimeEngine().detect(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=[snapshot],
    )

    assert regime is not None
    assert regime.regime == MarketRegime.BULL_TREND
    assert regime.risk_multiplier == 1.0


def test_regime_agent_detects_bear_trend() -> None:
    snapshot = FeatureSnapshot(
        exchange="MOCK",
        symbol="BTCUSDT",
        timeframe="4h",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 1, 1, tzinfo=UTC),
        features_json={
            "close": 90.0,
            "ema_20": 95.0,
            "ema_50": 100.0,
            "atr_14": 2.0,
            "roc_14": -5.0,
        },
    )

    regime = RegimeEngine().detect(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=[snapshot],
    )

    assert regime is not None
    assert regime.regime == MarketRegime.BEAR_TREND
    assert regime.risk_multiplier == 0.30


def test_regime_agent_detects_high_volatility() -> None:
    snapshot = FeatureSnapshot(
        exchange="MOCK",
        symbol="BTCUSDT",
        timeframe="4h",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 1, 1, tzinfo=UTC),
        features_json={
            "close": 100.0,
            "ema_20": 105.0,
            "ema_50": 100.0,
            "atr_14": 10.0,
            "roc_14": 1.0,
        },
    )

    regime = RegimeEngine().detect(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=[snapshot],
    )

    assert regime is not None
    assert regime.regime == MarketRegime.HIGH_VOLATILITY
    assert regime.risk_multiplier == 0.50
