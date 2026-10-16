"""Deterministic policy engine.

Applies Ryde's company policy to structured evidence and produces a ruling
recommendation. The Judge Agent treats this as a strong prior, while still
producing its own natural-language reasoning (and optionally deferring to the
LLM for the final narrative).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
import math
from typing import Any, Optional

from .evidence import EvidenceAnalysis

# Ruling actions.
NO_ACTION = "no_action"
PARTIAL_REFUND = "partial_refund"
FULL_REFUND = "full_refund"
COMPENSATION = "compensation"
ESCALATE = "escalate"
INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class PolicyDecision:
    action: str
    amount: float
    confidence: float
    currency: str = "SGD"
    matched_policy_ids: list[str] = field(default_factory=list)
    explanation: str = ""
    escalate: bool = False
    missing_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PolicyEngine:
    def __init__(self, policies: list[dict], config: Optional[dict] = None):
        self.policies = policies
        self.config = config or {}

    def decide(self, evidence: EvidenceAnalysis) -> PolicyDecision:
        # Missing critical evidence must never produce a refund by default (bug #3).
        if evidence.gaps:
            return PolicyDecision(
                action=INSUFFICIENT_EVIDENCE,
                amount=0.0,
                confidence=0.0,
                matched_policy_ids=[],
                explanation="Insufficient evidence — missing: " + ", ".join(evidence.gaps),
                escalate=True,
                missing_fields=list(evidence.gaps),
            )

        if evidence.category == "route_deviation":
            return self._decide_route_deviation(evidence)
        if evidence.category == "no_show":
            return self._decide_no_show(evidence)
        if evidence.category == "safety_incident":
            return PolicyDecision(
                action=ESCALATE,
                amount=0.0,
                confidence=1.0,
                matched_policy_ids=["POL-SF-001"],
                explanation="Safety incidents are escalated to human review by policy.",
                escalate=True,
            )
        # property_damage / unknown → escalate by default.
        return PolicyDecision(
            action=ESCALATE,
            amount=0.0,
            confidence=0.5,
            matched_policy_ids=[],
            explanation=(
                f"Dispute category '{evidence.category}' is not supported by automated "
                "resolution; escalated for human review."
            ),
            escalate=True,
        )

    def _decide_route_deviation(self, e: EvidenceAnalysis) -> PolicyDecision:
        ratio = e.deviation_ratio  # already rounded to 4 decimals (or None if gapped)
        ids = ["POL-RD-001"]
        traffic_tolerance = float(self.config.get("traffic_tolerance", 0.30))

        if ratio is None:
            # Defensive: should have been caught by the gaps check, but never crash.
            return PolicyDecision(
                action=INSUFFICIENT_EVIDENCE,
                amount=0.0,
                confidence=0.0,
                matched_policy_ids=ids,
                explanation="Route deviation ratio unavailable; insufficient evidence.",
                escalate=True,
                missing_fields=["trip.optimal_distance_km", "trip.actual_distance_km"],
            )

        # Bug #5: traffic does NOT blindly void a refund.
        if e.traffic_detected:
            if e.has_unexpected_stop:
                return self._route_refund(
                    e, include_base=True,
                    confidence=0.93,
                    matched_policy_ids=ids + ["RD-001.4", "RD-001.6"],
                    explanation=(
                        f"Traffic detour present, but an unexplained {e.unexpected_stop_min:.0f}-min stop "
                        "still triggers the stop clause of RD-001.4."
                    ),
                )
            if ratio > traffic_tolerance:
                return PolicyDecision(
                    action=ESCALATE,
                    amount=0.0,
                    confidence=0.5,
                    matched_policy_ids=ids + ["RD-001.5"],
                    explanation=(
                        f"Conflicting evidence: traffic detour claimed, but deviation "
                        f"{ratio * 100:.0f}% exceeds the {traffic_tolerance * 100:.0f}% tolerance."
                    ),
                    escalate=True,
                )
            return PolicyDecision(
                action=NO_ACTION,
                amount=0.0,
                confidence=0.9,
                matched_policy_ids=ids + ["RD-001.5"],
                explanation=(
                    f"Detour justified by live traffic within the {traffic_tolerance * 100:.0f}% tolerance; no refund."
                ),
            )

        if ratio < 0.05:
            return PolicyDecision(
                action=NO_ACTION,
                amount=0.0,
                confidence=0.95,
                matched_policy_ids=ids + ["RD-001.2"],
                explanation="Deviation below 5% tolerance; no refund.",
            )

        if ratio >= 0.15 or e.has_unexpected_stop:
            return self._route_refund(
                e, include_base=True,
                confidence=0.93,
                matched_policy_ids=ids + ["RD-001.4", "RD-001.6"],
                explanation=(
                    f"Deviation of {ratio * 100:.0f}%"
                    + (f" plus a {e.unexpected_stop_min:.0f}-min unexplained stop" if e.has_unexpected_stop else "")
                    + " exceeds policy; refunding excess distance fare and 50% base fare."
                ),
            )

        # 5%–15%
        return self._route_refund(
            e, include_base=False,
            confidence=0.88,
            matched_policy_ids=ids + ["RD-001.3", "RD-001.6"],
            explanation="Deviation between 5% and 15% without justification; refunding excess distance fare.",
        )

    @staticmethod
    def _missing_money(fields: list[str], ids: list[str]) -> PolicyDecision:
        return PolicyDecision(
            action=INSUFFICIENT_EVIDENCE, amount=0.0, confidence=0.0,
            matched_policy_ids=ids, escalate=True, missing_fields=fields,
            explanation="Insufficient evidence — missing: " + ", ".join(fields),
        )

    def _route_refund(
        self, e: EvidenceAnalysis, *, include_base: bool, confidence: float,
        matched_policy_ids: list[str], explanation: str,
    ) -> PolicyDecision:
        missing = list(e.missing_fares)
        if e.excess_distance_fare is None and not missing:
            missing.extend(["fare.distance_fare_actual", "fare.distance_fare_optimal"])
        if include_base and e.base_fare is None:
            missing.append("fare.base_fare")
        if missing:
            return self._missing_money(missing, matched_policy_ids)
        amount = e.excess_distance_fare + e.surge_refund
        if include_base:
            amount += 0.5 * e.base_fare
        if not math.isfinite(amount):
            return PolicyDecision(
                action=INSUFFICIENT_EVIDENCE, amount=0.0, confidence=0.0,
                matched_policy_ids=matched_policy_ids, escalate=True,
                explanation="Fare inputs overflow the refund calculation; human review required.",
                missing_fields=["fare (refund calculation overflow)"],
            )
        return PolicyDecision(
            action=PARTIAL_REFUND, amount=round(amount, 2), confidence=confidence,
            matched_policy_ids=matched_policy_ids, explanation=explanation,
        )

    def _decide_no_show(self, e: EvidenceAnalysis) -> PolicyDecision:
        ids = ["POL-NS-001"]
        arrived = e.driver_arrived
        wait = e.driver_wait_min
        late = e.driver_late_min
        # Per-ticket free-wait threshold overrides the global default (5 min)
        # for this case only; the global config is never mutated.
        free_wait = e.free_wait_min if e.free_wait_min is not None else 5.0

        if arrived is None or (arrived and (wait is None or (late is None and wait >= free_wait))):
            # Defensive: should have been caught by the gaps check, but never crash.
            return PolicyDecision(
                action=INSUFFICIENT_EVIDENCE,
                amount=0.0,
                confidence=0.0,
                matched_policy_ids=ids,
                explanation="Insufficient evidence to decide no-show; missing arrival, wait or lateness data.",
                escalate=True,
                missing_fields=list(e.gaps) or ['gps.driver_arrival.late_min'],
            )

        if (not arrived or (late is not None and late > 10) or wait < free_wait) and e.cancellation_fee is None:
            return self._missing_money(["fare.cancellation_fee"], ids)

        if not arrived:
            return PolicyDecision(
                action=FULL_REFUND,
                amount=e.cancellation_fee,
                confidence=0.95,
                matched_policy_ids=ids + ["NS-001.2"],
                explanation="Driver never arrived within 150 m of pickup; cancellation fee fully refunded.",
            )

        if late is not None and late > 10:
            return PolicyDecision(
                action=FULL_REFUND,
                amount=e.cancellation_fee,
                confidence=0.9,
                matched_policy_ids=ids + ["NS-001.3"],
                explanation="Driver arrived more than 10 minutes late; fee waived.",
            )

        if wait < free_wait:
            return PolicyDecision(
                action=FULL_REFUND,
                amount=e.cancellation_fee,
                confidence=0.88,
                matched_policy_ids=ids + ["NS-001.4"],
                explanation=(
                    f"Driver waited less than {free_wait:.0f} minutes before cancelling; fee refunded."
                ),
            )

        # Bug #4: NS-001.5 requires documented driver contact attempts.
        if e.driver_contact_attempts == 0:
            return PolicyDecision(
                action=ESCALATE,
                amount=0.0,
                confidence=0.5,
                matched_policy_ids=ids + ["NS-001.5"],
                explanation="No-show fee cannot be upheld: contact attempts not documented.",
                escalate=True,
            )

        # Arrived on time, waited >= 5 min, and documented contact attempts.
        return PolicyDecision(
            action=NO_ACTION,
            amount=0.0,
            confidence=0.92,
            matched_policy_ids=ids + ["NS-001.5"],
            explanation=f"Driver arrived within the permitted lateness and waited at least {free_wait:g} minutes; no-show fee upheld.",
        )


def apply_policy(evidence: EvidenceAnalysis, policies: list[dict], config: Optional[dict] = None) -> PolicyDecision:
    decision = PolicyEngine(policies, config).decide(evidence)
    available = {p['id'] for p in policies if p.get('category') == evidence.category}
    available.update(c['id'] for p in policies if p.get('category') == evidence.category
                     for c in p.get('clauses', []) if c.get('text'))
    if not set(decision.matched_policy_ids).issubset(available):
        return PolicyDecision(action=ESCALATE, amount=0.0, confidence=0.0, escalate=True,
                              explanation='Applicable policy is unavailable; human review required.')
    return decision
