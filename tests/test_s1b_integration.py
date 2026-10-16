"""GPS fallback must prove coverage and preserve unknowns and clock conflicts."""

import pytest

from backend.adapters.official_ticket import normalize_official_ticket
from backend.core.evidence import analyze_evidence
from backend.core.policy import apply_policy


@pytest.fixture
def gps_ticket():
    return {
        "dispute_ticket": {"dispute_id": "GPS-CASE", "dispute_type": "no_show_charge"},
        "trip_data": {
            "pickup_location": {"lat": 1.28, "lng": 103.83},
            "scheduled_time": "2026-09-13T08:45:00+08:00",
            "cancellation_time": "2026-09-13T08:51:00+08:00",
            "cancellation_fee": 5,
        },
        "gps_telemetry": [
            {"timestamp": "2026-09-13T08:40:00+08:00", "lat": 1.29, "lng": 103.84, "status": "en_route"},
            {"timestamp": "2026-09-13T08:51:00+08:00", "lat": 1.29, "lng": 103.84, "status": "cancelled"},
        ],
    }


def _decision(ticket, policies, config):
    return apply_policy(analyze_evidence(normalize_official_ticket(ticket)), policies, config)


def test_nonarrival_does_not_require_wait_or_schedule(gps_ticket, policies, config):
    gps_ticket["trip_data"].pop("scheduled_time")
    normalized = normalize_official_ticket(gps_ticket)
    assert normalized["gps"]["driver_arrival"]["arrived"] is False
    assert normalized["normalization_gaps"] == []
    decision = _decision(gps_ticket, policies, config)
    assert (decision.action, decision.amount, decision.escalate) == ("full_refund", 5, False)


def test_earliest_nearby_point_sets_wait_even_when_unsorted(gps_ticket):
    for point in gps_ticket["gps_telemetry"]:
        point.update(lat=1.28, lng=103.83)
    gps_ticket["gps_telemetry"].reverse()
    arrival = normalize_official_ticket(gps_ticket)["gps"]["driver_arrival"]
    assert arrival["arrived"] is True
    assert arrival["closest_distance_to_pickup_m"] == 0
    assert arrival["wait_time_min"] == 11
    assert arrival["late_min"] == 0


@pytest.mark.parametrize("value", [None, "bad", "2026-09-13T08:40:00"])
def test_invalid_or_mixed_point_clocks_stay_unknown(gps_ticket, policies, config, value):
    gps_ticket["gps_telemetry"][0]["timestamp"] = value
    normalized = normalize_official_ticket(gps_ticket)
    assert normalized["gps"]["driver_arrival"].get("arrived") is None
    assert any("gps_telemetry[0].timestamp" in gap for gap in normalized["normalization_gaps"])
    assert _decision(gps_ticket, policies, config).action == "insufficient_evidence"


@pytest.mark.parametrize("field,value", [("lat", None), ("lat", "bad"), ("lat", True), ("lat", 91), ("lng", -181), ("lat", float("inf")), ("lng", float("nan"))])
def test_invalid_coordinates_cannot_prove_nonarrival(gps_ticket, policies, config, field, value):
    gps_ticket["gps_telemetry"][0][field] = value
    normalized = normalize_official_ticket(gps_ticket)
    assert normalized["gps"]["driver_arrival"].get("arrived") is None
    assert any("gps_telemetry[0]" in gap for gap in normalized["normalization_gaps"])
    assert _decision(gps_ticket, policies, config).action == "insufficient_evidence"


@pytest.mark.parametrize("value", [None, "bad", "2026-09-13T08:51:00"])
def test_known_comparable_cancellation_required(gps_ticket, policies, config, value):
    gps_ticket["trip_data"]["cancellation_time"] = value
    assert _decision(gps_ticket, policies, config).action == "insufficient_evidence"


@pytest.mark.parametrize("which", ["pre_only", "post_only", "cancel_only", "post_nearby"])
def test_incomplete_coverage_does_not_prove_nonarrival(gps_ticket, policies, config, which):
    if which == "pre_only":
        gps_ticket["gps_telemetry"].pop()
    elif which == "cancel_only":
        gps_ticket["gps_telemetry"].pop(0)
    elif which == "post_only":
        gps_ticket["gps_telemetry"] = [{"timestamp": "2026-09-13T08:52:00+08:00", "lat": 1.28, "lng": 103.83}]
    else:
        gps_ticket["gps_telemetry"][-1].update(timestamp="2026-09-13T08:52:00+08:00", lat=1.28, lng=103.83)
    assert _decision(gps_ticket, policies, config).action == "insufficient_evidence"


def test_nonarrival_conflicting_with_supplied_arrival_escalates(gps_ticket, policies, config):
    gps_ticket["trip_data"]["driver_arrival_time"] = "2026-09-13T08:40:00+08:00"
    assert _decision(gps_ticket, policies, config).action == "insufficient_evidence"


def test_nearby_point_conflicting_with_supplied_arrival_escalates(gps_ticket, policies, config):
    gps_ticket["gps_telemetry"][0].update(lat=1.28, lng=103.83)
    gps_ticket["trip_data"]["driver_arrival_time"] = "2026-09-13T08:42:00+08:00"
    assert _decision(gps_ticket, policies, config).action == "insufficient_evidence"


def test_nonarrival_still_requires_refund_amount(gps_ticket, policies, config):
    gps_ticket["trip_data"].pop("cancellation_fee")
    decision = _decision(gps_ticket, policies, config)
    assert decision.action == "insufficient_evidence"
    assert "fare.cancellation_fee" in decision.missing_fields


@pytest.mark.parametrize("lat,expected", [(0.0013, True), (0.0014, False)])
def test_150m_boundary_and_zero_coordinates(gps_ticket, lat, expected):
    gps_ticket["trip_data"]["pickup_location"] = {"lat": 0, "lng": 0}
    for point in gps_ticket["gps_telemetry"]:
        point.update(lat=lat, lng=0)
    arrival = normalize_official_ticket(gps_ticket)["gps"]["driver_arrival"]
    assert arrival["arrived"] is expected


@pytest.mark.parametrize("pickup", [None, {}, {"lat": 1.28, "lng": float("inf")}, {"lat": False, "lng": 103.83}])
def test_invalid_pickup_prevents_distance_inference(gps_ticket, policies, config, pickup):
    gps_ticket["trip_data"]["pickup_location"] = pickup
    assert _decision(gps_ticket, policies, config).action == "insufficient_evidence"


def test_equivalent_utc_offsets_allow_gps_coverage(gps_ticket):
    gps_ticket["gps_telemetry"][0]["timestamp"] = "2026-09-13T00:40:00Z"
    assert normalize_official_ticket(gps_ticket)["gps"]["driver_arrival"]["arrived"] is False


def test_far_observations_bracket_cancellation(gps_ticket):
    gps_ticket["gps_telemetry"][-1]["timestamp"] = "2026-09-13T08:52:00+08:00"
    assert normalize_official_ticket(gps_ticket)["gps"]["driver_arrival"]["arrived"] is False


def test_cancelled_point_before_cancellation_is_conflict(gps_ticket, policies, config):
    gps_ticket["gps_telemetry"][0]["status"] = "cancelled"
    assert _decision(gps_ticket, policies, config).action == "insufficient_evidence"


def test_overflowing_coordinate_is_gap_instead_of_crash(gps_ticket):
    gps_ticket["gps_telemetry"][0]["lat"] = 10 ** 1000
    normalized = normalize_official_ticket(gps_ticket)
    assert normalized["gps"]["driver_arrival"].get("arrived") is None
    assert any("gps_telemetry[0]" in gap for gap in normalized["normalization_gaps"])

@pytest.mark.parametrize("explicit_arrival", [False, True])
@pytest.mark.parametrize("returns_to_pickup", [False, True])
def test_departure_during_claimed_wait_escalates(gps_ticket, policies, config, explicit_arrival, returns_to_pickup):
    gps_ticket["trip_data"]["scheduled_time"] = "2026-09-13T08:40:00+08:00"
    gps_ticket["gps_telemetry"][0].update(lat=1.28, lng=103.83)
    gps_ticket["gps_telemetry"].insert(1, {
        "timestamp": "2026-09-13T08:43:00+08:00", "lat": 1.29, "lng": 103.84,
    })
    gps_ticket["chat_logs"] = [{"sender": "driver", "content": "I have arrived."}]
    if explicit_arrival:
        gps_ticket["app_events"] = [{"event_type": "driver_arrived", "timestamp": "2026-09-13T08:40:00+08:00"}]
    if returns_to_pickup:
        gps_ticket["gps_telemetry"][-1].update(lat=1.28, lng=103.83)
    normalized = normalize_official_ticket(gps_ticket)
    assert normalized["gps"]["driver_arrival"].get("wait_time_min") is None
    assert any("departure" in gap for gap in normalized["normalization_gaps"])
    decision = _decision(gps_ticket, policies, config)
    assert decision.action == "insufficient_evidence"
    assert decision.escalate is True
