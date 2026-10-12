"""Adapter: normalise the organiser's official dispute-ticket format.

The official format has a top-level ``dispute_ticket`` key and a different field
layout (``rider_profile`` / ``driver_profile`` / ``trip_data`` /
``gps_telemetry`` / ``chat_logs`` / ``app_events`` / ``cancellation_policy``).
This module detects that shape and converts it into our internal dispute dict,
so the rest of the pipeline is unchanged.

It is intentionally forgiving: an unknown ``dispute_type`` escalates (with a
clear reason) rather than crashing, and missing sections fall back to defaults.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..schemas import Money

# Official dispute_type -> internal category.
TYPE_MAP: dict[str, str] = {
    "no_show_charge": "no_show",
}

# Arrival is within this distance of the pickup (metres) per NS-001.1/NS-001.2.
ARRIVAL_RADIUS_M = 150.0


class OfficialTripData(BaseModel):
    """``trip_data`` section: an object with a non-negative, finite money field."""

    model_config = ConfigDict(extra="allow")

    cancellation_fee: Money = None


class OfficialTicket(BaseModel):
    """Shape validation for the organiser's official dispute-ticket format.

    Structural rules (reject a malformed ticket with a clear 422 instead of a
    500): ``dispute_ticket`` / ``trip_data`` / the two profiles must be
    objects; ``chat_logs`` / ``app_events`` / ``gps_telemetry`` must be lists
    of objects. Money fields are additionally constrained to be non-negative
    and finite (see ``Money``). Unknown extra keys are preserved.
    """

    model_config = ConfigDict(extra="allow")

    dispute_ticket: dict
    trip_data: OfficialTripData = Field(default_factory=OfficialTripData)
    rider_profile: dict = Field(default_factory=dict)
    driver_profile: dict = Field(default_factory=dict)
    chat_logs: list[dict] = Field(default_factory=list)
    app_events: list[dict] = Field(default_factory=list)
    gps_telemetry: list[dict] = Field(default_factory=list)
    cancellation_policy: dict = Field(default_factory=dict)


def validate_official_ticket(payload: dict) -> None:
    """Validate ``payload`` as an official ticket, raising ``ValidationError``.

    Callers turn the raised ``ValidationError`` into an HTTP 422.
    """
    OfficialTicket.model_validate(payload)


def is_official_ticket(payload: dict) -> bool:
    """True if ``payload`` looks like the organiser's official format."""
    return isinstance(payload, dict) and "dispute_ticket" in payload


def normalize_official_ticket(ticket: dict) -> dict:
    """Convert an official ticket into an internal dispute dict."""
    dt = ticket.get("dispute_ticket") or {}
    rider_p = ticket.get("rider_profile") or {}
    driver_p = ticket.get("driver_profile") or {}
    trip = ticket.get("trip_data") or {}
    gps = ticket.get("gps_telemetry") or []
    chats = ticket.get("chat_logs") or []
    events = ticket.get("app_events") or []
    policy = ticket.get("cancellation_policy") or {}

    raw_type = dt.get("dispute_type", "")
    category = TYPE_MAP.get(raw_type, raw_type or "unknown")

    rider = _party(rider_p, rider_id_key="rider_id")
    driver = _party(driver_p, rider_id_key="driver_id")
    rider["claim"] = dt.get("description") or ""
    driver["response"] = ""

    normalized: dict[str, Any] = {
        "case_id": dt.get("dispute_id") or dt.get("trip_id"),
        "category": category,
        "rider": rider,
        "driver": driver,
        "trip": {
            "pickup": trip.get("pickup_location"),
            "dropoff": trip.get("dropoff_location"),
            "scheduled_pickup": trip.get("scheduled_time"),
        },
        "fare": {
            "currency": "SGD",
            # Leave a missing/null cancellation_fee missing: the evidence engine
            # turns it into an evidence gap, it is never silently 0.0.
            "cancellation_fee": _to_float(trip.get("cancellation_fee")),
        },
        "chat_log": [_normalize_chat(c) for c in chats],
        "raw_app_events": events,
        "cancellation_policy_override": policy,
    }

    if category == "no_show":
        normalized["gps"] = {"driver_arrival": _derive_no_show_gps(trip, events, gps)}
    else:
        # Unknown / unsupported type: the policy engine escalates it with a
        # clear reason (category is surfaced in the explanation). No crash.
        normalized["gps"] = {}

    return normalized


# --------------------------------------------------------------------------- #
# Field mapping helpers
# --------------------------------------------------------------------------- #


def _party(profile: dict, rider_id_key: str) -> dict:
    party: dict[str, Any] = {
        "id": profile.get(rider_id_key),
        "name": profile.get("name"),
        "dispute_history": _dispute_history_int(profile),
        "trips_completed": _to_int(profile.get("total_trips")),
        "account_age_days": _to_int(profile.get("account_age_days")),
        "avg_rating": _to_float(profile.get("avg_rating")),
        "fraud_flags_list": _fraud_flags(profile),
    }
    if profile.get("vehicle"):
        party["vehicle"] = profile["vehicle"]
    if profile.get("payment_method"):
        party["payment_method"] = profile["payment_method"]
    return party


def _dispute_history_int(profile: dict) -> int:
    dh = profile.get("dispute_history")
    if isinstance(dh, dict):
        return int(dh.get("total_disputes") or 0)
    if isinstance(dh, (int, float)):
        return int(dh)
    return 0


def _fraud_flags(profile: dict) -> list[str]:
    """Map fraud_flags / fraud_flag_details / dispute_history into flags."""
    flags: list[str] = []
    if profile.get("fraud_flags") and profile.get("fraud_flag_details"):
        flags.append(str(profile["fraud_flag_details"]))
    dh = profile.get("dispute_history")
    if isinstance(dh, dict):
        total = dh.get("total_disputes") or 0
        rejected = dh.get("rejected") or 0
        if total >= 3 and total > 0 and (rejected / total) >= 0.5:
            flags.append("high rate of rejected disputes")
    return flags


def _normalize_chat(entry: dict) -> dict:
    return {
        "from": entry.get("sender"),
        "text": entry.get("content", ""),
        "ts": entry.get("timestamp"),
        "type": entry.get("type"),
    }


def _derive_no_show_gps(trip: dict, events: list[dict], telemetry: list[dict]) -> dict:
    """Build the internal ``gps.driver_arrival`` dict for a no-show ticket.

    One resolved arrival time is used for both wait and lateness (fix 3).
    """
    arrived, closest = _derive_arrival(trip, events, telemetry)
    arrival_time, conflict = _resolve_arrival_time(trip, events, telemetry)
    wait_min = _wait_minutes(trip, arrival_time)
    late_min = _late_minutes(trip, arrival_time)
    result: dict[str, Any] = {
        "arrived": arrived,
        "wait_time_min": wait_min,
        "late_min": late_min,
    }
    if closest is not None:
        result["closest_distance_to_pickup_m"] = closest
    if conflict:
        result["conflict"] = conflict
    return result


def _event_arrival_time(events: list[dict], telemetry: list[dict]) -> Optional[datetime]:
    """The arrival timestamp from a ``driver_arrived`` event or telemetry status."""
    for e in events:
        if e.get("event_type") == "driver_arrived":
            return _parse_dt(e.get("timestamp"))
    for p in telemetry:
        if p.get("status") in ("arrived", "waiting"):
            return _parse_dt(p.get("timestamp"))
    return None


def _derive_arrival(trip: dict, events: list[dict], telemetry: list[dict]) -> tuple[Optional[bool], Optional[float]]:
    """Return ``(arrived, closest_distance_to_pickup_m)``.

    ``arrived`` is ``True``/``False``/``None`` (``None`` = unknown).
    """
    # 1. Explicit arrival via an app event or telemetry status.
    for e in events:
        if e.get("event_type") == "driver_arrived":
            return True, None
    for p in telemetry:
        if p.get("status") in ("arrived", "waiting"):
            return True, None

    # 2. No explicit arrival: derive from the closest telemetry approach.
    pickup = trip.get("pickup_location") or {}
    pickup_lat = _to_float(pickup.get("lat"))
    pickup_lng = _to_float(pickup.get("lng"))
    cancellation = _parse_dt(trip.get("cancellation_time"))

    if telemetry:
        closest: Optional[float] = None
        latest_ts: Optional[datetime] = None
        for p in telemetry:
            ts = _parse_dt(p.get("timestamp"))
            if ts is not None and (latest_ts is None or ts > latest_ts):
                latest_ts = ts
            d = _haversine(pickup_lat, pickup_lng, _to_float(p.get("lat")), _to_float(p.get("lng")))
            if d is not None and (closest is None or d < closest):
                closest = d
        if closest is not None:
            if closest <= ARRIVAL_RADIUS_M:
                return True, closest
            # Closest > 150 m. Conclusive only if telemetry covers up to the
            # cancellation moment (otherwise the driver might have arrived after
            # the last tracked point).
            if cancellation is None or latest_ts is None or latest_ts >= cancellation:
                return False, closest
            return None, None

    # 3. No telemetry and no explicit arrival event -> unknown (gap).
    return None, None


def _resolve_arrival_time(trip: dict, events: list[dict], telemetry: list[dict]) -> tuple[Optional[datetime], Optional[str]]:
    """Resolve a single arrival time for wait + lateness.

    Returns ``(arrival_time, conflict_note)``. A conflict is recorded when
    ``trip_data.driver_arrival_time`` and the app-event arrival timestamp differ
    by more than 2 minutes, instead of silently picking one.
    """
    trip_arrival = _parse_dt(trip.get("driver_arrival_time"))
    event_arrival = _event_arrival_time(events, telemetry)

    if trip_arrival is not None and event_arrival is not None:
        diff_min = abs((trip_arrival - event_arrival).total_seconds()) / 60.0
        if diff_min > 2.0:
            conflict = (
                f"arrival time conflict: trip_data {trip_arrival.isoformat()} "
                f"vs app_events {event_arrival.isoformat()}"
            )
            return event_arrival, conflict

    resolved = event_arrival if event_arrival is not None else trip_arrival
    if resolved is None:
        resolved = _parse_dt(trip.get("driver_wait_start"))
    return resolved, None


def _wait_minutes(trip: dict, arrival_time: Optional[datetime]) -> Optional[float]:
    """Wait time = cancellation_time − (single resolved) arrival time."""
    wait_start = arrival_time
    if wait_start is None:
        wait_start = _parse_dt(trip.get("driver_wait_start")) or _parse_dt(trip.get("driver_arrival_time"))
    cancellation = _parse_dt(trip.get("cancellation_time"))
    return _minutes_between(cancellation, wait_start)


def _late_minutes(trip: dict, arrival_time: Optional[datetime]) -> Optional[float]:
    scheduled = _parse_dt(trip.get("scheduled_time"))
    delta = _minutes_between(arrival_time, scheduled)
    if delta is None:
        return None  # unknown (missing scheduled_time / arrival), NOT 0
    return max(0.0, delta)


# --------------------------------------------------------------------------- #
# Small parsing helpers
# --------------------------------------------------------------------------- #


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _minutes_between(later: Optional[datetime], earlier: Optional[datetime]) -> Optional[float]:
    if later is None or earlier is None:
        return None
    return (later - earlier).total_seconds() / 60.0


def _haversine(lat1: Optional[float], lng1: Optional[float], lat2: Optional[float], lng2: Optional[float]) -> Optional[float]:
    """Great-circle distance in metres, or ``None`` if any coordinate is missing."""
    if None in (lat1, lng1, lat2, lng2):
        return None
    r = 6371000.0  # Earth radius, metres
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _to_float(value: Any) -> Optional[float]:
    if value is None:
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
