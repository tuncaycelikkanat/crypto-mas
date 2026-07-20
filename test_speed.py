import time
from datetime import UTC, datetime

from crypto_mas.services.backtesting.memory_cache import InMemoryFeatureSnapshotRepository


class DummyRepo:
    def list_by_symbol(self, *args, **kwargs):
        return []

repo = InMemoryFeatureSnapshotRepository(DummyRepo())
snapshots = []
now = datetime.now(UTC)

# Insert 21600 items for 10 symbols
for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT"]:
    snaps = []
    for _i in range(21600):
        snaps.append({
            "exchange": "BINANCE",
            "symbol": sym,
            "timeframe": "1m",
            "timestamp": now,
            "available_at": now,
            "features_json": {"rsi_14": 50, "imbalance": 0.1, "macd": 1}
        })
    repo.bulk_upsert(snaps)

t0 = time.time()
for _ in range(100): # 100 cycles
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT"]:
        repo.list_by_symbol("BINANCE", sym, "1m", end_time=now, limit=100)
t1 = time.time()
print(f"100 cycles took: {t1-t0}s. 1 cycle = {(t1-t0)/100}s")
