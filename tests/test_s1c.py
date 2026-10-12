"""S1c tests: last robustness gaps.

1. Malformed official tickets -> HTTP 422 (shape validation), not 500.
2. Invalid money (negative / NaN / Infinity) -> 422 in both formats;
   missing/null stays an evidence gap, explicit 0 stays valid.
3. & 4. Frontend fixes are exercised via the browser (not pytest).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_FILE = ROOT / "sample_data" / "official" / "DISP-002.json"


def _load_official() -> dict:
    return json.loads(OFFICIAL_FILE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Item 1 — malformed official tickets -> 422 (clear JSON), not 500
# --------------------------------------------------------------------------- #


def test_official_dispute_ticket_string_422(client):
    r = client.post("/api/resolve", json={"dispute_ticket": "broken"})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body
    # the message points at the offending field
    assert any("dispute_ticket" in str(e.get("loc", [])) for e in body["detail"])


def test_official_chat_logs_string_422(client):
    ticket = _load_official()
    ticket["chat_logs"] = "x"
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 422
    assert any("chat_logs" in str(e.get("loc", [])) for e in r.json()["detail"])


def test_official_chat_logs_list_of_strings_422(client):
    ticket = _load_official()
    ticket["chat_logs"] = ["hello", "world"]
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 422


def test_official_profile_not_object_422(client):
    ticket = _load_official()
    ticket["rider_profile"] = "x"
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 422
    assert any("rider_profile" in str(e.get("loc", [])) for e in r.json()["detail"])


def test_official_trip_data_not_object_422(client):
    ticket = _load_official()
    ticket["trip_data"] = ["not", "an", "object"]
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 422
    assert any("trip_data" in str(e.get("loc", [])) for e in r.json()["detail"])


def test_official_app_events_list_of_strings_422(client):
    ticket = _load_official()
    ticket["app_events"] = ["x"]
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 422


def test_official_valid_ticket_still_200(client):
    r = client.post("/api/resolve", json=_load_official())
    assert r.status_code == 200
    assert r.json()["ruling"]["action"] == "no_action"


# --------------------------------------------------------------------------- #
# Item 2 — invalid money values -> 422 (both formats)
# --------------------------------------------------------------------------- #


def test_official_negative_cancellation_fee_422(client):
    ticket = _load_official()
    ticket["trip_data"]["cancellation_fee"] = -5
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 422


def test_official_nan_cancellation_fee_422(client):
    ticket = _load_official()
    ticket["trip_data"]["cancellation_fee"] = "NaN"
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 422


def test_official_infinity_cancellation_fee_422(client):
    ticket = _load_official()
    ticket["trip_data"]["cancellation_fee"] = "Infinity"
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 422


def test_official_zero_cancellation_fee_valid(client):
    ticket = _load_official()
    ticket["trip_data"]["cancellation_fee"] = 0
    r = client.post("/api/resolve", json=ticket)
    assert r.status_code == 200
    # a genuine 0 is a valid value -> no evidence gap for it
    assert "fare.cancellation_fee" not in r.json()["evidence"]["gaps"]


def _inline_fare(**fare) -> dict:
    return {
        "category": "route_deviation",
        "rider": {"claim": "x"},
        "driver": {"response": "y"},
        "trip": {"optimal_distance_km": 10.0, "actual_distance_km": 12.0},
        "fare": fare,
        "chat_log": [],
    }


def test_inline_negative_money_422(client):
    r = client.post("/api/resolve", json=_inline_fare(base_fare=-3, distance_fare_actual=10, distance_fare_optimal=8))
    assert r.status_code == 422


def test_inline_nan_money_422(client):
    r = client.post("/api/resolve", json=_inline_fare(base_fare="NaN", distance_fare_actual=10, distance_fare_optimal=8))
    assert r.status_code == 422


def test_inline_infinity_money_422(client):
    r = client.post("/api/resolve", json=_inline_fare(base_fare="Infinity", distance_fare_actual=10, distance_fare_optimal=8))
    assert r.status_code == 422


def test_inline_zero_money_valid(client):
    r = client.post("/api/resolve", json=_inline_fare(base_fare=0, distance_fare_actual=10, distance_fare_optimal=8))
    assert r.status_code == 200
    assert r.json()["ruling"]["action"] in ("partial_refund", "no_action")
