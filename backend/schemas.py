"""Pydantic request models for the API layer."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ResolveRequest(BaseModel):
    """Body for POST /api/resolve.

    Provide either a `case_id` to resolve a known sample case, or a complete
    inline dispute. An inline dispute requires `category`, `rider` and
    `driver`; everything else is optional and missing fields are surfaced as
    evidence gaps (never as crashes).
    """

    case_id: Optional[str] = None
    category: Optional[str] = None
    rider: Optional[dict] = None
    driver: Optional[dict] = None
    trip: Optional[dict] = None
    gps: Optional[dict] = None
    fare: Optional[dict] = None
    chat_log: Optional[list] = Field(default_factory=list)
    priority: Optional[str] = "standard"
    status: Optional[str] = "pending"
    filed_at: Optional[str] = None

    def to_inline_dispute(self) -> dict:
        """Convert to a dispute dict, dropping None-valued fields."""
        data = {
            "category": self.category,
            "rider": self.rider or {},
            "driver": self.driver or {},
            "trip": self.trip or {},
            "gps": self.gps or {},
            "fare": self.fare or {},
            "chat_log": self.chat_log or [],
            "priority": self.priority or "standard",
            "status": self.status or "pending",
        }
        if self.filed_at:
            data["filed_at"] = self.filed_at
        return data
