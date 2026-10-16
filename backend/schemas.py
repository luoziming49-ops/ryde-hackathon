"""Typed request/dispute models for the API and the sample-data loader.

Nested pydantic models with ``extra="allow"``:

- numeric strings are coerced (e.g. ``"3.00"`` -> ``3.0``, ``"8"`` -> ``8``);
- non-numeric strings fail validation (HTTP 422 via FastAPI / a clear load
  error from the sample-data loader);
- unknown / extra keys are preserved rather than rejected.

The inline ``POST /api/resolve`` body and the ``sample_data/disputes.json``
loader both validate through these models, so the two paths coerce data the
same way.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _not_boolean(value: Any) -> Any:
    if isinstance(value, bool):
        raise ValueError("A number, not a boolean, is required")
    return value


Money = Annotated[float, BeforeValidator(_not_boolean), Field(ge=0, allow_inf_nan=False)]
Count = Annotated[int, BeforeValidator(_not_boolean), Field(ge=0)]


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Stop(_Base):
    lat: Optional[float] = None
    lng: Optional[float] = None
    dwell_min: Optional[float] = None
    label: Optional[str] = None


class Trip(_Base):
    id: Optional[str] = None
    pickup: Optional[dict] = None
    dropoff: Optional[dict] = None
    optimal_distance_km: Optional[float] = None
    actual_distance_km: Optional[float] = None
    traffic_detected: Optional[bool] = None
    unexpected_stops: list[Stop] = Field(default_factory=list)
    estimated_duration_min: Optional[float] = None
    actual_duration_min: Optional[float] = None
    scheduled_pickup: Optional[str] = None
    actual_pickup: Optional[str] = None
    actual_dropoff: Optional[str] = None


class Fare(_Base):
    currency: Optional[str] = None
    base_fare: Optional[Money] = None
    cancellation_fee: Optional[Money] = None
    surge_multiplier: Optional[Money] = None
    total_charged: Optional[Money] = None
    optimal_total_estimate: Optional[Money] = None
    distance_fare_actual: Optional[Money] = None
    distance_fare_optimal: Optional[Money] = None
    time_fare_actual: Optional[Money] = None
    time_fare_optimal: Optional[Money] = None
    promo_code: Optional[str] = None


class ChatMessage(_Base):
    ts: Optional[str] = None
    timestamp: Optional[str] = None
    from_: Optional[str] = Field(default=None, alias="from")
    text: Optional[str] = None
    sender: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None


class Party(_Base):
    id: Optional[str] = None
    name: Optional[str] = None
    claim: Optional[str] = None
    response: Optional[str] = None
    dispute_history: Optional[int] = None
    trips_completed: Optional[int] = None
    account_age_days: Optional[int] = None
    avg_rating: Optional[float] = None
    # Official-ticket fields (ignored by the internal engine but preserved).
    fraud_flags: Optional[int] = None
    fraud_flag_details: Optional[str] = None
    vehicle: Optional[str] = None
    payment_method: Optional[str] = None


class DriverArrival(_Base):
    closest_distance_to_pickup_m: Optional[float] = None
    arrival_time: Optional[str] = None
    wait_time_min: Optional[float] = None
    left_pickup_time: Optional[str] = None
    late_min: Optional[float] = None
    arrived: Optional[bool] = None


class Gps(_Base):
    optimal_route: list[Any] = Field(default_factory=list)
    actual_route: list[Any] = Field(default_factory=list)
    driver_arrival: Optional[DriverArrival] = None


class Dispute(_Base):
    """A full dispute as loaded from ``sample_data/disputes.json``."""

    case_id: str
    category: str
    filed_at: Optional[str] = None
    priority: Optional[str] = "standard"
    status: Optional[str] = "pending"
    rider: Party = Field(default_factory=Party)
    driver: Party = Field(default_factory=Party)
    trip: Trip = Field(default_factory=Trip)
    gps: Gps = Field(default_factory=Gps)
    fare: Fare = Field(default_factory=Fare)
    chat_log: list[ChatMessage] = Field(default_factory=list)
    normalization_gaps: list[str] = Field(default_factory=list)


class ResolveRequest(_Base):
    """Body for ``POST /api/resolve``.

    Provide either a ``case_id`` to resolve a known sample case, or a complete
    inline dispute. An inline dispute requires ``category``, ``rider`` and
    ``driver``; everything else is optional and missing fields are surfaced as
    evidence gaps (never as crashes).
    """

    case_id: Optional[str] = None
    category: Optional[str] = None
    rider: Optional[Party] = None
    driver: Optional[Party] = None
    trip: Optional[Trip] = None
    gps: Optional[Gps] = None
    fare: Optional[Fare] = None
    chat_log: list[ChatMessage] = Field(default_factory=list)
    priority: Optional[str] = "standard"
    status: Optional[str] = "pending"
    filed_at: Optional[str] = None

    def to_inline_dispute(self) -> dict:
        """Convert to an internal dispute dict, dropping ``None``-valued fields."""
        data = {
            "category": self.category,
            "rider": self.rider.model_dump(by_alias=True, exclude_none=True) if self.rider else {},
            "driver": self.driver.model_dump(by_alias=True, exclude_none=True) if self.driver else {},
            "trip": self.trip.model_dump(by_alias=True, exclude_none=True) if self.trip else {},
            "gps": self.gps.model_dump(by_alias=True, exclude_none=True) if self.gps else {},
            "fare": self.fare.model_dump(by_alias=True, exclude_none=True) if self.fare else {},
            "chat_log": [m.model_dump(by_alias=True, exclude_none=True) for m in self.chat_log],
            "priority": self.priority or "standard",
            "status": self.status or "pending",
        }
        if self.filed_at:
            data["filed_at"] = self.filed_at
        return data


def dump_dispute(dispute: Dispute) -> dict:
    """Dump a validated ``Dispute`` back to a plain dict for the engine."""
    return dispute.model_dump(by_alias=True, exclude_none=True)


class OfficialDisputeTicket(_Base):
    dispute_id: Optional[str] = None
    trip_id: Optional[str] = None
    dispute_type: Optional[str] = None
    description: Optional[str] = None


class OfficialHistory(_Base):
    total_disputes: Optional[Count] = None
    upheld: Optional[Count] = None
    upheld_against: Optional[Count] = None
    rejected: Optional[Count] = None


class OfficialProfile(_Base):
    rider_id: Optional[str] = None
    driver_id: Optional[str] = None
    name: Optional[str] = None
    account_age_days: Optional[Count] = None
    total_trips: Optional[Count] = None
    avg_rating: Optional[Money] = None
    dispute_history: Optional[OfficialHistory | Count] = None
    fraud_flags: Optional[Count] = None
    fraud_flag_details: Optional[str] = None
    vehicle: Optional[str] = None
    payment_method: Optional[str] = None


class OfficialTrip(_Base):
    pickup_location: Optional[dict] = None
    dropoff_location: Optional[dict] = None
    scheduled_time: Optional[str] = None
    driver_arrival_time: Optional[str] = None
    driver_wait_start: Optional[str] = None
    cancellation_time: Optional[str] = None
    cancellation_fee: Optional[Money] = None


class OfficialEvent(_Base):
    timestamp: Optional[str] = None
    event_type: Optional[str] = None


class OfficialTelemetry(_Base):
    timestamp: Optional[str] = None
    status: Optional[str] = None


class OfficialPolicy(_Base):
    free_wait_time_min: Optional[Money] = None
    no_show_threshold_min: Optional[Money] = None
    cancellation_fee_after_wait: Optional[Money] = None


class OfficialTicket(_Base):
    """Validate external types before the adapter can lose missing/invalid values."""

    dispute_ticket: OfficialDisputeTicket
    rider_profile: OfficialProfile = Field(default_factory=OfficialProfile)
    driver_profile: OfficialProfile = Field(default_factory=OfficialProfile)
    trip_data: OfficialTrip = Field(default_factory=OfficialTrip)
    gps_telemetry: list[OfficialTelemetry] = Field(default_factory=list)
    chat_logs: list[ChatMessage] = Field(default_factory=list)
    app_events: list[OfficialEvent] = Field(default_factory=list)
    cancellation_policy: OfficialPolicy = Field(default_factory=OfficialPolicy)
