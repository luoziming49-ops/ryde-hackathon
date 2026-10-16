"""Consumer-visible input failures, including both supported input formats."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def boundary_client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def official():
    return json.loads((Path(__file__).resolve().parents[1] / "sample_data/official/DISP-002.json").read_text())


@pytest.mark.parametrize("field,bad", [
    ("dispute_ticket", "broken"), ("dispute_ticket", []),
    ("trip_data", []), ("rider_profile", "broken"), ("driver_profile", 12),
    ("chat_logs", ["hello"]), ("app_events", [None]),
    ("gps_telemetry", {"status": "arrived"}), ("cancellation_policy", []),
])
def test_official_bad_nested_types_422(boundary_client, official, field, bad):
    official[field] = bad
    response = boundary_client.post("/api/resolve", json=official)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("value", [-5, "bad", "NaN", "Infinity", "-Infinity", True])
@pytest.mark.parametrize("format", ["internal", "official"])
def test_money_invalid_both_formats_422(boundary_client, official, sample_case, value, format):
    if format == "official":
        payload = official
        payload["trip_data"]["cancellation_fee"] = value
    else:
        payload = deepcopy(sample_case("RYDE-2026-0002"))
        payload.pop("case_id")
        payload["fare"]["cancellation_fee"] = value
    response = boundary_client.post("/api/resolve", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("field", ["base_fare", "distance_fare_actual", "distance_fare_optimal", "total_charged", "time_fare_actual"])
def test_other_negative_fares_rejected(boundary_client, sample_case, field):
    payload = deepcopy(sample_case("RYDE-2026-0001"))
    payload.pop("case_id")
    payload["fare"][field] = -1
    assert boundary_client.post("/api/resolve", json=payload).status_code == 422


def test_official_numeric_strings_and_raw_events_preserved(boundary_client, official):
    official["trip_data"]["cancellation_fee"] = "5.00"
    official["rider_profile"]["dispute_history"]["total_disputes"] = "4"
    official["cancellation_policy"]["free_wait_time_min"] = "5"
    response = boundary_client.post("/api/resolve", json=official)
    assert response.status_code == 200
    result = response.json()
    assert result["ruling"]["action"] == "no_action"
    assert result["raw_app_events"] == official["app_events"]


@pytest.mark.parametrize("field,value", [
    ("dispute_history", {"total_disputes": "many"}),
    ("dispute_history", {"rejected": "many", "total_disputes": 4}),
    ("total_trips", "Infinity"),
])
def test_official_profile_invalid_counts_422(boundary_client, official, field, value):
    official["rider_profile"][field] = value
    assert boundary_client.post("/api/resolve", json=official).status_code == 422


def test_official_loaded_samples_use_same_validation(monkeypatch, tmp_path, official):
    from backend.main import _load_official_disputes
    from pydantic import ValidationError
    official["trip_data"]["cancellation_fee"] = -5
    (tmp_path / "bad.json").write_text(json.dumps(official))
    monkeypatch.setattr("backend.main.OFFICIAL_DIR", tmp_path)
    with pytest.raises(ValidationError):
        _load_official_disputes()
