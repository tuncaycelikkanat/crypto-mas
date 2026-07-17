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

        end_idx = len(cached_candles)
        if e_time:
            for i in range(len(cached_candles) - 1, -1, -1):
                c = cached_candles[i]
                c_time = c.open_time
                if c_time.tzinfo is None:
                    c_time = c_time.replace(tzinfo=timezone.utc)
                if c_time <= e_time:
                    end_idx = i + 1
                    break
            else:
                end_idx = 0

        start_idx = 0
        if limit is not None:
            start_idx = max(0, end_idx - limit)
            
        filtered = cached_candles[start_idx:end_idx]
        
        if s_time:
            filtered = [c for c in filtered if (c.open_time.replace(tzinfo=timezone.utc) if c.open_time.tzinfo is None else c.open_time) >= s_time]
            
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

    def get_latest(self, exchange: str, symbol: str, timeframe: str, end_time: datetime | None = None) -> FeatureSnapshot | None:
        key = f"{exchange}_{symbol}_{timeframe}"
        if key in self.cache and self.cache[key]:
            if end_time:
                # Find the latest snapshot <= end_time
                from datetime import timezone
                e_time = end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)
                for i in range(len(self.cache[key]) - 1, -1, -1):
                    snap = self.cache[key][i]
                    s_time = getattr(snap, "snapshot_time", getattr(snap, "timestamp", None))
                    s_time = s_time if s_time.tzinfo else s_time.replace(tzinfo=timezone.utc)
                    if s_time <= e_time:
                        return snap
                return None
            return self.cache[key][-1]
        return self.db_repo.get_latest(exchange, symbol, timeframe, end_time=end_time)

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

        # Since cached_snaps is sorted by time, we can search backwards to find the relevant elements in O(1) time
        end_idx = len(cached_snaps)
        if e_time:
            # Find the last element <= e_time
            for i in range(len(cached_snaps) - 1, -1, -1):
                s = cached_snaps[i]
                s_time_val = getattr(s, "snapshot_time", getattr(s, "timestamp", None))
                if s_time_val.tzinfo is None:
                    s_time_val = s_time_val.replace(tzinfo=timezone.utc)
                if s_time_val <= e_time:
                    end_idx = i + 1
                    break
            else:
                end_idx = 0

        start_idx = 0
        if limit is not None:
            start_idx = max(0, end_idx - limit)
            
        filtered = cached_snaps[start_idx:end_idx]
        
        # If start_time is provided, filter the resulting small list
        if s_time:
            filtered = [s for s in filtered if getattr(s, "snapshot_time", getattr(s, "timestamp", None)).replace(tzinfo=timezone.utc) >= s_time]
            
        return filtered
