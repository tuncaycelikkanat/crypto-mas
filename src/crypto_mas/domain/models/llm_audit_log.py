import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from crypto_mas.infrastructure.db.base import Base

class LLMAuditLog(Base):
    __tablename__ = "llm_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    symbol: Mapped[str] = mapped_column(String, index=True)
    agent_name: Mapped[str] = mapped_column(String)  # 'TechnicalAgent' | 'SentimentAgent' | 'RiskAgent' | 'ChairAgent'
    prompt: Mapped[str] = mapped_column(String)
    response_json: Mapped[dict] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String)
    prompt_template_version: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    fallback_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
