from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from crypto_mas.infrastructure.db.base import Base


class PaperAccount(Base):
    __tablename__ = "paper_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    exchange: Mapped[str] = mapped_column(String(32), nullable=False, default="MOCK")
    base_currency: Mapped[str] = mapped_column(String(16), nullable=False, default="USDT")

    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )
    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )
    equity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

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
