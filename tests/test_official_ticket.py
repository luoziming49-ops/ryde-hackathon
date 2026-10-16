"""S1 PART B tests: the organiser's official DISP-002 ticket format."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.adapters.official_ticket import is_official_ticket, normalize_official_ticket
from backend.core.evidence import analyze_evidence

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_FILE = ROOT / "sample_data" / "official" / "DISP-002.json"


def _load_official() -> dict:
    return json.loads(OFFICIAL_FILE.read_text(encoding="utf-8"))


def test_disp002_adapter_field_by_field():
    ticket = _load_official()
    assert is_official_ticket(ticket) is True

    normalized = normalize_official_ticket(ticket)
    assert normalized["case_id"] == "DISP-002"
    assert normalized["category"] == "no_show"
    assert normalized["gps"]["driver_arrival"]["arrived"] is True
    assert normalized["gps"]["driver_arrival"]["wait_time_min"] == pytest.approx(8.0)
    assert normalized["gps"]["driver_arrival"]["late_min"] == 0.0
    assert normalized["fare"]["cancellation_fee"] == 5.0
    # dispute_history object -> int
    assert normalized["rider"]["dispute_history"] == 4
    assert normalized["driver"]["dispute_history"] == 1
    # fraud flags
    assert "high rate of rejected disputes" in normalized["rider"]["fraud_flags_list"]
    assert normalized["driver"]["fraud_flags_list"] == []
    # raw app events kept
    assert normalized["raw_app_events"] == ticket["app_events"]

    evidence = analyze_evidence(normalized)
    assert evidence.driver_arrived is True
    assert evidence.driver_wait_min == pytest.approx(8.0)
    assert evidence.driver_late_min == 0.0
    assert evidence.driver_contact_attempts == 5
    assert evidence.driver_call_attempts == 1
    assert evidence.free_wait_min == 5.0


def test_disp002_end_to_end_no_action(client):
    ticket = _load_official()
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 200
    body = r.json()
    ruling = body["ruling"]
    assert ruling["action"] == "no_action"
    assert ruling["escalated"] is False
    assert ruling["amount"] == 0.0
    # app_events surfaced verbatim in the response
    assert body["raw_app_events"] == ticket["app_events"]


def test_missing_cancellation_policy_falls_back_to_defaults():
    ticket = _load_official()
    ticket.pop("cancellation_policy")
    normalized = normalize_official_ticket(ticket)
    assert normalized["cancellation_policy_override"] == {}
    evidence = analyze_evidence(normalized)
    assert evidence.free_wait_min is None  # policy falls back to global 5 min


def test_missing_app_events_derives_arrival_from_telemetry():
    ticket = _load_official()
    ticket.pop("app_events")
    normalized = normalize_official_ticket(ticket)
    assert normalized["gps"]["driver_arrival"]["arrived"] is True
    evidence = analyze_evidence(normalized)
    assert evidence.driver_arrived is True
    assert evidence.driver_wait_min == pytest.approx(8.0)


def test_unknown_dispute_type_escalates(client):
    ticket = _load_official()
    ticket["dispute_ticket"]["dispute_type"] = "fare_dispute"
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 200
    ruling = r.json()["ruling"]
    assert ruling["escalated"] is True
    assert ruling["action"] == "escalate"
