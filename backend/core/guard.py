"""Check reference/decision consistency, not the truth of external evidence."""

import hashlib
import json
import math

from ..contracts import AgentClaim, EvidenceItem, GuardResult, LLMResult
from .evidence import EvidenceAnalysis


def _fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode()).hexdigest()


def policy_version(policies: list[dict], config: dict, override: dict) -> str:
    return "policy-v1-" + _fingerprint([policies, config, override])[:16]


def build_policy_context(policies, config, dispute, evidence, decision) -> dict:
    """Expose the one deterministic decision's rules, including effective overrides."""
    matched = set(decision.matched_policy_ids)
    rules = []
    for policy in policies:
        if policy["id"] in matched:
            rules.append({"id": policy["id"], "text": policy.get("title", "")})
        rules.extend({"id": clause["id"], "text": clause["text"]}
                     for clause in policy.get("clauses", []) if clause["id"] in matched)
    return {"version": policy_version(policies, config, dispute.get("cancellation_policy_override") or {}),
            "matched_rules": rules,
            "effective_free_wait_min": (evidence.free_wait_min if evidence.free_wait_min is not None else 5.0)
                if evidence.category == "no_show" else None,
            "free_wait_source": "case_override" if evidence.free_wait_min is not None else "default_policy"}


def build_evidence_catalog(dispute: dict, evidence: EvidenceAnalysis, *, is_simulated=None) -> list[EvidenceItem]:
    version = _fingerprint(dispute)[:20]
    case_id = dispute.get("case_id") or "inline-" + version
    catalog = []

    def add(path, value, text, kind="derived", source="deterministic_analysis"):
        catalog.append(EvidenceItem(
            id="ev-" + _fingerprint([case_id, version, path])[:24], case_id=case_id,
            version=version, source=source, source_path=path, value=value, text=text,
            kind=kind, is_simulated=is_simulated,
        ))

    def number(path, value, label, suffix=""):
        if value is not None and (not isinstance(value, float) or math.isfinite(value)):
            add(path, value, f"{label}: {value:g}{suffix}.")

    add("analysis.category", evidence.category if evidence.category in ("route_deviation", "no_show") else "other",
        "Dispute evidence has been processed by the deterministic analysis engine.")
    if evidence.category == "route_deviation":
        number("analysis.deviation_ratio", None if evidence.deviation_ratio is None else evidence.deviation_ratio * 100,
               "Computed route deviation", "%")
        number("analysis.excess_distance_km", evidence.excess_distance_km, "Computed extra distance", " km")
        if evidence.has_unexpected_stop:
            add("trip.unexpected_stops", True, "An unexpected stop is recorded in the supplied trip data.")
        traffic = (dispute.get("trip") or {}).get("traffic_detected")
        if isinstance(traffic, bool):
            add("trip.traffic_detected", traffic, "Traffic is flagged in the supplied trip data." if traffic else
                "Traffic is not flagged in the supplied trip data.")
        number("analysis.excess_distance_fare", evidence.excess_distance_fare, "Computed excess distance fare")
    elif evidence.category == "no_show":
        if evidence.driver_arrived is not None and not dispute.get("normalization_gaps"):
            add("analysis.driver_arrived", evidence.driver_arrived,
                "Recorded arrival evidence indicates the driver arrived." if evidence.driver_arrived else
                "Recorded arrival evidence indicates the driver did not arrive.")
        number("analysis.driver_wait_min", evidence.driver_wait_min, "Computed driver wait", " minutes")
        arrival = (dispute.get("gps") or {}).get("driver_arrival") or {}
        if arrival.get("late_min") is not None:
            number("analysis.driver_late_min", evidence.driver_late_min, "Computed driver lateness", " minutes")
        number("analysis.driver_contact_attempts", evidence.driver_contact_attempts, "Recorded driver contact attempts")
        threshold = evidence.free_wait_min if evidence.free_wait_min is not None else 5.0
        path = "cancellation_policy_override.free_wait_time_min" if evidence.free_wait_min is not None else "policy.default_free_wait_min"
        number(path, threshold, "Effective free-wait threshold", " minutes")
    number("fare.cancellation_fee", evidence.cancellation_fee, "Recorded cancellation fee")
    number("fare.base_fare", evidence.base_fare, "Recorded base fare")
    for party in ("rider", "driver"):
        key = "claim" if party == "rider" else "response"
        value = (dispute.get(party) or {}).get(key)
        if value:
            # Keep long/private source text in the case file, not in model output.
            add(f"{party}.{key}", value, f"{party.title()} reports: {str(value)[:3000]}", "reported", "party_statement")
    return catalog


def validate_claim(data: dict, *, party: str, catalog: list[EvidenceItem], policy_ids: set[str],
                   missing_evidence: list[str], expected_action: str | None = None) -> dict:
    """policy_ids must come from the current deterministic policy decision."""
    result = AgentClaim.model_validate(data)
    if result.party != party or (expected_action is not None and result.proposed_action != expected_action):
        raise ValueError("invalid_action_or_party")
    if not set(result.missing_evidence).issubset(missing_evidence):
        raise ValueError("invalid_missing_evidence")
    index = {item.id: item for item in catalog}
    seen = set()
    for claim in result.claims:
        evidence_id = claim.evidence_ids[0]
        item = index.get(evidence_id)
        if item is None or item.text != claim.text or evidence_id in seen:
            raise ValueError("invalid_evidence_reference")
        if party == "judge" and item.kind != "derived":
            raise ValueError("reported_claim_is_not_a_computed_fact")
        if not set(claim.policy_ids).issubset(policy_ids):
            raise ValueError("invalid_policy_reference")
        seen.add(evidence_id)
    return result.model_dump()


def fallback_claim(party: str, catalog: list[EvidenceItem], policy_ids: set[str],
                   missing_evidence: list[str], action: str) -> dict:
    return {"party": party, "claims": [
        {"text": item.text, "evidence_ids": [item.id], "policy_ids": []}
        for item in catalog if item.kind == "derived"
    ][:8], "missing_evidence": list(dict.fromkeys(missing_evidence))[:64], "proposed_action": action}


def guard_result(result: LLMResult, ruling: dict, version: str) -> GuardResult:
    return GuardResult(
        status="rejected" if result.status in ("rejected", "error") else "approved",
        reasons=[result.error_code] if result.error_code else [],
        final_action=ruling["action"], final_amount=ruling["amount"], policy_version=version,
        evidence_ids=[claim["evidence_ids"][0] for claim in result.value["claims"]],
    )
