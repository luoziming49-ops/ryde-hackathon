"""Missing money must not become a confident zero-value refund."""

from copy import deepcopy

import pytest


def inline(sample_case, case_id):
    body = deepcopy(sample_case(case_id))
    body.pop("case_id")
    return body


@pytest.mark.parametrize("field", ["base_fare", "distance_fare_actual", "distance_fare_optimal"])
@pytest.mark.parametrize("missing", ["absent", "null"])
def test_route_refund_missing_fare_escalates(client, sample_case, field, missing):
    body = inline(sample_case, "RYDE-2026-0001")
    if missing == "absent":
        body["fare"].pop(field)
    else:
        body["fare"][field] = None
    result = client.post("/api/resolve", json=body).json()
    ruling = result["ruling"]
    assert ruling["action"] == "insufficient_evidence"
    assert ruling["escalated"] is True
    assert ruling["amount"] is None
    assert ruling["confidence"] is None
    assert "fare." + field in ruling["missing_fields"]


def test_no_show_refund_missing_fee_escalates(client, sample_case):
    body = inline(sample_case, "RYDE-2026-0002")
    body["fare"].pop("cancellation_fee")
    result = client.post("/api/resolve", json=body).json()
    assert result["ruling"]["action"] == "insufficient_evidence"
    assert result["ruling"]["amount"] is None
    assert result["ruling"]["confidence"] is None
    assert result["ruling"]["missing_fields"] == ["fare.cancellation_fee"]
    assert result["evidence"]["cancellation_fee"] is None
    assert not any("SGD 0.00 cancellation fee" in p for p in result["rider_case"]["points"])


@pytest.mark.parametrize("case_id,action", [("RYDE-2026-0001", "partial_refund"), ("RYDE-2026-0002", "full_refund")])
def test_explicit_zero_money_is_not_missing(client, sample_case, case_id, action):
    body = inline(sample_case, case_id)
    for field in ["base_fare", "distance_fare_actual", "distance_fare_optimal", "cancellation_fee"]:
        body["fare"][field] = 0
    ruling = client.post("/api/resolve", json=body).json()["ruling"]
    assert ruling["action"] == action
    assert ruling["amount"] == 0.0
    assert ruling["escalated"] is False


def test_no_action_does_not_require_unrelated_fares(client, sample_case):
    body = inline(sample_case, "RYDE-2026-0003")
    body["fare"] = {}
    ruling = client.post("/api/resolve", json=body).json()["ruling"]
    assert ruling["action"] == "no_action"
    assert ruling["escalated"] is False


def test_lower_route_refund_does_not_require_base_fare(client, sample_case):
    body = inline(sample_case, "RYDE-2026-0001")
    body["trip"].update(optimal_distance_km=100, actual_distance_km=110, unexpected_stops=[], traffic_detected=False)
    body["fare"] = {"distance_fare_actual": 10, "distance_fare_optimal": 8, "surge_multiplier": 1}
    ruling = client.post("/api/resolve", json=body).json()["ruling"]
    assert ruling["action"] == "partial_refund"
    assert ruling["amount"] == 2.0


def test_arrived_false_without_distance_no_500(client, sample_case):
    body = inline(sample_case, "RYDE-2026-0002")
    body["gps"]["driver_arrival"].pop("closest_distance_to_pickup_m")
    body["gps"]["driver_arrival"]["arrived"] = False
    response = client.post("/api/resolve", json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["ruling"]["action"] == "full_refund"
    assert result["ruling"]["amount"] == 5
    assert "unknown" in " ".join(result["evidence"]["notes"]).lower()
