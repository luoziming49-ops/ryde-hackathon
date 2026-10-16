"""Regression cases discovered by independent WB01 review."""

from copy import deepcopy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def review_client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "1e309"])
def test_native_nonfinite_money_is_json_422(review_client, sample_case, value):
    body = deepcopy(sample_case("RYDE-2026-0002"))
    body.pop("case_id")
    body["fare"]["cancellation_fee"] = "NONFINITE"
    response = review_client.post("/api/resolve", content=json.dumps(body).replace('"NONFINITE"', value),
                                  headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("value", [-1, True, "NaN", "Infinity", "-Infinity"])
def test_invalid_surge_cannot_produce_ruling(review_client, sample_case, value):
    body = deepcopy(sample_case("RYDE-2026-0001"))
    body.pop("case_id")
    body["fare"]["surge_multiplier"] = value
    assert review_client.post("/api/resolve", json=body).status_code == 422


@pytest.mark.parametrize("base,distance,surge", [(1.7e308, 1.7e308, 1), (1, 1e308, 1e308)])
def test_refund_overflow_escalates(review_client, sample_case, base, distance, surge):
    body = deepcopy(sample_case("RYDE-2026-0001"))
    body.pop("case_id")
    body["fare"].update(base_fare=base, distance_fare_actual=distance,
                        distance_fare_optimal=0, surge_multiplier=surge)
    response = review_client.post("/api/resolve", json=body)
    assert response.status_code == 200
    ruling = response.json()["ruling"]
    assert ruling["action"] == "insufficient_evidence"
    assert ruling["escalated"] is True
    assert ruling["amount"] is None
    assert ruling["confidence"] is None


@pytest.mark.parametrize("status,timestamp", [
    ("cancelled", "2026-09-13T08:44:00+08:00"),
    ("waiting", "2026-09-13T08:52:00+08:00"),
])
def test_conflicting_telemetry_chronology_escalates(review_client, status, timestamp):
    body = json.loads((Path(__file__).resolve().parents[1] / "sample_data/official/DISP-002.json").read_text())
    next(row for row in body["gps_telemetry"] if row["status"] == status)["timestamp"] = timestamp
    response = review_client.post("/api/resolve", json=body)
    assert response.status_code == 200
    ruling = response.json()["ruling"]
    assert ruling["action"] == "insufficient_evidence"
    assert ruling["escalated"] is True
    assert ruling["amount"] is None


def test_later_waiting_observation_does_not_conflict_with_known_arrival(review_client):
    body = json.loads((Path(__file__).resolve().parents[1] / "sample_data/official/DISP-002.json").read_text())
    body["app_events"] = []
    body["gps_telemetry"] = [row for row in body["gps_telemetry"] if row["status"] != "arrived"]
    result = review_client.post("/api/resolve", json=body).json()
    assert result["ruling"]["action"] == "no_action"
    assert result["evidence"]["driver_wait_min"] == 8
