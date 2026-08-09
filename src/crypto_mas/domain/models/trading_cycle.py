from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from crypto_mas.infrastructure.db.base import Base
from crypto_mas.domain.value_objects.enums import CycleStatus



class TradingCycle(Base):
    __tablename__ = "trading_cycles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    account_name: Mapped[str] = mapped_column(String(64), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CycleStatus.RUNNING)
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)

    symbols_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decisions_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trades_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    starting_equity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=Decimal("0"))
    ending_equity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=Decimal("0"))
    cycle_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=Decimal("0"))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
