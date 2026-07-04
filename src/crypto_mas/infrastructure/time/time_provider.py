from datetime import UTC, datetime
from typing import Protocol


class TimeProvider(Protocol):
    def now(self) -> datetime:
        """Return current time as timezone-aware UTC datetime."""
        ...


class SystemTimeProvider:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedTimeProvider:
    def __init__(self, fixed_time: datetime) -> None:
        if fixed_time.tzinfo is None:
            fixed_time = fixed_time.replace(tzinfo=UTC)

        self.fixed_time = fixed_time.astimezone(UTC)

    def now(self) -> datetime:
        return self.fixed_time

from datetime import timedelta

class SimulatedTimeProvider:
    def __init__(self, start_time: datetime) -> None:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        self.current_time = start_time.astimezone(UTC)

    def now(self) -> datetime:
        return self.current_time

    def tick(self, delta: timedelta) -> None:
        """Saves current time by delta"""
        self.current_time += delta

    def set_time(self, new_time: datetime) -> None:
        if new_time.tzinfo is None:
            new_time = new_time.replace(tzinfo=UTC)
        self.current_time = new_time.astimezone(UTC)
