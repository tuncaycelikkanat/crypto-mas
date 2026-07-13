from crypto_mas.engine.strategy.realtime_metrics import RealtimeMetricsStore


def test_realtime_metrics_singleton():
    store1 = RealtimeMetricsStore()
    store2 = RealtimeMetricsStore()
    assert store1 is store2

def test_realtime_metrics_set_get():
    store = RealtimeMetricsStore()
    store.set_metric("BTCUSDT", "vwap", 50000.0)
    assert store.get_metric("BTCUSDT", "vwap") == 50000.0
    assert store.get_metric("DOGEUSDT", "vwap", 0.0) == 0.0
