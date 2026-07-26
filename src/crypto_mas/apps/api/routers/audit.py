"""
audit.py — FastAPI Router for Explainable AI (XAI) Decision Audit Trails.

Endpoints:
    GET /api/v1/audit/latest
    GET /api/v1/audit/symbol/{symbol}
    GET /api/v1/audit/stats
    POST /api/v1/audit/log
"""
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from crypto_mas.services.audit_service.decision_audit_service import (
    DecisionAuditRecord,
    DecisionAuditService,
)

router = APIRouter(prefix="/api/v1/audit", tags=["Decision Audit (XAI)"])


class LogAuditRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol, e.g. BTCUSDT")
    decision: str = Field(..., description="Decision direction: LONG, SHORT, HOLD, REJECTED")
    audit_trail: dict[str, Any] = Field(default_factory=dict, description="Detailed engine scores")
    exchange: str = "MOCK"
    timeframe: str = "4h"
    notes: str | None = None


@router.get("/latest", response_model=list[DecisionAuditRecord])
def get_latest_audits(limit: int = Query(50, ge=1, le=500)) -> list[DecisionAuditRecord]:
    """Retrieve the latest decision audit records across all symbols."""
    service = DecisionAuditService.get_instance()
    return service.get_latest(limit=limit)


@router.get("/symbol/{symbol}", response_model=list[DecisionAuditRecord])
def get_symbol_audits(
    symbol: str,
    limit: int = Query(50, ge=1, le=500),
) -> list[DecisionAuditRecord]:
    """Retrieve decision audit records for a specific symbol."""
    service = DecisionAuditService.get_instance()
    return service.get_by_symbol(symbol=symbol, limit=limit)


@router.get("/stats")
def get_audit_stats() -> dict[str, Any]:
    """Retrieve summary statistics of decision audit buffer."""
    service = DecisionAuditService.get_instance()
    return service.get_summary_stats()


@router.post("/log", response_model=DecisionAuditRecord, status_code=201)
def log_audit_record(payload: LogAuditRequest) -> DecisionAuditRecord:
    """Manually log a decision audit record (useful for external scripts or engines)."""
    service = DecisionAuditService.get_instance()
    return service.log_decision(
        symbol=payload.symbol,
        decision=payload.decision,
        audit_trail=payload.audit_trail,
        exchange=payload.exchange,
        timeframe=payload.timeframe,
        notes=payload.notes,
    )
