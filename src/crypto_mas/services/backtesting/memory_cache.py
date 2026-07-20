"""
In-memory repository proxies for ultra-fast backtesting.

Key design decisions:
- All timestamps are normalized to UTC-aware datetimes exactly ONCE at insert time.
- Binary search (bisect) replaces all O(n) linear scans, giving O(log n) lookups.
- The cache stores pre-sorted lists; no re-sorting on every access.
"""
import bisect
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from crypto_mas.domain.models.candle import Candle
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository


def _to_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC-aware. No-op if already aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# ──────────────────────────────────────────────────────────────────────────────
# Candle cache
# ──────────────────────────────────────────────────────────────────────────────

class InMemoryCandleRepository:
    """
    An in-memory proxy for CandleRepository.

    Loads all requested candles into RAM once, keeps them sorted by open_time,
    and serves range queries with O(log n) binary search instead of O(n) scans.
    """

    def __init__(self, db_repo: CandleRepository) -> None:
        self.db_repo = db_repo
        # key → sorted list of Candles (ascending open_time, UTC-aware)
        self._candles: dict[str, list[Candle]] = {}
        # key → sorted list of UTC-aware timestamps (parallel index for bisect)
        self._times: dict[str, list[datetime]] = {}

    # ── internal helpers ────────────────────────────────────────────────────

    def _load(self, key: str, exchange: str, symbol: str, timeframe: str) -> None:
        """Load and normalize all candles for a (exchange, symbol, timeframe) into cache."""
        candles: list[Candle] = self.db_repo.list_by_symbol(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            limit=None,
        )
        # Normalize tz once and detach from SQLAlchemy session to prevent overhead
        for c in candles:
            c.open_time = _to_utc(c.open_time)
            self.db_repo.db.expunge(c)

        candles.sort(key=lambda c: c.open_time)
        self._candles[key] = candles
        self._times[key] = [c.open_time for c in candles]

    def _ensure(self, key: str, exchange: str, symbol: str, timeframe: str) -> None:
        if key not in self._candles:
            self._load(key, exchange, symbol, timeframe)

    # ── public API ──────────────────────────────────────────────────────────

    def preload(
        self,
        exchange: str,
        symbols: list[str],
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """Eager-load all candles for the given symbols into cache."""
        for symbol in symbols:
            key = f"{exchange}_{symbol}_{timeframe}"
            self._load(key, exchange, symbol, timeframe)

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
        self._ensure(key, exchange, symbol, timeframe)

        times = self._times[key]
        candles = self._candles[key]
        n = len(candles)

        if n == 0:
            return []

        # Binary search for end_time (right boundary, inclusive)
        if end_time is not None:
            e = _to_utc(end_time)
            # rightmost position where time <= e
            end_idx = bisect.bisect_right(times, e)
        else:
            end_idx = n

        # Binary search for start_time (left boundary, inclusive)
        if start_time is not None:
            s = _to_utc(start_time)
            start_idx = bisect.bisect_left(times, s)
        else:
            start_idx = 0

        # Apply limit from the right
        if limit is not None:
            start_idx = max(start_idx, end_idx - limit)

        return candles[start_idx:end_idx]


# ──────────────────────────────────────────────────────────────────────────────
# Feature snapshot cache
# ──────────────────────────────────────────────────────────────────────────────

class InMemoryFeatureSnapshotRepository:
    """
    An in-memory proxy for FeatureSnapshotRepository.

    Stores feature snapshots sorted by timestamp with O(log n) retrieval.
    Writes stay in RAM during the backtest loop — no SQLite disk I/O per tick.
    """

    def __init__(self, db_repo: FeatureSnapshotRepository) -> None:
        self.db_repo = db_repo
        # key → sorted list of FeatureSnapshot (ascending timestamp, UTC-aware)
        self._snaps: dict[str, list[FeatureSnapshot]] = {}
        # key → sorted list of UTC-aware timestamps (parallel index for bisect)
        self._times: dict[str, list[datetime]] = {}

    # ── internal helpers ────────────────────────────────────────────────────

    def _key(self, exchange: str, symbol: str, timeframe: str) -> str:
        return f"{exchange}_{symbol}_{timeframe}"

    def _insert_sorted(self, key: str, snap: FeatureSnapshot) -> None:
        """Insert a snapshot maintaining sorted order (binary search for position)."""
        ts = _to_utc(snap.timestamp)
        snap.timestamp = ts  # normalize in place

        snaps = self._snaps[key]
        times = self._times[key]

        idx = bisect.bisect_left(times, ts)
        if idx < len(times) and times[idx] == ts:
            # Upsert: replace existing snapshot at same timestamp
            snaps[idx] = snap
        else:
            snaps.insert(idx, snap)
            times.insert(idx, ts)

    # ── public API ──────────────────────────────────────────────────────────

    def bulk_upsert(self, snapshots: Sequence[dict[str, Any]]) -> int:
        if not snapshots:
            return 0

        first = snapshots[0]
        key = self._key(first["exchange"], first["symbol"], first["timeframe"])

        if key not in self._snaps:
            self._snaps[key] = []
            self._times[key] = []

        added = 0
        for snap_dict in snapshots:
            ts = _to_utc(snap_dict["timestamp"])
            snap = FeatureSnapshot(
                exchange=snap_dict["exchange"],
                symbol=snap_dict["symbol"],
                timeframe=snap_dict["timeframe"],
                timestamp=ts,
                available_at=snap_dict["available_at"],
                features_json=snap_dict["features_json"],
            )
            self._insert_sorted(key, snap)
            added += 1

        return added

    def get_latest(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        end_time: datetime | None = None,
    ) -> FeatureSnapshot | None:
        key = self._key(exchange, symbol, timeframe)

        if key not in self._snaps or not self._snaps[key]:
            return self.db_repo.get_latest(exchange, symbol, timeframe, end_time=end_time)

        times = self._times[key]
        snaps = self._snaps[key]

        if end_time is None:
            return snaps[-1]

        e = _to_utc(end_time)
        # Rightmost timestamp <= e
        idx = bisect.bisect_right(times, e) - 1
        if idx < 0:
            return None
        return snaps[idx]

    def list_by_symbol(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[FeatureSnapshot]:
        key = self._key(exchange, symbol, timeframe)

        if key not in self._snaps:
            return self.db_repo.list_by_symbol(
                exchange, symbol, timeframe, start_time, end_time, limit
            )

        times = self._times[key]
        snaps = self._snaps[key]
        n = len(snaps)

        if n == 0:
            return []

        if end_time is not None:
            e = _to_utc(end_time)
            end_idx = bisect.bisect_right(times, e)
        else:
            end_idx = n

        if start_time is not None:
            s = _to_utc(start_time)
            start_idx = bisect.bisect_left(times, s)
        else:
            start_idx = 0

        if limit is not None:
            start_idx = max(start_idx, end_idx - limit)

        return snaps[start_idx:end_idx]


# ──────────────────────────────────────────────────────────────────────────────
# Position cache (eliminates all position DB queries during backtest)
# ──────────────────────────────────────────────────────────────────────────────

class InMemoryPositionRepository:
    """
    Fully in-memory drop-in replacement for PositionRepository.

    During backtesting, every position read/write stays in RAM.
    No SQLite queries, no commits, no refreshes — pure Python dicts.

    Wire up in engine.py:
        mem_positions = InMemoryPositionRepository()
        broker.position_repository = mem_positions
        cycle_service._bt_position_repo = mem_positions
    """

    def __init__(self) -> None:
        # symbol -> open Position (only one position per symbol allowed)
        self._open: dict[str, Any] = {}
        # symbol -> expiry datetime for SL cooldown
        self._sl_cooldowns: dict[str, datetime] = {}

    # ── Bulk-query helpers (O(1) set returns) ─────────────────────────────────

    def get_open_position_symbols(self, account_name: str, exchange: str) -> set[str]:
        return set(self._open.keys())

    def get_recent_stop_loss_symbols(
        self,
        account_name: str,
        exchange: str,
        time_now: datetime,
        cooldown_minutes: int = 30,
    ) -> set[str]:
        now = _to_utc(time_now)
        return {sym for sym, exp in self._sl_cooldowns.items() if now < exp}

    # ── Standard PositionRepository interface ─────────────────────────────────

    def list_open_positions(self, account_name: str) -> list:
        return list(self._open.values())

    def get_open_position(self, account_name: str, exchange: str, symbol: str):
        return self._open.get(symbol)

    def has_recent_stop_loss(
        self,
        account_name: str,
        exchange: str,
        symbol: str,
        time_now: datetime,
        cooldown_minutes: int = 30,
    ) -> bool:
        expiry = self._sl_cooldowns.get(symbol)
        if expiry is None:
            return False
        return _to_utc(time_now) < expiry

    def create_open_position(
        self,
        account_name: str,
        exchange: str,
        symbol: str,
        quantity,
        entry_price,
        notional_value,
        opened_at: datetime,
        stop_loss_price=None,
        take_profit_price=None,
        strategy_mode: str | None = None,
        side: str = "LONG",
        skip_commit: bool = False,  # ignored — always skipped
    ):
        from decimal import Decimal

        from crypto_mas.domain.models.position import Position

        position = Position(
            account_name=account_name,
            exchange=exchange,
            symbol=symbol,
            side=side,
            status="OPEN",
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            notional_value=notional_value,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            strategy_mode=strategy_mode,
            opened_at=opened_at,
            closed_at=None,
            close_reason=None,
        )
        self._open[symbol] = position
        return position

    def update_mark_price(self, position, current_price, skip_commit: bool = False):
        from decimal import Decimal

        if position.side == "LONG":
            raw = (current_price - position.entry_price) * position.quantity
        else:
            raw = (position.entry_price - current_price) * position.quantity

        tiny = Decimal("0.00000001")
        position.unrealized_pnl = raw if abs(raw) >= tiny else Decimal("0")
        position.current_price = current_price
        position.notional_value = position.quantity * current_price
        return position

    def update_stop_loss(self, position, stop_loss_price, skip_commit: bool = False):
        position.stop_loss_price = stop_loss_price
        return position

    def close_position(
        self,
        position,
        exit_price,
        closed_at: datetime,
        close_reason: str = "SIGNAL",
        skip_commit: bool = False,  # ignored
    ):
        from datetime import timedelta
        from decimal import Decimal

        if position.side == "LONG":
            raw = (exit_price - position.entry_price) * position.quantity
        else:
            raw = (position.entry_price - exit_price) * position.quantity

        tiny = Decimal("0.00000001")
        position.realized_pnl = raw if abs(raw) >= tiny else Decimal("0")
        position.unrealized_pnl = Decimal("0")
        position.current_price = exit_price
        position.status = "CLOSED"
        position.closed_at = closed_at
        position.close_reason = close_reason

        self._open.pop(position.symbol, None)

        if close_reason == "STOP_LOSS":
            self._sl_cooldowns[position.symbol] = _to_utc(closed_at) + timedelta(minutes=30)

        return position
