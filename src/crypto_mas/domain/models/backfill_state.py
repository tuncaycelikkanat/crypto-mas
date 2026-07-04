from datetime import UTC, datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from crypto_mas.infrastructure.db.base import Base


class BackfillState(Base):
    __tablename__ = "backfill_states"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)

    last_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("exchange", "symbol", "timeframe", name="uq_backfill_state"),
    )
