from collections.abc import Sequence
from datetime import datetime

from crypto_mas.domain.models.candle import Candle
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository


class InMemoryCandleRepository:
    """
    An in-memory proxy for CandleRepository.
    Loads all requested candles into RAM once, and serves them instantly
    without hitting the SQLite database.
    """
    def __init__(self, db_repo: CandleRepository):
        self.db_repo = db_repo
        self.cache: dict[str, list[Candle]] = {}

    def preload(self, exchange: str, symbols: list[str], timeframe: str, start_time: datetime, end_time: datetime):
        """Loads all required candles into memory."""
        for symbol in symbols:
            key = f"{exchange}_{symbol}_{timeframe}"
            candles = self.db_repo.list_by_symbol(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time
            )
            # Ensure they are sorted ascending by open_time
            candles.sort(key=lambda c: c.open_time)
            self.cache[key] = candles

    def bulk_upsert(self, candles: Sequence) -> int:
        return self.db_repo.bulk_upsert(candles)

    def list_by_symbol(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        key = f"{exchange}_{symbol}_{timeframe}"
        if key not in self.cache:
            # Auto-preload full history on first read
            # For backtesting, we just load everything available in DB for this symbol/tf
            candles = self.db_repo.list_by_symbol(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                limit=None
            )
            candles.sort(key=lambda c: c.open_time)
            self.cache[key] = candles

        cached_candles = self.cache[key]
        
        filtered = []
        from datetime import timezone
        
        # Ensure start/end are aware
        s_time = start_time
        if s_time and s_time.tzinfo is None:
            s_time = s_time.replace(tzinfo=timezone.utc)
            
        e_time = end_time
        if e_time and e_time.tzinfo is None:
            e_time = e_time.replace(tzinfo=timezone.utc)

        for c in cached_candles:
            c_time = c.open_time
            if c_time.tzinfo is None:
                c_time = c_time.replace(tzinfo=timezone.utc)
                
            if s_time and c_time < s_time:
                continue
            if e_time and c_time > e_time:
                break
            filtered.append(c)

        if limit is not None:
            return filtered[-limit:]
            
        return filtered


from typing import Any

class InMemoryFeatureSnapshotRepository:
    """
    An in-memory proxy for FeatureSnapshotRepository.
    Saves features only to RAM during backtest loops to prevent massive SQLite disk I/O.
    """
    def __init__(self, db_repo: FeatureSnapshotRepository):
        self.db_repo = db_repo
        self.cache: dict[str, list[FeatureSnapshot]] = {}

    def bulk_upsert(self, snapshots: Sequence[dict[str, Any]]) -> int:
        if not snapshots:
            return 0
        
        # Only process the last snapshot if we already have data, otherwise process all 
        # (to warm up the cache on the first cycle)
        first_snap = snapshots[0]
        key = f"{first_snap['exchange']}_{first_snap['symbol']}_{first_snap['timeframe']}"
        
        if key not in self.cache:
            self.cache[key] = []
            snaps_to_add = snapshots
        else:
            # For subsequent cycles, we only care about the latest snapshot
            snaps_to_add = [snapshots[-1]]
            
        added = 0
        for snap_dict in snaps_to_add:
            # Skip if we already have this timestamp
            if self.cache[key] and self.cache[key][-1].timestamp >= snap_dict["timestamp"]:
                continue
                
            snap = FeatureSnapshot(
                exchange=snap_dict["exchange"],
                symbol=snap_dict["symbol"],
                timeframe=snap_dict["timeframe"],
                timestamp=snap_dict["timestamp"],
                available_at=snap_dict["available_at"],
                features_json=snap_dict["features_json"]
            )
            self.cache[key].append(snap)
            added += 1
            
        return added

    def get_latest(self, exchange: str, symbol: str, timeframe: str) -> FeatureSnapshot | None:
        key = f"{exchange}_{symbol}_{timeframe}"
        if key in self.cache and self.cache[key]:
            return self.cache[key][-1]
        return self.db_repo.get_latest(exchange, symbol, timeframe)

    def list_by_symbol(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[FeatureSnapshot]:
        key = f"{exchange}_{symbol}_{timeframe}"
        if key not in self.cache:
            return self.db_repo.list_by_symbol(exchange, symbol, timeframe, start_time, end_time, limit)

        cached_snaps = self.cache[key]
        
        filtered = []
        from datetime import timezone
        
        s_time = start_time
        if s_time and s_time.tzinfo is None:
            s_time = s_time.replace(tzinfo=timezone.utc)
            
        e_time = end_time
        if e_time and e_time.tzinfo is None:
            e_time = e_time.replace(tzinfo=timezone.utc)

        for s in cached_snaps:
            s_time_val = s.snapshot_time if hasattr(s, "snapshot_time") else s.timestamp
            if s_time_val.tzinfo is None:
                s_time_val = s_time_val.replace(tzinfo=timezone.utc)
                
            if s_time and s_time_val < s_time:
                continue
            if e_time and s_time_val > e_time:
                break
            filtered.append(s)

        if limit is not None:
            return filtered[-limit:]
            
        return filtered
