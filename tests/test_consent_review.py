"""Party reports cannot establish oral consent or explain a GPS stop."""

from copy import deepcopy

import pytest

from backend.core.evidence import analyze_evidence
from backend.core.guard import build_evidence_catalog, validate_claim


def route_body(sample_case, rider="unknown", driver="unknown", *, percent=20, stop=False, traffic=False):
    body = deepcopy(sample_case("RYDE-2026-0001"))
    body.pop("case_id")
    body["rider"]["route_consent"] = rider
    body["driver"]["route_consent"] = driver
    body["trip"].update(optimal_distance_km=100, actual_distance_km=100 + percent,
                        traffic_detected=traffic, unexpected_stops=[{"dwell_min": 6}] if stop else [])
    return body


@pytest.mark.parametrize("value", [True, None, "yes", {"verified": True}])
def test_invalid_consent_reports_rejected(client, sample_case, value):
    body = route_body(sample_case)
    body["rider"]["route_consent"] = value
    assert client.post("/api/resolve", json=body).status_code == 422


@pytest.mark.parametrize("rider,driver,state,value", [
    ("unknown", "unknown", "unconfirmed", None),
    ("agreed", "unknown", "unconfirmed", None),
    ("unknown", "not_agreed", "unconfirmed", None),
    ("agreed", "not_agreed", "conflicting", None),
    ("not_agreed", "agreed", "conflicting", None),
    ("agreed", "agreed", "consistent", "agreed"),
    ("not_agreed", "not_agreed", "consistent", "not_agreed"),
])
def test_only_structured_reports_determine_comparison(sample_case, rider, driver, state, value):
    body = route_body(sample_case, rider, driver)
    # Neither a driver's disclosure nor a free-text answer establishes a typed report.
    body["chat_log"] = [{"from": "driver", "text": "I need to stop"},
                        {"from": "rider", "text": "Yes, I agreed to everything"}]
    evidence = analyze_evidence(body)
    assert evidence.rider_route_consent == rider
    assert evidence.driver_route_consent == driver
    assert evidence.consent_report_state == state
    assert evidence.consent_consistent_value == value


def test_original_route_is_unconfirmed_and_requires_review(client, sample_case):
    original = deepcopy(sample_case("RYDE-2026-0001"))
    result = client.post("/api/resolve", json={"case_id": "RYDE-2026-0001"}).json()
    assert result["evidence"]["consent_report_state"] == "unconfirmed"
    ruling = result["ruling"]
    assert (ruling["action"], ruling["amount"], ruling["confidence"]) == ("insufficient_evidence", None, None)
    assert ruling["escalated"] is True
    assert ruling["review_questions"] and any("oral" in q.lower() for q in ruling["review_questions"])
    assert sample_case("RYDE-2026-0001") == original
    assert "unexplained stop" not in ruling["reasoning"].lower()


@pytest.mark.parametrize("rider,driver,percent,stop,traffic,action,amount", [
    ("unknown", "unknown", 4, False, None, "no_action", 0),
    ("agreed", "not_agreed", 4, False, None, "no_action", 0),
    ("unknown", "unknown", 10, False, False, "insufficient_evidence", None),
    ("agreed", "not_agreed", 20, False, False, "insufficient_evidence", None),
    ("agreed", "agreed", 20, False, None, "no_action", 0),
    ("agreed", "agreed", 20, True, False, "insufficient_evidence", None),
    ("not_agreed", "not_agreed", 10, False, False, "partial_refund", 6.37),
    ("not_agreed", "not_agreed", 20, True, False, "partial_refund", 7.87),
    ("not_agreed", "not_agreed", 10, True, False, "insufficient_evidence", None),
    ("not_agreed", "not_agreed", 4, True, False, "insufficient_evidence", None),
    ("not_agreed", "not_agreed", 10, False, None, "insufficient_evidence", None),
    ("unknown", "unknown", 20, False, True, "no_action", 0),
    ("unknown", "unknown", 10, True, True, "insufficient_evidence", None),
])
def test_only_decisive_uncertainty_blocks_amount(client, sample_case, rider, driver, percent, stop, traffic, action, amount):
    response = client.post("/api/resolve", json=route_body(sample_case, rider, driver, percent=percent, stop=stop, traffic=traffic))
    assert response.status_code == 200
    result = response.json()
    ruling = result["ruling"]
    assert (ruling["action"], ruling["amount"]) == (action, amount)
    assert isinstance(ruling["review_questions"], list)
    assert bool(ruling["review_questions"]) == (action == "insufficient_evidence")
    assert result["evidence"]["traffic_detected"] is traffic
    assert "live traffic" not in ruling["reasoning"].lower()


def test_no_show_objective_refund_does_not_need_chat_or_consent(client, sample_case):
    body = deepcopy(sample_case("RYDE-2026-0002"))
    body.pop("case_id")
    body["chat_log"] = []
    body["rider"]["route_consent"] = "agreed"
    body["driver"]["route_consent"] = "not_agreed"
    ruling = client.post("/api/resolve", json=body).json()["ruling"]
    assert (ruling["action"], ruling["amount"]) == ("full_refund", 5)
    assert ruling["review_questions"] == []


def test_consistent_reports_stay_reported_and_cannot_become_judge_facts(sample_case):
    body = route_body(sample_case, "agreed", "agreed")
    evidence = analyze_evidence(body)
    catalog = build_evidence_catalog(body, evidence)
    reports = [item for item in catalog if item.source_path.endswith("route_consent")]
    assert len(reports) == 2 and all(item.kind == "reported" for item in reports)
    assert all("reports" in item.text.lower() for item in reports)
    assert not any("consent is verified" in item.text.lower() for item in catalog)
    report = reports[0]
    draft = {"party": "judge", "claims": [{"text": report.text, "evidence_ids": [report.id], "policy_ids": []}],
             "missing_evidence": [], "proposed_action": "no_action"}
    with pytest.raises(ValueError, match="reported_claim"):
        validate_claim(draft, party="judge", catalog=catalog, policy_ids=set(), missing_evidence=[], expected_action="no_action")


def test_policy_explains_report_basis_without_external_verification(client, sample_case):
    result = client.post("/api/resolve", json=route_body(sample_case, "not_agreed", "not_agreed")).json()
    text = result["ruling"]["reasoning"].lower()
    assert "report" in text and "not independently verified" in text
    assert "RD-001.8" in result["ruling"]["matched_policy_ids"]


@pytest.mark.parametrize("rider,driver", [("agreed", "not_agreed"), ("unknown", "unknown")])
def test_official_profile_reports_survive_normalization(client, rider, driver):
    from backend.adapters.official_ticket import normalize_official_ticket
    ticket = {"dispute_ticket": {"dispute_id": "PROFILE-REPORTS", "dispute_type": "no_show_charge"},
              "rider_profile": {"route_consent": rider}, "driver_profile": {"route_consent": driver}}
    normalized = normalize_official_ticket(ticket)
    assert normalized["rider"]["route_consent"] == rider
    assert normalized["driver"]["route_consent"] == driver
    # Route reports cannot fill missing no-show evidence.
    response = client.post("/api/resolve", json=ticket)
    assert response.status_code == 200
    assert response.json()["ruling"]["action"] == "insufficient_evidence"


@pytest.mark.parametrize("party", ["rider_profile", "driver_profile"])
def test_official_profile_invalid_report_is_rejected(client, party):
    ticket = {"dispute_ticket": {"dispute_id": "PROFILE-REPORTS", "dispute_type": "no_show_charge"},
              party: {"route_consent": "verified"}}
    assert client.post("/api/resolve", json=ticket).status_code == 422


def test_missing_traffic_stays_unknown_instead_of_false(client, sample_case):
    body = route_body(sample_case, "not_agreed", "not_agreed")
    body["trip"].pop("traffic_detected")
    response = client.post("/api/resolve", json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["evidence"]["traffic_detected"] is None
    assert result["ruling"]["amount"] is None
    assert "trip.traffic_detected" in result["ruling"]["missing_fields"]
    assert any("traffic" in question.lower() for question in result["ruling"]["review_questions"])


@pytest.mark.parametrize("request_body,action", [
    ({"case_id": "RYDE-2026-0001"}, "insufficient_evidence"),
    ({"category": "safety_incident", "rider": {}, "driver": {}}, "escalate"),
])
def test_review_flag_api_does_not_claim_support_dispatch(client, request_body, action):
    response = client.post("/api/resolve", json=request_body)
    assert response.status_code == 200
    result = response.json()
    ruling = result["ruling"]
    assert ruling["action"] == action and ruling["escalated"] is True
    assert ruling["amount"] is None
    rule_trace = next(message["content"] for message in result["trace"]
                      if message["agent"] == "Judge" and message["role"] == "rule")
    for text in (ruling["reasoning"], rule_trace):
        assert "Flagged for human review" in text
        assert "No support case has been dispatched" in text
        assert "escalated to" not in text.lower() and "escalating to" not in text.lower()


def test_review_flag_run_event_does_not_claim_support_dispatch(client):
    response = client.post("/api/runs", json={"case_id": "RYDE-2026-0001"})
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    client.app.state.runs.wait(run_id, timeout=3)
    snapshot = client.get("/api/runs/" + run_id).json()
    assert snapshot["status"] == "completed"
    event = next(event for event in snapshot["events"]
                 if event["actor"] == "Judge" and event["kind"] == "rule")
    assert "Flagged for human review" in event["output_summary"]
    assert "No support case has been dispatched" in event["output_summary"]
