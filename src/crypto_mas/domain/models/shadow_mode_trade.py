import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from crypto_mas.infrastructure.db.base import Base

class ShadowModeTrade(Base):
    __tablename__ = "shadow_mode_trades"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    committee_decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("committee_decisions.id"))
    rule_based_decision: Mapped[str] = mapped_column(String)
    entry_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    pnl_pct: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    max_adverse_excursion: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    regime_at_entry: Mapped[str | None] = mapped_column(String, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    decision: Mapped["CommitteeDecision"] = relationship("CommitteeDecision", back_populates="shadow_trade")
