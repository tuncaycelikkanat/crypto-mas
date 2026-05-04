from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    exchange: Mapped[str] = mapped_column(String(32), nullable=False, default="BINANCE")
    symbol: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    base_asset: Mapped[str] = mapped_column(String(32), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(32), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="TRADING")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_stablecoin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_leveraged_token: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    listing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delisting_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("exchange", "symbol", name="uq_symbols_exchange_symbol"),
        Index("ix_symbols_exchange_symbol", "exchange", "symbol"),
    )
