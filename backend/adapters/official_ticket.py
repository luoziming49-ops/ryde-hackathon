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

from datetime import datetime
from typing import Any, Optional

# Official dispute_type -> internal category.
TYPE_MAP: dict[str, str] = {
    "no_show_charge": "no_show",
}


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
            "cancellation_fee": _to_float(trip.get("cancellation_fee")) or 0.0,
            "base_fare": 0.0,
        },
        "chat_log": [_normalize_chat(c) for c in chats],
        "raw_app_events": events,
        "cancellation_policy_override": policy,
    }

    if category == "no_show":
        arrived, arrival_time = _derive_arrival(events, gps)
        wait_min = _wait_minutes(trip, arrival_time)
        late_min = _late_minutes(trip, arrival_time)
        normalized["gps"] = {
            "driver_arrival": {
                "arrived": arrived,
                "wait_time_min": wait_min,
                "late_min": late_min,
            }
        }
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


def _derive_arrival(events: list[dict], telemetry: list[dict]) -> tuple[Optional[bool], Optional[datetime]]:
    """Driver arrival from ``app_events``, else from ``gps_telemetry`` status."""
    for e in events:
        if e.get("event_type") == "driver_arrived":
            return True, _parse_dt(e.get("timestamp"))
    for p in telemetry:
        if p.get("status") in ("arrived", "waiting"):
            return True, _parse_dt(p.get("timestamp"))
    return None, None


def _wait_minutes(trip: dict, arrival_time: Optional[datetime]) -> Optional[float]:
    wait_start = _parse_dt(trip.get("driver_wait_start")) or _parse_dt(trip.get("driver_arrival_time"))
    cancellation = _parse_dt(trip.get("cancellation_time"))
    return _minutes_between(cancellation, wait_start)


def _late_minutes(trip: dict, arrival_time: Optional[datetime]) -> float:
    scheduled = _parse_dt(trip.get("scheduled_time"))
    delta = _minutes_between(arrival_time, scheduled)
    if delta is None:
        return 0.0
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
