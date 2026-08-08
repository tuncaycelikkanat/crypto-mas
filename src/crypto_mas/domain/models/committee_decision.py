import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, JSON, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from crypto_mas.infrastructure.db.base import Base

class CommitteeDecision(Base):
    __tablename__ = "committee_decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    symbol: Mapped[str] = mapped_column(String, index=True)
    market_regime: Mapped[str] = mapped_column(String)  # BULL/BEAR/RANGE/HIGH_VOLATILITY
    votes: Mapped[dict] = mapped_column(JSON)           # list of agent votes
    consensus_score: Mapped[float] = mapped_column(Numeric(5,2))
    final_decision: Mapped[str] = mapped_column(String) # LONG | SHORT | PASS
    source: Mapped[str] = mapped_column(String)         # llm_committee | rule_based_fallback
    shadow_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    reasoning: Mapped[str | None] = mapped_column(String, nullable=True)

    shadow_trade: Mapped["ShadowModeTrade"] = relationship("ShadowModeTrade", back_populates="decision")
