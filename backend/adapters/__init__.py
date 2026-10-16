"""Adapter for the organiser's official dispute-ticket format."""

from .official_ticket import normalize_official_ticket, is_official_ticket

__all__ = ["normalize_official_ticket", "is_official_ticket"]
