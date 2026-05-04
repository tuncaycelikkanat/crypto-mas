from datetime import UTC, datetime, timedelta
from decimal import Decimal

from domain.models.candle import Candle
from services.feature_pipeline.calculator import FeatureCalculator


def _make_candle(index: int) -> Candle:
    open_time = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=4 * index)
    close = Decimal("100") + Decimal(index)

    return Candle(
        exchange="MOCK",
        symbol="BTCUSDT",
        timeframe="4h",
        open_time=open_time,
        close_time=open_time + timedelta(hours=4),
        open=close - Decimal("1"),
        high=close + Decimal("2"),
        low=close - Decimal("2"),
        close=close,
        volume=Decimal("1000"),
        quote_volume=Decimal("100000"),
        trade_count=100,
        source="TEST",
    )


def test_feature_calculator_returns_empty_when_not_enough_candles() -> None:
    candles = [_make_candle(index) for index in range(20)]

    snapshots = FeatureCalculator().calculate(candles)

    assert snapshots == []


def test_feature_calculator_creates_snapshots() -> None:
    candles = [_make_candle(index) for index in range(60)]

    snapshots = FeatureCalculator().calculate(candles)

    assert len(snapshots) == 60

    last_features = snapshots[-1]["features_json"]

    assert last_features["ema_20"] is not None
    assert last_features["ema_50"] is not None
    assert last_features["sma_20"] is not None
    assert last_features["rsi_14"] is not None
    assert last_features["atr_14"] is not None
    assert last_features["roc_14"] is not None
