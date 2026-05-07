from datetime import UTC, datetime

from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider, SystemTimeProvider


def test_system_time_provider_returns_timezone_aware_utc_datetime() -> None:
    now = SystemTimeProvider().now()

    assert now.tzinfo is not None
    assert now.utcoffset() is not None


def test_fixed_time_provider_returns_fixed_utc_time() -> None:
    fixed = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    provider = FixedTimeProvider(fixed)

    assert provider.now() == fixed
