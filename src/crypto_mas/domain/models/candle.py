from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from crypto_mas.infrastructure.db.base import Base


class Candle(Base):
    __tablename__ = "candles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False, default="BINANCE")

    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)

    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    open: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)

    volume: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 10), nullable=True)

    trade_count: Mapped[int | None] = mapped_column(nullable=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="BINANCE")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "exchange",
            "symbol",
            "timeframe",
            "open_time",
            name="uq_candles_exchange_symbol_tf_open",
        ),
        Index("ix_candles_exchange_symbol_tf_open", "exchange", "symbol", "timeframe", "open_time"),
    )
