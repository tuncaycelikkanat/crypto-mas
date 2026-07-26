"""
decision_audit_service.py — Explainable AI (XAI) Decision Audit Trail Service.

Records every algorithmic trading evaluation and decision with full mathematical
traceability across Trend, Scoring, Regime, and Risk engines.
Stores records in an in-memory ring buffer (default 500) and appends to JSONL log file.
"""
import json
import logging
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field

logger = logging.getLogger("crypto_mas.decision_audit_service")


class DecisionAuditRecord(BaseModel):
    """Immutable audit trail record for a single symbol evaluation."""

    audit_id: str
    timestamp: str
    symbol: str
    exchange: str
    timeframe: str
    decision: str  # "LONG", "SHORT", "HOLD", "REJECTED", etc.
    audit_trail: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class DecisionAuditService:
    """Singleton service for recording and retrieving decision audit trails."""

    _instance: ClassVar["DecisionAuditService | None"] = None
    _lock_class: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, log_file_path: str | Path | None = None, max_buffer_size: int = 500):
        self.max_buffer_size = max_buffer_size
        self._buffer: list[DecisionAuditRecord] = []
        self._lock = threading.Lock()

        if log_file_path is None:
            self.log_file_path = Path("logs") / "decision_audit_trail.jsonl"
        else:
            self.log_file_path = Path(log_file_path)

        # Ensure parent dir exists
        try:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create directory for audit log: %s", exc)

    @classmethod
    def get_instance(cls, log_file_path: str | Path | None = None) -> "DecisionAuditService":
        with cls._lock_class:
            if cls._instance is None:
                cls._instance = cls(log_file_path=log_file_path)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock_class:
            cls._instance = None

    def log_decision(
        self,
        symbol: str,
        decision: str,
        audit_trail: dict[str, Any],
        exchange: str = "MOCK",
        timeframe: str = "4h",
        notes: str | None = None,
    ) -> DecisionAuditRecord:
        """Create, buffer, and persist a decision audit record."""
        record = DecisionAuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            symbol=symbol.upper(),
            exchange=exchange,
            timeframe=timeframe,
            decision=decision.upper(),
            audit_trail=audit_trail,
            notes=notes,
        )

        with self._lock:
            self._buffer.append(record)
            if len(self._buffer) > self.max_buffer_size:
                self._buffer.pop(0)

        # Persist asynchronously / safely to JSONL
        try:
            line = record.model_dump_json() + "\n"
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:
            logger.warning("Failed to write audit record to file: %s", exc)

        return record

    def get_latest(self, limit: int = 50) -> list[DecisionAuditRecord]:
        """Return the latest N audit records in reverse chronological order (newest first)."""
        with self._lock:
            return list(reversed(self._buffer))[:limit]

    def get_by_symbol(self, symbol: str, limit: int = 50) -> list[DecisionAuditRecord]:
        """Return latest N audit records for a specific symbol."""
        sym = symbol.upper()
        with self._lock:
            filtered = [r for r in self._buffer if r.symbol == sym]
            return list(reversed(filtered))[:limit]

    def get_summary_stats(self) -> dict[str, Any]:
        """Return counts of decisions across the current memory buffer."""
        with self._lock:
            total = len(self._buffer)
            counts: dict[str, int] = {}
            for r in self._buffer:
                counts[r.decision] = counts.get(r.decision, 0) + 1
            return {
                "total_records_in_buffer": total,
                "decision_counts": counts,
                "max_buffer_size": self.max_buffer_size,
            }
