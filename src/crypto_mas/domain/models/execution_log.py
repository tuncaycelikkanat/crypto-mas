from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from crypto_mas.infrastructure.db.base import Base


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    account_name: Mapped[str] = mapped_column(String(64), nullable=False)
    cycle_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("trading_cycles.id"), nullable=True)

    level: Mapped[str] = mapped_column(String(16), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
