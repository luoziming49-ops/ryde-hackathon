"""Deterministic evidence analysis engine.

Converts raw dispute evidence (GPS, chat, fare, history) into structured,
machine-readable findings. This layer is intentionally deterministic — the
agents and judge reason *on top of* these findings, but the facts themselves
are computed, not hallucinated.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
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
    trip = dispute.get("trip", {})
    fare = dispute.get("fare", {})
    gps = dispute.get("gps", {})
    rider = dispute.get("rider", {})
    driver = dispute.get("driver", {})

    analysis = EvidenceAnalysis(
        category=category,
        base_fare=fare.get("base_fare", 0.0),
        cancellation_fee=fare.get("cancellation_fee", 0.0),
        total_charged=fare.get("total_charged", 0.0),
        optimal_total_estimate=fare.get("optimal_total_estimate", 0.0),
        rider_dispute_history=rider.get("dispute_history", 0),
        driver_dispute_history=driver.get("dispute_history", 0),
    )

    # Contact attempts from chat log.
    chat = dispute.get("chat_log", [])
    analysis.rider_contact_attempts = sum(1 for m in chat if m.get("from") == "rider")
    analysis.driver_contact_attempts = sum(1 for m in chat if m.get("from") == "driver")

    # Did the driver proactively disclose an unexpected stop *before* the rider
    # first queried it? Computed from the chat log, never assumed.
    analysis.driver_stop_mentions = _count_driver_stop_mentions(chat)
    analysis.driver_disclosed_stop = _driver_proactively_disclosed_stop(chat)

    if category == "route_deviation":
        _analyze_route_deviation(analysis, trip, fare, gps)
    elif category == "no_show":
        _analyze_no_show(analysis, trip, fare, gps)
    elif category == "property_damage":
        analysis.notes.append("Image evidence required; multi-modal analysis is a stretch goal.")
    elif category == "safety_incident":
        analysis.notes.append("Safety incident — flagged for mandatory human escalation.")

    return analysis


_STOP_KEYWORDS = ("stop", "break", "toilet", "rest", "restroom")


def _is_stop_message(text: str) -> bool:
    lowered = (text or "").lower()
    return any(k in lowered for k in _STOP_KEYWORDS)


def _count_driver_stop_mentions(chat: list[dict]) -> int:
    return sum(1 for m in chat if m.get("from") == "driver" and _is_stop_message(m.get("text", "")))


def _driver_proactively_disclosed_stop(chat: list[dict]) -> bool:
    """True only if the driver mentioned a stop before the rider first asked about one."""
    rider_ask_ts = None
    for m in chat:
        if m.get("from") == "rider" and _is_stop_message(m.get("text", "")):
            rider_ask_ts = m.get("ts")
            break
    for m in chat:
        if m.get("from") == "driver" and _is_stop_message(m.get("text", "")):
            if rider_ask_ts is None or m.get("ts", "") <= rider_ask_ts:
                return True
    return False


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _analyze_route_deviation(a: EvidenceAnalysis, trip: dict, fare: dict, gps: dict) -> None:
    optimal = _to_float(trip.get("optimal_distance_km"))
    actual = _to_float(trip.get("actual_distance_km"))

    if optimal is None or optimal <= 0:
        a.gaps.append("trip.optimal_distance_km")
    if actual is None:
        a.gaps.append("trip.actual_distance_km")

    if optimal is not None and optimal > 0 and actual is not None:
        a.excess_distance_km = max(0.0, actual - optimal)
        # Round to 4 decimals before any boundary comparison (bug #2).
        a.deviation_ratio = round((actual - optimal) / optimal, 4)
    else:
        a.excess_distance_km = None
        a.deviation_ratio = None

    a.traffic_detected = bool(trip.get("traffic_detected", False))

    stops = trip.get("unexpected_stops", [])
    if stops:
        a.has_unexpected_stop = True
        a.unexpected_stop_min = sum(float(s.get("dwell_min", 0)) for s in stops)

    est_dur = _to_float(trip.get("estimated_duration_min"))
    act_dur = _to_float(trip.get("actual_duration_min"))
    a.duration_delta_min = (act_dur - est_dur) if (act_dur is not None and est_dur is not None) else None

    # Fare deltas.
    dist_actual = _to_float(fare.get("distance_fare_actual")) or 0.0
    dist_optimal = _to_float(fare.get("distance_fare_optimal")) or 0.0
    a.excess_distance_fare = round(max(0.0, dist_actual - dist_optimal), 2)

    surge = _to_float(fare.get("surge_multiplier")) or 1.0
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
    wait = _to_float(arrival.get("wait_time_min"))
    late = _to_float(arrival.get("late_min"))

    if dist is None:
        # Missing distance must NOT be read as "did not arrive" (bug #3).
        a.gaps.append("gps.driver_arrival.closest_distance_to_pickup_m")
        a.driver_arrival_distance_m = None
        a.driver_arrived = None
    else:
        a.driver_arrival_distance_m = dist
        a.driver_arrived = dist <= 150

    if wait is None:
        a.gaps.append("gps.driver_arrival.wait_time_min")
        a.driver_wait_min = None
    else:
        a.driver_wait_min = wait

    a.driver_late_min = late if late is not None else 0.0

    if a.driver_arrived is None:
        a.notes.append("Driver arrival status could not be determined (missing GPS arrival data).")
    else:
        a.notes.append(
            f"Driver closest approach to pickup: {a.driver_arrival_distance_m:.0f} m "
            f"({'arrived' if a.driver_arrived else 'did NOT arrive'})."
        )
    wait_str = f"{a.driver_wait_min:.0f} min" if a.driver_wait_min is not None else "unknown"
    a.notes.append(f"Driver waited {wait_str} and was {a.driver_late_min:.0f} min late.")
