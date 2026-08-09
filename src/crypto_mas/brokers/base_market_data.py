"""Shared utilities for market data provider adapters."""

from datetime import UTC, datetime


def to_millis(value: datetime) -> int:
    """Convert a datetime to milliseconds since epoch."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)

    value = value.astimezone(UTC)

    return int(value.timestamp() * 1000)


def from_millis(value: int) -> datetime:
    """Convert milliseconds since epoch to a datetime."""
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def is_stablecoin(base_asset: str) -> bool:
    """Check if a trading pair is a stablecoin pair."""
    stablecoins = {
        "USDT",
        "USDC",
        "FDUSD",
        "TUSD",
        "DAI",
        "BUSD",
        "USDP",
        "EUR",
        "TRY",
    }

    return base_asset.upper() in stablecoins


def is_leveraged_token(symbol: str) -> bool:
    """Check if a symbol is a leveraged token."""
    leveraged_suffixes = (
        "UPUSDT",
        "DOWNUSDT",
        "BULLUSDT",
        "BEARUSDT",
        "3LUSDT",
        "3SUSDT",
        "5LUSDT",
        "5SUSDT",
    )

    return symbol.upper().endswith(leveraged_suffixes)
