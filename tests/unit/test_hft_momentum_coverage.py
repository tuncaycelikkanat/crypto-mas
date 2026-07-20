from datetime import UTC, datetime

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.strategy.hft_momentum import HFTMomentumStrategy
from crypto_mas.engine.strategy.realtime_metrics import RealtimeMetricsStore
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def _get_dummy_snapshot(symbol: str, features_json: dict) -> FeatureSnapshot:
    return FeatureSnapshot(
        exchange=Exchange.BINANCE.value,
        symbol=symbol,
        timeframe=Timeframe.ONE_MINUTE.value,
        timestamp=datetime.now(UTC),
        features_json=features_json
    )

def test_hft_momentum_no_trigger():
    store = RealtimeMetricsStore()
    store.set_metric("BTCUSDT", "volume_spike", False)
    
    strategy = HFTMomentumStrategy()
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_MINUTE, [_get_dummy_snapshot("BTCUSDT", {"close": 1000.0, "ema_20": 1000, "ema_50": 900, "adx_14": 30, "rsi_14": 50})])
    assert decision is None

def test_hft_momentum_buy_trigger():
    store = RealtimeMetricsStore()
    store.set_metric("ETHUSDT", "volume_spike", True)
    store.set_metric("ETHUSDT", "vwap", 1000.0)
    store.set_metric("ETHUSDT", "last_price", 1003.0)
    store.set_metric("ETHUSDT", "imbalance", 0.65)
    store.set_metric("ETHUSDT", "depth_imbalance", 0.6)
    store.set_metric("ETHUSDT", "cvd", 50000.0)
    store.set_metric("ETHUSDT", "rvol_live", 3.0)
    store.set_metric("ETHUSDT", "window_notional", 100000.0)

    strategy = HFTMomentumStrategy()
    decision = strategy.decide(Exchange.BINANCE, "ETHUSDT", Timeframe.ONE_MINUTE, [_get_dummy_snapshot("ETHUSDT", {"close": 1003.0, "ema_20": 1000, "ema_50": 900, "adx_14": 30, "rsi_14": 30})])
    assert decision is not None
    assert decision.action == DecisionAction.CONSIDER_LONG
    assert decision.confidence > 0.6

def test_hft_momentum_sell_trigger():
    store = RealtimeMetricsStore()
    store.set_metric("SOLUSDT", "volume_spike", True)
    store.set_metric("SOLUSDT", "vwap", 100.0)
    store.set_metric("SOLUSDT", "last_price", 99.0)
    store.set_metric("SOLUSDT", "imbalance", 0.35)
    
    strategy = HFTMomentumStrategy()
    # For SHORT, we need ema_20 < ema_50 (downtrend)
    # last_price is 99.0. If ema_20=100.0, dist = (99-100)/100 = -0.01. For SHORT this is REJECTED because dist < -0.006.
    # We want dist around 0. Let's make ema_20=99.0
    decision = strategy.decide(Exchange.BINANCE, "SOLUSDT", Timeframe.ONE_MINUTE, [_get_dummy_snapshot("SOLUSDT", {"close": 99.0, "ema_20": 99.0, "ema_50": 110.0, "adx_14": 30, "rsi_14": 70})])
    assert decision is not None
    assert decision.action == DecisionAction.CONSIDER_SHORT
    assert decision.confidence > 0.6
