"""Rider & Driver Advocate Agents.

Each advocate is intentionally *adversarial*: it gathers evidence from its own
party's perspective, cites the policy clauses that favour its side, and argues
for its preferred outcome. The Judge then arbitrates between the two.
"""

from __future__ import annotations

from typing import Any

from ..core.evidence import EvidenceAnalysis
from ..core.policy import PolicyDecision
from .base import BaseAgent, format_money, bulletize


class AdvocateAgent(BaseAgent):
    """Shared adversarial-case builder for one party."""

    party: str = "rider"  # 'rider' | 'driver'
    opponent: str = "driver"

    def __init__(self, policies: list[dict], **kwargs):
        super().__init__(**kwargs)
        self.policies = policies

    # ------------------------------------------------------------------ #
    def build_case(self, dispute: dict, evidence: EvidenceAnalysis) -> dict[str, Any]:
        points = self._gather_points(dispute, evidence)
        desired = self._desired_outcome(dispute, evidence)
        policy_citations = self._policy_citations(evidence)

        self.emit("gather", f"Collecting {self.party}-side evidence across GPS, chat, fare and history.")
        for p in points:
            self.emit("evidence", p)

        argument = self._write_argument(dispute, evidence, points, desired)
        self.emit("argue", argument, desired_outcome=desired, policy_citations=policy_citations)

        return {
            "party": self.party,
            "desired_outcome": desired,
            "points": points,
            "policy_citations": policy_citations,
            "argument": argument,
        }

    # ------------------------------------------------------------------ #
    def _gather_points(self, dispute: dict, e: EvidenceAnalysis) -> list[str]:
        raise NotImplementedError

    def _desired_outcome(self, dispute: dict, e: EvidenceAnalysis) -> str:
        raise NotImplementedError

    def _policy_citations(self, e: EvidenceAnalysis) -> list[str]:
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    def _write_argument(self, dispute, e, points, desired) -> str:
        system = (
            f"You are the {self.party.title()} Advocate in a ride-hailing dispute. "
            "Argue persuasively but factually for your party, citing policy. "
            "Do not fabricate facts beyond the evidence provided."
        )
        user = (
            f"Party: {self.party}\n"
            f"Category: {dispute.get('category')}\n"
            f"Claim/response: {dispute.get(self.party, {}).get('claim') or dispute.get(self.party, {}).get('response')}\n"
            f"Evidence points:\n{bulletize(points)}\n"
            f"Desired outcome: {desired}\n\n"
            "Write a concise 3-5 sentence closing argument."
        )
        fallback = self._fallback_argument(points, desired)
        return self.llm_or(system, user, fallback)

    @staticmethod
    def _fallback_argument(points: list[str], desired: str) -> str:
        summary = " ".join(points[:3])
        return (
            f"Based on the evidence, the {desired}. Key facts supporting this position: "
            f"{summary}."
        )


class RiderAdvocateAgent(AdvocateAgent):
    name = "Rider Advocate"
    description = "Represents the rider; argues for rider-favourable outcomes."
    party = "rider"
    opponent = "driver"

    def _gather_points(self, dispute: dict, e: EvidenceAnalysis) -> list[str]:
        rider = dispute.get("rider", {})
        trip = dispute.get("trip", {})
        fare = dispute.get("fare", {})
        points = [
            f"Rider claim: {rider.get('claim')}",
            f"Rider history: {rider.get('dispute_history', 0)} prior dispute(s), rating {rider.get('avg_rating')}.",
        ]
        if e.category == "route_deviation":
            if e.deviation_ratio is not None and e.excess_distance_km is not None:
                points.append(
                    f"Trip was {e.deviation_ratio * 100:.1f}% longer than optimal "
                    f"({e.excess_distance_km:.1f} km extra)."
                )
            else:
                points.append("Route distance data is missing; deviation cannot be verified.")
            if e.has_unexpected_stop:
                points.append(f"Unexpected {e.unexpected_stop_min:.1f}-min stop confirmed by GPS dwell.")
            if not e.traffic_detected:
                points.append("No traffic justification for the longer route.")
            points.append(
                f"Rider was charged {format_money(e.total_charged)} vs an estimated "
                f"{format_money(e.optimal_total_estimate)} for the optimal route."
            )
        elif e.category == "no_show":
            if e.driver_arrived is False and e.driver_arrival_distance_m is not None:
                points.append(
                    f"Driver never arrived — closest approach was {e.driver_arrival_distance_m:.0f} m from pickup."
                )
            wait_str = f"{e.driver_wait_min:.0f} min" if e.driver_wait_min is not None else "an unknown duration"
            points.append(f"Driver waited {wait_str} and was {e.driver_late_min:.0f} min late.")
            points.append(f"Rider was charged a {format_money(e.cancellation_fee)} cancellation fee.")
        return points

    def _desired_outcome(self, dispute: dict, e: EvidenceAnalysis) -> str:
        if e.category == "route_deviation":
            return "full refund of the excess distance fare plus 50% of the base fare"
        if e.category == "no_show":
            return "full refund of the cancellation fee"
        return "refund or compensation in favour of the rider"

    def _policy_citations(self, e: EvidenceAnalysis) -> list[str]:
        if e.category == "route_deviation":
            return ["RD-001.4", "RD-001.6"]
        if e.category == "no_show":
            return ["NS-001.2", "NS-001.4"]
        return []


class DriverAdvocateAgent(AdvocateAgent):
    name = "Driver Advocate"
    description = "Represents the driver; argues for driver-favourable outcomes."
    party = "driver"
    opponent = "rider"

    def _gather_points(self, dispute: dict, e: EvidenceAnalysis) -> list[str]:
        driver = dispute.get("driver", {})
        trip = dispute.get("trip", {})
        points = [
            f"Driver response: {driver.get('response')}",
            f"Driver history: {driver.get('dispute_history', 0)} prior dispute(s), rating {driver.get('avg_rating')}.",
        ]
        if e.category == "route_deviation":
            if e.traffic_detected:
                points.append("Live traffic data confirms the detour was justified.")
            else:
                points.append("Driver states the detour was to avoid traffic (unconfirmed by live data).")
            if e.has_unexpected_stop:
                # Bug #6: only claim stop disclosure if it is computed from the chat log.
                if e.driver_disclosed_stop:
                    points.append(
                        f"The {e.unexpected_stop_min:.1f}-min stop was proactively disclosed by the driver in chat."
                    )
                elif e.driver_stop_mentions > 0:
                    points.append(f"The driver mentioned a break in chat ({e.driver_stop_mentions} mention(s)).")
            points.append(f"Driver completed {driver.get('trips_completed')} trips with rating {driver.get('avg_rating')}.")
        elif e.category == "no_show":
            if e.driver_arrived is True:
                if e.driver_arrival_distance_m is not None:
                    points.append(f"Driver arrived within {e.driver_arrival_distance_m:.0f} m of pickup.")
                wait_str = f"{e.driver_wait_min:.0f} min" if e.driver_wait_min is not None else "an unspecified duration"
                points.append(f"Driver waited {wait_str} before cancelling.")
            elif e.driver_arrived is False and e.driver_arrival_distance_m is not None:
                points.append(f"Driver reports arriving near the pickup (closest {e.driver_arrival_distance_m:.0f} m).")
            points.append(f"Driver made {e.driver_contact_attempts} contact attempt(s) in chat.")
        return points

    def _desired_outcome(self, dispute: dict, e: EvidenceAnalysis) -> str:
        if e.category == "route_deviation":
            return "dismissal of the refund claim (fare upheld)"
        if e.category == "no_show":
            return "upholding of the cancellation fee"
        return "dismissal of the rider's claim"

    def _policy_citations(self, e: EvidenceAnalysis) -> list[str]:
        if e.category == "route_deviation":
            return ["RD-001.5", "RD-001.2"]
        if e.category == "no_show":
            return ["NS-001.5", "NS-001.1"]
        return []
