"""Deterministic evidence analysis engine.

Converts raw dispute evidence (GPS, chat, fare, history) into structured,
machine-readable findings. This layer is intentionally deterministic — the
agents and judge reason *on top of* these findings, but the facts themselves
are computed, not hallucinated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional


@dataclass
class EvidenceAnalysis:
    category: str
    # Route deviation
    deviation_ratio: Optional[float] = None
    excess_distance_km: Optional[float] = None
    has_unexpected_stop: bool = False
    unexpected_stop_min: float = 0.0
    traffic_detected: bool = False
    duration_delta_min: Optional[float] = None
    # No-show
    driver_arrival_distance_m: Optional[float] = None
    driver_wait_min: Optional[float] = None
    driver_late_min: Optional[float] = None
    driver_arrived: Optional[bool] = None
    free_wait_min: Optional[float] = None  # per-ticket override of the no-show wait threshold
    # Fare
    excess_distance_fare: float = 0.0
    surge_refund: float = 0.0
    base_fare: float = 0.0
    cancellation_fee: float = 0.0
    total_charged: float = 0.0
    optimal_total_estimate: float = 0.0
    # Behavioural
    rider_dispute_history: int = 0
    driver_dispute_history: int = 0
    rider_contact_attempts: int = 0
    driver_contact_attempts: int = 0
    driver_call_attempts: int = 0
    # Stop disclosure (route_deviation)
    driver_disclosed_stop: bool = False
    driver_stop_mentions: int = 0
    # Evidence completeness
    gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_evidence(dispute: dict) -> EvidenceAnalysis:
    category = dispute.get("category", "")
    trip = dispute.get("trip", {}) or {}
    fare = dispute.get("fare", {}) or {}
    gps = dispute.get("gps", {}) or {}
    rider = dispute.get("rider", {}) or {}
    driver = dispute.get("driver", {}) or {}

    analysis = EvidenceAnalysis(
        category=category,
        base_fare=_to_float(fare.get("base_fare")) or 0.0,
        cancellation_fee=_to_float(fare.get("cancellation_fee")) or 0.0,
        total_charged=_to_float(fare.get("total_charged")) or 0.0,
        optimal_total_estimate=_to_float(fare.get("optimal_total_estimate")) or 0.0,
        rider_dispute_history=_to_int(rider.get("dispute_history")),
        driver_dispute_history=_to_int(driver.get("dispute_history")),
    )

    # Contact attempts from chat log. "system" senders never count; a message
    # with no explicit type is treated as a "message".
    chat = dispute.get("chat_log", []) or []
    analysis.rider_contact_attempts = sum(
        1 for m in chat if m.get("from") == "rider" and _is_contact_type(m)
    )
    analysis.driver_contact_attempts = sum(
        1 for m in chat if m.get("from") == "driver" and _is_contact_type(m)
    )
    analysis.driver_call_attempts = sum(
        1 for m in chat if m.get("from") == "driver" and m.get("type") == "call"
    )

    # Did the driver proactively disclose an unexpected stop *before* the rider
    # first queried it? Computed from the chat log, never assumed.
    analysis.driver_stop_mentions = _count_driver_stop_mentions(chat)
    analysis.driver_disclosed_stop = _driver_proactively_disclosed_stop(chat)

    # Per-ticket no-show policy override (official tickets carry thresholds).
    if category == "no_show":
        override = dispute.get("cancellation_policy_override") or {}
        analysis.free_wait_min = _to_float(override.get("free_wait_time_min"))

    if category == "route_deviation":
        _analyze_route_deviation(analysis, trip, fare, gps)
    elif category == "no_show":
        _analyze_no_show(analysis, trip, fare, gps)
    elif category == "property_damage":
        analysis.notes.append("Image evidence required; multi-modal analysis is a stretch goal.")
    elif category == "safety_incident":
        analysis.notes.append("Safety incident — flagged for mandatory human escalation.")
    else:
        analysis.notes.append(
            f"Unrecognised dispute category '{category}'; escalated for human review."
        )

    return analysis


# --------------------------------------------------------------------------- #
# Stop disclosure — word-boundary matching on a narrow phrase list.
# --------------------------------------------------------------------------- #

_STOP_DISCLOSURE_PHRASES = (
    "quick break",
    "toilet",
    "restroom",
    "pit stop",
    "stopping for",
    "stopped for",
    "need to stop",
)

# Broader set used only to detect that the *rider* first noticed/asked about a
# stop (so a driver reply after that point is reactive, not proactive).
_RIDER_STOP_QUERY_WORDS = ("stop", "stopped", "stopping", "break", "waiting", "waited")


def _word_boundary_match(pattern: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(pattern)}\b", (text or "").lower()) is not None


def _is_stop_disclosure(text: str) -> bool:
    return any(_word_boundary_match(p, text) for p in _STOP_DISCLOSURE_PHRASES)


def _is_stop_query(text: str) -> bool:
    return any(_word_boundary_match(w, text) for w in _RIDER_STOP_QUERY_WORDS)


def _count_driver_stop_mentions(chat: list[dict]) -> int:
    return sum(
        1 for m in chat if m.get("from") == "driver" and _is_stop_disclosure(m.get("text", ""))
    )


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _driver_proactively_disclosed_stop(chat: list[dict]) -> bool:
    """True only if the driver mentioned a stop before the rider first asked about one."""
    rider_ask_ts: Optional[datetime] = None
    for m in chat:
        if m.get("from") == "rider" and _is_stop_query(m.get("text", "")):
            rider_ask_ts = _parse_ts(m.get("ts") or m.get("timestamp"))
            break
    for m in chat:
        if m.get("from") == "driver" and _is_stop_disclosure(m.get("text", "")):
            driver_ts = _parse_ts(m.get("ts") or m.get("timestamp"))
            if rider_ask_ts is None:
                return True
            if driver_ts is not None and driver_ts <= rider_ask_ts:
                return True
    return False


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _is_contact_type(m: dict) -> bool:
    """A chat entry counts as a contact attempt unless it is a system message."""
    return m.get("type", "message") in ("message", "call")


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------------------------- #
# Category-specific analysis
# --------------------------------------------------------------------------- #


def _analyze_route_deviation(a: EvidenceAnalysis, trip: dict, fare: dict, gps: dict) -> None:
    optimal = _to_float(trip.get("optimal_distance_km"))
    actual = _to_float(trip.get("actual_distance_km"))

    if optimal is None or optimal <= 0:
        a.gaps.append("trip.optimal_distance_km")
    if actual is None or actual < 0:
        a.gaps.append("trip.actual_distance_km")

    if optimal is not None and optimal > 0 and actual is not None and actual >= 0:
        a.excess_distance_km = max(0.0, actual - optimal)
        # Round to 4 decimals before any boundary comparison (bug #2).
        a.deviation_ratio = round((actual - optimal) / optimal, 4)
    else:
        a.excess_distance_km = None
        a.deviation_ratio = None

    a.traffic_detected = bool(trip.get("traffic_detected", False))

    stops = trip.get("unexpected_stops", []) or []
    if stops:
        a.has_unexpected_stop = True
        a.unexpected_stop_min = sum(_to_float(s.get("dwell_min")) or 0.0 for s in stops)

    est_dur = _to_float(trip.get("estimated_duration_min"))
    act_dur = _to_float(trip.get("actual_duration_min"))
    a.duration_delta_min = (act_dur - est_dur) if (act_dur is not None and est_dur is not None) else None

    # Fare deltas.
    dist_actual = _to_float(fare.get("distance_fare_actual")) or 0.0
    dist_optimal = _to_float(fare.get("distance_fare_optimal")) or 0.0
    a.excess_distance_fare = round(max(0.0, dist_actual - dist_optimal), 2)

    # A non-numeric surge multiplier is an evidence gap, never a silent 1.0.
    surge_raw = fare.get("surge_multiplier")
    surge = _to_float(surge_raw)
    if surge_raw is not None and surge is None:
        a.gaps.append("fare.surge_multiplier")
        surge = 1.0
    elif surge is None:
        surge = 1.0
    if surge > 1.0:
        a.surge_refund = round(a.excess_distance_fare * (surge - 1.0), 2)

    if a.deviation_ratio is not None:
        a.notes.append(
            f"Route deviation {a.deviation_ratio * 100:.1f}% "
            f"({a.excess_distance_km:.1f} km over optimal)."
        )
    else:
        a.notes.append("Route deviation could not be computed (missing distance data).")
    if a.has_unexpected_stop:
        a.notes.append(f"Unexpected stop of {a.unexpected_stop_min:.1f} min detected in GPS dwell.")
    if a.traffic_detected:
        a.notes.append("Live traffic data confirms a valid detour.")
    else:
        a.notes.append("No traffic justification found for the detour.")


def _analyze_no_show(a: EvidenceAnalysis, trip: dict, fare: dict, gps: dict) -> None:
    arrival = gps.get("driver_arrival") or {}
    dist = _to_float(arrival.get("closest_distance_to_pickup_m"))
    arrived_flag = arrival.get("arrived")
    wait = _to_float(arrival.get("wait_time_min"))
    late = _to_float(arrival.get("late_min"))

    # An explicit "arrived" boolean (from the official-ticket adapter) wins;
    # otherwise arrival is derived from the closest-approach distance.
    if arrived_flag is not None:
        a.driver_arrived = bool(arrived_flag)
        a.driver_arrival_distance_m = dist
    elif dist is not None:
        a.driver_arrival_distance_m = dist
        a.driver_arrived = dist <= 150
    else:
        # Missing distance must NOT be read as "did not arrive" (bug #3).
        a.gaps.append("gps.driver_arrival.closest_distance_to_pickup_m")
        a.driver_arrival_distance_m = None
        a.driver_arrived = None

    if wait is None:
        a.gaps.append("gps.driver_arrival.wait_time_min")
        a.driver_wait_min = None
    else:
        a.driver_wait_min = wait

    a.driver_late_min = late if late is not None else 0.0

    if a.driver_arrived is None:
        a.notes.append("Driver arrival status could not be determined (missing GPS arrival data).")
    elif a.driver_arrived:
        a.notes.append("Driver arrived at the pickup point.")
    else:
        a.notes.append(
            f"Driver closest approach to pickup: {a.driver_arrival_distance_m:.0f} m "
            "(did NOT arrive)."
        )
    wait_str = f"{a.driver_wait_min:.0f} min" if a.driver_wait_min is not None else "unknown"
    a.notes.append(f"Driver waited {wait_str} and was {a.driver_late_min:.0f} min late.")
