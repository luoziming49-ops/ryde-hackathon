"""S1 robustness tests: typed models, gaps, stop-disclosure, confidence null."""

from __future__ import annotations

import pytest

from backend.agents.judge import JudgeAgent
from backend.core.evidence import _is_stop_disclosure, analyze_evidence
from backend.core.policy import INSUFFICIENT_EVIDENCE, apply_policy


def _base_inline() -> dict:
    return {
        "category": "route_deviation",
        "rider": {
            "claim": "I was overcharged.",
            "dispute_history": 0,
            "trips_completed": 50,
            "account_age_days": 200,
            "avg_rating": 4.5,
        },
        "driver": {
            "response": "The fare is correct.",
            "dispute_history": 1,
            "trips_completed": 1000,
            "account_age_days": 500,
            "avg_rating": 4.7,
        },
        "trip": {
            "optimal_distance_km": 10.0,
            "actual_distance_km": 12.0,
            "traffic_detected": False,
            "unexpected_stops": [],
            "estimated_duration_min": 20,
            "actual_duration_min": 24,
        },
        "fare": {
            "base_fare": 3.0,
            "distance_fare_actual": 10.0,
            "distance_fare_optimal": 8.0,
            "surge_multiplier": 1.0,
            "total_charged": 15.0,
            "optimal_total_estimate": 12.0,
            "cancellation_fee": 0,
        },
        "chat_log": [],
    }


# --- Fuzz every field listed in S1 PART A -----------------------------------


def _mut_dwell_min_string(body):
    body["trip"]["unexpected_stops"] = [{"dwell_min": "six"}]


def _mut_base_fare_numeric_string(body):
    body["fare"]["base_fare"] = "3.00"


def _mut_base_fare_null(body):
    body["fare"]["base_fare"] = None


def _mut_cancellation_fee_null(body):
    body["fare"]["cancellation_fee"] = None


def _mut_chat_log_strings(body):
    body["chat_log"] = ["hello", "world"]


def _mut_dispute_history_string(body):
    body["rider"]["dispute_history"] = "many"


def _mut_trips_completed_null(body):
    body["rider"]["trips_completed"] = None


def _mut_claim_null(body):
    body["rider"]["claim"] = None


@pytest.mark.parametrize(
    "mutator,expected_status",
    [
        (_mut_dwell_min_string, 422),          # "six" -> non-numeric -> 422
        (_mut_base_fare_numeric_string, 200),  # "3.00" -> coerced -> 200
        (_mut_base_fare_null, 200),            # null -> 200 (no crash)
        (_mut_cancellation_fee_null, 200),     # null -> 200 (no crash)
        (_mut_chat_log_strings, 422),          # list of strings -> 422
        (_mut_dispute_history_string, 422),    # "many" -> non-numeric -> 422
        (_mut_trips_completed_null, 200),      # null -> 200 (no crash)
        (_mut_claim_null, 200),                # null -> 200 (no crash)
    ],
)
def test_inline_fuzz(client, mutator, expected_status):
    body = _base_inline()
    mutator(body)
    r = client.post("/api/resolve", json=body)
    assert r.status_code == expected_status
    if expected_status == 200:
        assert "ruling" in r.json()


def test_inline_extra_keys_allowed(client):
    body = _base_inline()
    body["totally_unknown_field"] = {"anything": 123}
    r = client.post("/api/resolve", json=body)
    assert r.status_code == 200


# --- Negative distance / non-numeric surge become gaps ----------------------


def _route(actual, surge=1.0):
    return {
        "category": "route_deviation",
        "trip": {
            "optimal_distance_km": 10.0,
            "actual_distance_km": actual,
            "traffic_detected": False,
            "unexpected_stops": [],
        },
        "fare": {
            "base_fare": 3.0,
            "distance_fare_actual": 10.0,
            "distance_fare_optimal": 8.0,
            "surge_multiplier": surge,
        },
        "gps": {},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }


def test_negative_actual_distance_is_gap():
    result = analyze_evidence(_route(-5.0))
    assert "trip.actual_distance_km" in result.gaps
    assert result.deviation_ratio is None


def test_negative_distance_escalates(policies, config):
    decision = apply_policy(analyze_evidence(_route(-5.0)), policies, config)
    assert decision.action == INSUFFICIENT_EVIDENCE
    assert decision.escalate is True


def test_non_numeric_surge_is_gap():
    result = analyze_evidence(_route(12.0, surge="high"))
    assert "fare.surge_multiplier" in result.gaps


def test_non_numeric_surge_escalates(policies, config):
    decision = apply_policy(analyze_evidence(_route(12.0, surge="high")), policies, config)
    assert decision.action == INSUFFICIENT_EVIDENCE
    assert decision.escalate is True


# --- Stop-disclosure word-boundary matching ---------------------------------


def test_rest_assured_is_not_stop_disclosure():
    assert _is_stop_disclosure("Rest assured, the fare is correct.") is False


def test_bus_stop_is_not_stop_disclosure():
    assert _is_stop_disclosure("I'll meet you at the bus stop.") is False


def test_quick_break_is_stop_disclosure():
    assert _is_stop_disclosure("Quick break, sorry.") is True


def test_need_to_stop_is_stop_disclosure():
    assert _is_stop_disclosure("I need to stop for a moment.") is True


# --- Insufficient evidence: confidence null, nudge skipped ------------------


def test_insufficient_evidence_confidence_is_null(client):
    r = client.post(
        "/api/resolve",
        json={"category": "route_deviation", "rider": {"claim": "x"}, "driver": {"response": "y"}},
    )
    assert r.status_code == 200
    ruling = r.json()["ruling"]
    assert ruling["action"] == "insufficient_evidence"
    assert ruling["escalated"] is True
    assert ruling["confidence"] is None
    assert ruling["missing_fields"]


def test_precedent_nudge_skipped_when_escalated(policies, config):
    dispute = {
        "category": "route_deviation",
        "trip": {
            "optimal_distance_km": 100.0,
            "actual_distance_km": 145.0,
            "traffic_detected": True,
            "unexpected_stops": [],
        },
        "fare": {
            "base_fare": 3.0,
            "distance_fare_actual": 10.0,
            "distance_fare_optimal": 8.0,
            "surge_multiplier": 1.0,
        },
        "gps": {},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }
    evidence = analyze_evidence(dispute)
    judge = JudgeAgent(policies, config)
    ruling = judge.rule(
        dispute,
        evidence,
        {"argument": "rider"},
        {"argument": "driver"},
        fraud=None,
        precedent={"precedents": [{"id": "PRC-RD-201", "category": "route_deviation"}]},
    )
    assert ruling["escalated"] is True
    assert ruling["action"] == "escalate"
    assert ruling["confidence"] == 0.5  # no +0.03 precedent nudge


# --- RYDE-2026-0001 driver advocate must not claim proactive disclosure -----


def test_ryde_0001_driver_advocate_has_no_proactive_disclosure(client):
    r = client.post("/api/resolve", json={"case_id": "RYDE-2026-0001"})
    assert r.status_code == 200
    points = " ".join(r.json()["driver_case"]["points"])
    assert "proactively disclosed" not in points
