"""API tests (bugs #1, #9 + regression)."""

from __future__ import annotations


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "llm_configured" in body
    assert "state" in body


def test_list_disputes(client):
    r = client.get("/api/disputes")
    assert r.status_code == 200
    body = r.json()
    # 3 internal sample cases + 1 official sample.
    assert len(body) == 4
    by_id = {d["case_id"]: d for d in body}
    assert by_id["RYDE-2026-0001"]["source"] == "internal"
    assert by_id["DISP-002"]["source"] == "official"


def test_get_dispute(client):
    r = client.get("/api/disputes/RYDE-2026-0001")
    assert r.status_code == 200
    assert r.json()["case_id"] == "RYDE-2026-0001"


def test_unknown_dispute_404(client):
    r = client.post("/api/resolve", json={"case_id": "NOPE"})
    assert r.status_code == 404


# --- Bug #1: bad input must not 500 ---------------------------------------


def test_minimal_inline_dispute_does_not_crash(client):
    # No trip/fare/gps at all — must resolve to insufficient_evidence, not 500.
    r = client.post(
        "/api/resolve",
        json={"category": "route_deviation", "rider": {"claim": "x"}, "driver": {"response": "y"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ruling"]["action"] == "insufficient_evidence"
    assert body["ruling"]["escalated"] is True


def test_no_show_missing_gps_does_not_crash(client):
    # Missing gps.driver_arrival must resolve to insufficient_evidence, not 500.
    r = client.post(
        "/api/resolve",
        json={
            "category": "no_show",
            "rider": {"claim": "x"},
            "driver": {"response": "y"},
            "trip": {},
            "gps": {},
            "fare": {"cancellation_fee": 5.0},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ruling"]["action"] == "insufficient_evidence"
    assert body["ruling"]["escalated"] is True


def test_empty_body_422(client):
    r = client.post("/api/resolve", json={})
    assert r.status_code == 422


def test_missing_rider_driver_422(client):
    r = client.post("/api/resolve", json={"category": "route_deviation"})
    assert r.status_code == 422


def test_invalid_case_id_type_422(client):
    r = client.post("/api/resolve", json={"case_id": 123})
    assert r.status_code == 422


# --- Regression: three original cases through the API ----------------------


def test_api_resolve_case_0001(client):
    r = client.post("/api/resolve", json={"case_id": "RYDE-2026-0001"})
    assert r.status_code == 200
    ruling = r.json()["ruling"]
    assert ruling["action"] == "partial_refund"
    assert ruling["amount"] == 7.87


def test_api_resolve_case_0002(client):
    r = client.post("/api/resolve", json={"case_id": "RYDE-2026-0002"})
    ruling = r.json()["ruling"]
    assert ruling["action"] == "full_refund"
    assert ruling["amount"] == 5.00


def test_api_resolve_case_0003(client):
    r = client.post("/api/resolve", json={"case_id": "RYDE-2026-0003"})
    ruling = r.json()["ruling"]
    assert ruling["action"] == "no_action"
    assert ruling["amount"] == 0.0


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Ryde Dispute AI" in r.text
