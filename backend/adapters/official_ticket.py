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
import math
from typing import Any, Optional

from ..schemas import Dispute, OfficialTicket, dump_dispute

# Official dispute_type -> internal category.
TYPE_MAP: dict[str, str] = {
    "no_show_charge": "no_show",
}


def is_official_ticket(payload: dict) -> bool:
    """True if ``payload`` looks like the organiser's official format."""
    return isinstance(payload, dict) and "dispute_ticket" in payload


def normalize_official_ticket(ticket: dict) -> dict:
    """Convert an official ticket into an internal dispute dict."""
    validated = OfficialTicket.model_validate(ticket)
    raw_events = ticket.get("app_events", [])
    ticket = validated.model_dump(by_alias=True, exclude_none=True)
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
            "cancellation_fee": trip.get("cancellation_fee"),
        },
        "chat_log": [_normalize_chat(c) for c in chats],
        "raw_app_events": raw_events,
        "cancellation_policy_override": policy,
    }

    if category == "no_show":
        arrived, arrival_time = _derive_arrival(events, gps, _parse_dt(trip.get("driver_arrival_time")))
        distance = None
        gaps: list[str] = []
        if arrived is None:
            arrived, arrival_time, distance, gaps = _derive_gps_arrival(trip, gps)
        if arrived is False:
            # A nonarrival ruling does not depend on waiting or lateness.
            # Supplied arrival/wait claims still contradict that conclusion.
            for field in ("driver_arrival_time", "driver_wait_start"):
                if field in trip:
                    gaps.append(f"trip_data.{field} (conflicting nonarrival)")
            wait_min = late_min = None
        else:
            gaps.extend(_timing_gaps(trip, events, gps, arrival_time))
            gaps.extend(_departure_gaps(trip, gps, arrival_time))
            wait_min = _wait_minutes(trip, arrival_time)
            late_min = _late_minutes(trip, arrival_time)
        normalized["normalization_gaps"] = gaps
        # Conflicting clocks cannot establish reliable elapsed durations.
        if gaps:
            wait_min = late_min = None
        normalized["gps"] = {
            "driver_arrival": {
                "arrived": arrived,
                "closest_distance_to_pickup_m": distance,
                "wait_time_min": wait_min,
                "late_min": late_min,
            }
        }
    else:
        # Unknown / unsupported type: the policy engine escalates it with a
        # clear reason (category is surfaced in the explanation). No crash.
        normalized["gps"] = {}

    return dump_dispute(Dispute.model_validate(normalized))


# --------------------------------------------------------------------------- #
# Field mapping helpers
# --------------------------------------------------------------------------- #


def _party(profile: dict, rider_id_key: str) -> dict:
    party: dict[str, Any] = {
        "id": profile.get(rider_id_key),
        "name": profile.get("name"),
        "route_consent": profile.get("route_consent", "unknown"),
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


def _derive_arrival(events: list[dict], telemetry: list[dict],
                    trip_arrival: Optional[datetime] = None) -> tuple[Optional[bool], Optional[datetime]]:
    """Driver arrival from ``app_events``, else from ``gps_telemetry`` status."""
    for e in events:
        if e.get("event_type") == "driver_arrived":
            return True, _parse_dt(e.get("timestamp"))
    for status in ("arrived", "waiting"):
        for p in telemetry:
            if p.get("status") == status:
                # Waiting only proves the driver has already arrived; it need
                # not share the exact earlier arrival timestamp.
                return True, trip_arrival if status == "waiting" and trip_arrival is not None else _parse_dt(p.get("timestamp"))
    return None, None


def _derive_gps_arrival(trip: dict, telemetry: list[dict]) -> tuple[
    Optional[bool], Optional[datetime], Optional[float], list[str]
]:
    """Infer arrival from a complete, comparable GPS observation window.

    Never expose a distance on inconclusive input: the evidence engine can use
    a distance alone as an arrival decision. Post-cancellation observations only
    establish coverage; they cannot establish a timely arrival.
    """
    gaps: list[str] = []
    cancellation = _parse_dt(trip.get("cancellation_time"))
    pickup = _coordinates(trip.get("pickup_location"))
    if cancellation is None:
        gaps.append("trip_data.cancellation_time (required for GPS arrival)")
    if pickup is None:
        gaps.append("trip_data.pickup_location (invalid or missing coordinates)")
    if not telemetry:
        gaps.append("gps_telemetry (missing arrival coverage)")
    observations: list[tuple[datetime, float, float]] = []
    for i, point in enumerate(telemetry):
        timestamp = _parse_dt(point.get("timestamp"))
        since_cancel = _minutes_between(timestamp, cancellation)
        coordinates = _coordinates(point)
        if since_cancel is None:
            gaps.append(f"gps_telemetry[{i}].timestamp (invalid or uncomparable)")
        elif point.get("status") == "cancelled" and since_cancel < 0:
            gaps.append(f"gps_telemetry[{i}].timestamp (conflicting cancelled chronology)")
        if coordinates is None:
            gaps.append(f"gps_telemetry[{i}] (invalid or missing coordinates)")
        if timestamp is not None and since_cancel is not None and coordinates is not None and pickup is not None:
            observations.append((timestamp, since_cancel, _distance_m(pickup, coordinates)))
    if gaps:
        return None, None, None, gaps
    if not any(delta < 0 for _, delta, _ in observations) or not any(delta >= 0 for _, delta, _ in observations):
        return None, None, None, ["gps_telemetry (must cover before and through cancellation)"]
    before_cancel = [(timestamp, distance) for timestamp, delta, distance in observations if delta <= 0]
    nearby = [(timestamp, distance) for timestamp, distance in before_cancel if distance <= 150]
    closest = min(distance for _, distance in before_cancel)
    if nearby:
        return True, min(timestamp for timestamp, _ in nearby), closest, []
    if any(distance <= 150 for _, delta, distance in observations if delta > 0):
        return None, None, None, ["gps_telemetry (arrival only observed after cancellation)"]
    return False, None, closest, []


def _departure_gaps(trip: dict, telemetry: list[dict], arrival_time: Optional[datetime]) -> list[str]:
    """An arrival does not prove continuous waiting when GPS shows departure.

    Apply to both explicit arrival events and GPS-inferred arrivals. Returning
    later cannot turn an interrupted wait into a continuous waiting period.
    """
    pickup = _coordinates(trip.get("pickup_location"))
    cancellation = _parse_dt(trip.get("cancellation_time"))
    if pickup is None or arrival_time is None or cancellation is None:
        return []
    gaps = []
    for i, point in enumerate(telemetry):
        timestamp = _parse_dt(point.get("timestamp"))
        since_arrival = _minutes_between(timestamp, arrival_time)
        until_cancel = _minutes_between(cancellation, timestamp)
        coordinates = _coordinates(point)
        if (since_arrival is not None and since_arrival >= 0
                and until_cancel is not None and until_cancel >= 0
                and coordinates is not None and _distance_m(pickup, coordinates) > 150):
            gaps.append(f"gps_telemetry[{i}] (departure contradicts continuous wait)")
    return gaps


def _coordinates(value: Any) -> Optional[tuple[float, float]]:
    if not isinstance(value, dict):
        return None
    coordinates: list[float] = []
    for field, limit in (("lat", 90), ("lng", 180)):
        raw = value.get(field)
        if isinstance(raw, bool):
            return None
        parsed = _to_float(raw)
        if parsed is None or not math.isfinite(parsed) or abs(parsed) > limit:
            return None
        coordinates.append(parsed)
    return coordinates[0], coordinates[1]


def _distance_m(start: tuple[float, float], end: tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*start, *end))
    haversine = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, haversine))))


def _wait_minutes(trip: dict, arrival_time: Optional[datetime]) -> Optional[float]:
    # A supplied but invalid timestamp must not silently fall through.
    wait_start = arrival_time
    for key in ("driver_wait_start", "driver_arrival_time"):
        if trip.get(key) is not None:
            wait_start = _parse_dt(trip[key])
            break
    cancellation = _parse_dt(trip.get("cancellation_time"))
    delta = _minutes_between(cancellation, wait_start)
    return delta if delta is not None and delta >= 0 else None


def _late_minutes(trip: dict, arrival_time: Optional[datetime]) -> Optional[float]:
    scheduled = _parse_dt(trip.get("scheduled_time"))
    delta = _minutes_between(arrival_time, scheduled)
    if delta is None:
        return None
    return max(0.0, delta)


def _timing_gaps(trip: dict, events: list[dict], telemetry: list[dict],
                 arrival_time: Optional[datetime]) -> list[str]:
    """Check comparable clocks and chronology without inventing a timezone."""
    gaps: list[str] = []
    arrivals: list[tuple[str, Optional[datetime]]] = []
    for field in ("driver_arrival_time", "driver_wait_start", "scheduled_time", "cancellation_time"):
        parsed = _parse_dt(trip.get(field))
        if parsed is None and (field in trip or field in ("scheduled_time", "cancellation_time")):
            gaps.append(f"trip_data.{field}")
        if field == "driver_arrival_time" and field in trip:
            arrivals.append((f"trip_data.{field}", parsed))
    for label, records, field, value in (
        ("app_events", events, "event_type", "driver_arrived"),
        ("gps_telemetry", telemetry, "status", "arrived"),
    ):
        for i, record in enumerate(records):
            if record.get(field) == value:
                arrivals.append((f"{label}[{i}].timestamp", _parse_dt(record.get("timestamp"))))
    if arrival_time is None:
        gaps.append("gps.driver_arrival.arrival_time")
    for path, value in arrivals:
        delta = _minutes_between(value, arrival_time)
        if delta is None or delta != 0:
            gaps.append(path + " (missing, invalid or conflicting arrival)")
    wait_start = _parse_dt(trip.get("driver_wait_start")) or _parse_dt(trip.get("driver_arrival_time")) or arrival_time
    since_arrival = _minutes_between(wait_start, arrival_time)
    if since_arrival is None or since_arrival < 0:
        gaps.append("trip_data.driver_wait_start (uncomparable or before arrival)")
    if _wait_minutes(trip, arrival_time) is None:
        gaps.append("trip_data.cancellation_time (uncomparable or before waiting)")
    if _late_minutes(trip, arrival_time) is None:
        gaps.append("trip_data.scheduled_time (uncomparable or missing)")
    cancellation = _parse_dt(trip.get("cancellation_time"))
    for i, record in enumerate(telemetry):
        status = record.get("status")
        if status not in ("waiting", "cancelled"):
            continue
        timestamp = _parse_dt(record.get("timestamp"))
        from_arrival = _minutes_between(timestamp, arrival_time)
        from_cancel = _minutes_between(timestamp, cancellation)
        if (from_arrival is None or from_cancel is None or from_arrival < 0
                or (status == "waiting" and from_cancel > 0)
                or (status == "cancelled" and from_cancel < 0)):
            gaps.append(f"gps_telemetry[{i}].timestamp (conflicting {status} chronology)")
    return list(dict.fromkeys(gaps))


# --------------------------------------------------------------------------- #
# Small parsing helpers
# --------------------------------------------------------------------------- #


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        # Python 3.10 does not accept the ISO UTC suffix directly.
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _minutes_between(later: Optional[datetime], earlier: Optional[datetime]) -> Optional[float]:
    if later is None or earlier is None:
        return None
    try:
        return (later - earlier).total_seconds() / 60.0
    except TypeError:
        # Mixing timezone-aware and local timestamps has no known ordering.
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
