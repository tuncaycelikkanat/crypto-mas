"""Unit tests for DecisionAuditService (Explainable AI / XAI audit trail)."""
import json
from pathlib import Path

import pytest

from crypto_mas.services.audit_service.decision_audit_service import DecisionAuditService


@pytest.fixture(autouse=True)
def clean_service(tmp_path: Path):
    DecisionAuditService.reset_instance()
    log_file = tmp_path / "test_audit.jsonl"
    service = DecisionAuditService.get_instance(log_file_path=log_file)
    yield service
    DecisionAuditService.reset_instance()


def test_log_decision_and_get_latest(clean_service: DecisionAuditService, tmp_path: Path):
    record1 = clean_service.log_decision(
        symbol="BTCUSDT",
        decision="LONG",
        audit_trail={"trend": {"signal": "BULL", "score": 85.0}},
        notes="Strong bull trend",
    )
    record2 = clean_service.log_decision(
        symbol="ETHUSDT",
        decision="HOLD",
        audit_trail={"trend": {"signal": "NEUTRAL", "score": 50.0}},
        notes="Consolidating",
    )

    latest = clean_service.get_latest(limit=10)
    assert len(latest) == 2
    # Reverse chronological (newest first)
    assert latest[0].symbol == "ETHUSDT"
    assert latest[0].decision == "HOLD"
    assert latest[1].symbol == "BTCUSDT"
    assert latest[1].decision == "LONG"
    assert latest[1].audit_id == record1.audit_id

    # Verify JSONL persistence
    log_file = tmp_path / "test_audit.jsonl"
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    parsed1 = json.loads(lines[0])
    assert parsed1["symbol"] == "BTCUSDT"
    assert parsed1["audit_trail"]["trend"]["score"] == 85.0


def test_get_by_symbol_and_summary_stats(clean_service: DecisionAuditService):
    clean_service.log_decision("BTCUSDT", "LONG", {})
    clean_service.log_decision("BTCUSDT", "SHORT", {})
    clean_service.log_decision("SOLUSDT", "HOLD", {})

    btc_records = clean_service.get_by_symbol("BTCUSDT")
    assert len(btc_records) == 2
    assert all(r.symbol == "BTCUSDT" for r in btc_records)

    stats = clean_service.get_summary_stats()
    assert stats["total_records_in_buffer"] == 3
    assert stats["decision_counts"]["LONG"] == 1
    assert stats["decision_counts"]["SHORT"] == 1
    assert stats["decision_counts"]["HOLD"] == 1
