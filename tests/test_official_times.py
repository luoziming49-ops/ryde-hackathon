"""Arrival sources and time comparisons must not invent a valid wait."""

import json
from pathlib import Path

import pytest

from backend.adapters.official_ticket import normalize_official_ticket


@pytest.fixture
def ticket():
    return json.loads((Path(__file__).resolve().parents[1] / "sample_data/official/DISP-002.json").read_text())


@pytest.mark.parametrize("source", ["events", "telemetry"])
def test_official_wait_uses_event_arrival(client, ticket, source):
    ticket["trip_data"].pop("driver_wait_start")
    ticket["trip_data"].pop("driver_arrival_time")
    if source == "telemetry":
        ticket.pop("app_events")
    normalized = normalize_official_ticket(ticket)
    assert normalized["gps"]["driver_arrival"]["wait_time_min"] == 8.0
    ruling = client.post("/api/resolve", json=ticket).json()["ruling"]
    assert ruling["action"] == "no_action"
    assert ruling["escalated"] is False


def test_equivalent_timezones_are_same_instant(client, ticket):
    ticket["trip_data"]["driver_wait_start"] = "2026-09-13T00:43:00+00:00"
    ticket["trip_data"]["driver_arrival_time"] = "2026-09-13T00:43:00Z"
    result = client.post("/api/resolve", json=ticket).json()
    assert result["ruling"]["action"] == "no_action"
    assert result["evidence"]["driver_wait_min"] == 8


@pytest.mark.parametrize("field,value", [
    ("cancellation_time", "2026-09-13T08:40:00+08:00"),
    ("cancellation_time", "2026-09-13T08:51:00"),
    ("driver_wait_start", "2026-09-13T08:42:00+08:00"),
    ("driver_arrival_time", "2026-09-13T08:50:00+08:00"),
    ("driver_wait_start", "broken"),
    ("scheduled_time", "broken"),
])
def test_invalid_or_conflicting_times_escalate(client, ticket, field, value):
    ticket["trip_data"][field] = value
    response = client.post("/api/resolve", json=ticket)
    assert response.status_code == 200
    ruling = response.json()["ruling"]
    assert ruling["action"] == "insufficient_evidence"
    assert ruling["escalated"] is True
    assert ruling["amount"] is None
    assert ruling["confidence"] is None
    assert ruling["missing_fields"]


def test_later_wait_start_is_valid(client, ticket):
    ticket["trip_data"]["driver_wait_start"] = "2026-09-13T08:44:00+08:00"
    result = client.post("/api/resolve", json=ticket).json()
    assert result["evidence"]["driver_wait_min"] == 7
    assert result["ruling"]["action"] == "no_action"


def test_conflicting_arrival_events_escalate(client, ticket):
    ticket["app_events"].append({"event_type": "driver_arrived", "timestamp": "2026-09-13T08:49:00+08:00"})
    ruling = client.post("/api/resolve", json=ticket).json()["ruling"]
    assert ruling["action"] == "insufficient_evidence"


def test_internal_mixed_chat_timezones_do_not_crash(client, sample_case):
    from copy import deepcopy
    body = deepcopy(sample_case("RYDE-2026-0001"))
    body.pop("case_id")
    body["chat_log"] = [
        {"from": "driver", "text": "I need to stop", "ts": "2026-09-13T08:42:00"},
        {"from": "rider", "text": "Why stop?", "ts": "2026-09-13T08:43:00+08:00"},
    ]
    response = client.post("/api/resolve", json=body)
    assert response.status_code == 200
    assert response.json()["evidence"]["driver_disclosed_stop"] is False
