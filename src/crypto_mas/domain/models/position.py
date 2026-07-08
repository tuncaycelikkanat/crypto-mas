from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from crypto_mas.infrastructure.db.base import Base


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    account_name: Mapped[str] = mapped_column(String(64), nullable=False)

    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)

    side: Mapped[str] = mapped_column(String(16), nullable=False, default="LONG")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")

    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    notional_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)

    # Risk management
    stop_loss_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    # Strategy metadata
    strategy_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_positions_account_status", "account_name", "status"),
        Index("ix_positions_exchange_symbol_status", "exchange", "symbol", "status"),
    )
