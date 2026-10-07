"""Fraud & Bad-Faith Detection Agent (stretch goal).

Scores the likelihood that each party is abusing the dispute process using
dispute *rates* (disputes / trips) with a minimum-sample rule — not raw counts.
Emits per-party risk signals that the Judge factors into confidence for the
party who would benefit from the ruling.
"""

from __future__ import annotations

from typing import Any

from ..core.evidence import EvidenceAnalysis
from .base import BaseAgent

MIN_SAMPLE_TRIPS = 20
HIGH_RATE_THRESHOLD = 0.05  # 5% of trips disputed is high


class FraudDetectionAgent(BaseAgent):
    name = "Fraud & Bad-Faith Detection"
    description = "Scores dispute-abuse risk per party and flags suspicious patterns."

    def analyze(self, dispute: dict, evidence: EvidenceAnalysis) -> dict[str, Any]:
        rider = dispute.get("rider", {}) or {}
        driver = dispute.get("driver", {}) or {}

        rider_risk = self._score(
            dispute_history=rider.get("dispute_history", 0),
            trips=rider.get("trips_completed", 0),
            account_age=rider.get("account_age_days", 0),
        )
        driver_risk = self._score(
            dispute_history=driver.get("dispute_history", 0),
            trips=driver.get("trips_completed", 0),
            account_age=driver.get("account_age_days", 0),
        )

        # Case-level red flags (rate-based, not absolute counts).
        flags: list[str] = []
        if self._high_rate(rider):
            flags.append("Rider has a high dispute-filing rate.")
        if self._high_rate(driver):
            flags.append("Driver has a high dispute rate.")
        if evidence.category == "route_deviation" and evidence.deviation_ratio is not None and evidence.deviation_ratio > 0.5:
            flags.append("Extreme route deviation — possible detour abuse.")
        if evidence.category == "no_show" and evidence.driver_arrived is False and evidence.cancellation_fee > 0:
            flags.append("Cancellation fee charged despite driver never arriving — possible fee abuse.")

        # Adapter-supplied per-party flags (e.g. official-ticket fraud signals).
        for label, party in (("Rider", rider), ("Driver", driver)):
            for flag in party.get("fraud_flags_list") or []:
                flags.append(f"{label} fraud flag: {flag}")

        self.emit(
            "risk",
            f"Bad-faith risk: rider={rider_risk:.2f}, driver={driver_risk:.2f}.",
            rider_risk=rider_risk,
            driver_risk=driver_risk,
            flags=flags,
        )

        return {
            "rider_risk": rider_risk,
            "driver_risk": driver_risk,
            "rider_rationale": self._rationale(rider, rider_risk),
            "driver_rationale": self._rationale(driver, driver_risk),
            "flags": flags,
        }

    @staticmethod
    def _high_rate(party: dict) -> bool:
        trips = party.get("trips_completed") or 0
        if trips < MIN_SAMPLE_TRIPS:
            return False
        return ((party.get("dispute_history") or 0) / trips) >= HIGH_RATE_THRESHOLD

    @staticmethod
    def _score(dispute_history, trips, account_age) -> float:
        """Per-party risk in [0, 1], based on dispute rate with a minimum sample."""
        dispute_history = dispute_history or 0
        trips = trips or 0
        account_age = account_age or 0
        score = 0.0
        if trips >= MIN_SAMPLE_TRIPS:
            rate = dispute_history / trips
            score += min(rate / HIGH_RATE_THRESHOLD, 1.0) * 0.7
        else:
            # Insufficient sample: small, bounded uncertainty penalty.
            score += 0.15
        if account_age < 60:
            score += 0.2
        return round(min(score, 1.0), 3)

    @staticmethod
    def _rationale(party: dict, risk: float) -> str:
        trips = party.get("trips_completed") or 0
        disputes = party.get("dispute_history") or 0
        if trips >= MIN_SAMPLE_TRIPS:
            rate = disputes / trips
            return f"{disputes} dispute(s) over {trips} trips ({rate:.2%} rate)."
        return f"{disputes} dispute(s) over {trips} trips (insufficient sample)."
