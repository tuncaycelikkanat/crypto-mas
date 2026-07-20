from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from crypto_mas.infrastructure.db.base import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    account_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)

    side: Mapped[str] = mapped_column(String(16), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    notional: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=Decimal("0"))

    position_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("positions.id"), nullable=True)
    cycle_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("trading_cycles.id"), nullable=True)

    reason: Mapped[str] = mapped_column(String(255), nullable=False)

    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
