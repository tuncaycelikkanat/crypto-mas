
from crypto_mas.engine.strategy.hft_momentum import HFTMomentumStrategy
from crypto_mas.engine.strategy.realtime_metrics import RealtimeMetricsStore
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def test_hft_momentum_no_trigger():
    store = RealtimeMetricsStore()
    store.set_metric("BTCUSDT", "volume_spike", False)
    
    strategy = HFTMomentumStrategy()
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.ONE_MINUTE, [])
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
    decision = strategy.decide(Exchange.BINANCE, "ETHUSDT", Timeframe.ONE_MINUTE, [])
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
    decision = strategy.decide(Exchange.BINANCE, "SOLUSDT", Timeframe.ONE_MINUTE, [])
    assert decision is not None
    assert decision.action == DecisionAction.HOLD
    assert decision.confidence == 0.0
