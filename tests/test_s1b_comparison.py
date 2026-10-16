"""S1b tests: three follow-up fixes from the S1 review.

1. Null money fields -> evidence gap (never a silent 0.0).
2. "Driver never arrived" -> full_refund under NS-001.2, not escalated.
3. One resolved arrival time + conflict check; missing scheduled_time -> unknown lateness.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from backend.adapters.official_ticket import normalize_official_ticket
from backend.core.evidence import analyze_evidence
from backend.core.policy import (
    apply_policy,
    NO_ACTION,
    FULL_REFUND,
    INSUFFICIENT_EVIDENCE,
)

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_FILE = ROOT / "sample_data" / "official" / "DISP-002.json"


def _load_official() -> dict:
    return json.loads(OFFICIAL_FILE.read_text(encoding="utf-8"))


def _never_arrived_ticket() -> dict:
    """An official no-show ticket where the driver clearly never reached the pickup.

    gps_telemetry is present (and covers up to cancellation_time) but has no
    ``driver_arrived`` event and no telemetry point with status ``arrived``/
    ``waiting``; every telemetry point is ~1 km from the pickup.
    """
    return {
        "dispute_ticket": {
            "dispute_id": "DISP-099",
            "trip_id": "TRIP-099",
            "dispute_type": "no_show_charge",
            "description": "Driver never arrived.",
        },
        "rider_profile": {"rider_id": "R-9", "name": "Rider", "total_trips": 50, "account_age_days": 300},
        "driver_profile": {"driver_id": "D-9", "name": "Driver", "total_trips": 2000, "account_age_days": 500},
        "trip_data": {
            "pickup_location": {"lat": 1.2847, "lng": 103.8382},
            "dropoff_location": {"lat": 1.2648, "lng": 103.8223},
            "scheduled_time": "2026-09-13T08:45:00+08:00",
            "cancellation_time": "2026-09-13T08:51:00+08:00",
            "cancellation_fee": 5.0,
            "cancellation_reason": "rider_no_show",
        },
        "gps_telemetry": [
            {"timestamp": "2026-09-13T08:31:00+08:00", "lat": 1.2920, "lng": 103.8450, "status": "en_route"},
            {"timestamp": "2026-09-13T08:40:00+08:00", "lat": 1.2905, "lng": 103.8460, "status": "en_route"},
            {"timestamp": "2026-09-13T08:51:00+08:00", "lat": 1.2910, "lng": 103.8465, "status": "cancelled"},
        ],
        "app_events": [
            {"timestamp": "2026-09-13T08:30:00+08:00", "event_type": "driver_en_route", "details": "..."},
        ],
        "chat_logs": [],
        "cancellation_policy": {"free_wait_time_min": 5},
    }


# --------------------------------------------------------------------------- #
# Fix 1 — null money fields become evidence gaps (never a silent 0.0)
# --------------------------------------------------------------------------- #


def test_null_base_fare_on_route_deviation_escalates(disputes, policies, config):
    case = copy.deepcopy(next(d for d in disputes if d["case_id"] == "RYDE-2026-0001"))
    case["fare"]["base_fare"] = None
    decision = apply_policy(analyze_evidence(case), policies, config)
    assert decision.action == INSUFFICIENT_EVIDENCE
    assert decision.escalate is True
    assert "fare.base_fare" in decision.missing_fields


def test_null_cancellation_fee_on_no_show_escalates(disputes, policies, config):
    case = copy.deepcopy(next(d for d in disputes if d["case_id"] == "RYDE-2026-0002"))
    case["fare"]["cancellation_fee"] = None
    decision = apply_policy(analyze_evidence(case), policies, config)
    assert decision.action == INSUFFICIENT_EVIDENCE
    assert decision.escalate is True
    assert "fare.cancellation_fee" in decision.missing_fields


def test_null_distance_fare_on_route_deviation_escalates(policies, config):
    dispute = {
        "category": "route_deviation",
        "trip": {"optimal_distance_km": 10.0, "actual_distance_km": 12.0},
        "fare": {
            "base_fare": 3.0,
            "distance_fare_actual": None,
            "distance_fare_optimal": 8.0,
            "surge_multiplier": 1.0,
        },
        "gps": {},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }
    decision = apply_policy(analyze_evidence(dispute), policies, config)
    assert decision.action == INSUFFICIENT_EVIDENCE
    assert "fare.distance_fare_actual" in decision.missing_fields


def test_genuine_zero_money_field_is_valid(policies, config):
    dispute = {
        "category": "no_show",
        "trip": {},
        "gps": {"driver_arrival": {"closest_distance_to_pickup_m": 45, "wait_time_min": 6, "late_min": 1}},
        "fare": {"cancellation_fee": 0.0},
        "chat_log": [{"from": "driver", "text": "I'm at the pickup point."}],
        "rider": {},
        "driver": {},
    }
    evidence = analyze_evidence(dispute)
    assert "fare.cancellation_fee" not in evidence.gaps
    decision = apply_policy(evidence, policies, config)
    assert decision.action == NO_ACTION


def test_official_null_cancellation_fee_not_invented():
    ticket = _load_official()
    ticket["trip_data"]["cancellation_fee"] = None
    normalized = normalize_official_ticket(ticket)
    assert normalized["fare"].get("cancellation_fee") is None
    # base_fare must not be hard-coded to 0.0 by the adapter.
    assert "base_fare" not in normalized["fare"]


def test_official_null_cancellation_fee_unneeded_for_no_action(client):
    ticket = _load_official()
    ticket["trip_data"]["cancellation_fee"] = None
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 200
    ruling = r.json()["ruling"]
    # WB01 uses decisive fields per branch: upholding a fee needs no refund amount.
    assert ruling["action"] == NO_ACTION
    assert ruling["escalated"] is False


# --------------------------------------------------------------------------- #
# Fix 2 — "driver never arrived" resolves to full_refund (NS-001.2)
# --------------------------------------------------------------------------- #


def test_never_arrived_derives_false_with_distance():
    normalized = normalize_official_ticket(_never_arrived_ticket())
    arrival = normalized["gps"]["driver_arrival"]
    assert arrival["arrived"] is False
    assert arrival["closest_distance_to_pickup_m"] > 150


def test_never_arrived_full_refund(client):
    r = client.post("/api/resolve", json=_never_arrived_ticket())
    assert r.status_code == 200
    ruling = r.json()["ruling"]
    assert ruling["action"] == FULL_REFUND
    assert ruling["escalated"] is False
    assert ruling["amount"] == 5.0
    assert "NS-001.2" in ruling["matched_policy_ids"]


def test_arrived_within_150m_derives_true():
    ticket = _never_arrived_ticket()
    ticket["gps_telemetry"][1] = {
        "timestamp": "2026-09-13T08:40:00+08:00",
        "lat": 1.2847,
        "lng": 103.8382,
        "status": "en_route",
    }
    normalized = normalize_official_ticket(ticket)
    assert normalized["gps"]["driver_arrival"]["arrived"] is True


def test_no_telemetry_no_events_arrival_unknown_escalates(client):
    ticket = _never_arrived_ticket()
    ticket["gps_telemetry"] = []
    ticket["app_events"] = []
    r = client.post("/api/resolve", json=ticket)
    ruling = r.json()["ruling"]
    assert ruling["action"] == INSUFFICIENT_EVIDENCE
    assert ruling["escalated"] is True


# --------------------------------------------------------------------------- #
# Fix 3 — single arrival time, conflict check, missing scheduled_time
# --------------------------------------------------------------------------- #


def test_arrival_time_conflict_escalates(client):
    ticket = _load_official()
    # trip_data.driver_arrival_time (08:35) vs app_events driver_arrived (08:43)
    # differ by 8 minutes -> conflict -> escalate.
    ticket["trip_data"]["driver_arrival_time"] = "2026-09-13T08:35:00+08:00"
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 200
    body = r.json()
    assert body["ruling"]["escalated"] is True
    assert any("conflicting arrival" in gap for gap in body["evidence"]["gaps"])


def test_missing_scheduled_time_lateness_unknown_escalates(client):
    ticket = _load_official()
    ticket["trip_data"].pop("scheduled_time")
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 200
    body = r.json()
    assert body["evidence"]["driver_late_min"] is None
    assert body["ruling"]["escalated"] is True
