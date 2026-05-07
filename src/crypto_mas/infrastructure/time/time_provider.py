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
