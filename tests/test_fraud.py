"""Tests for the Fraud & Bad-Faith agent (bug #7)."""

from __future__ import annotations

from backend.agents.fraud_detection import FraudDetectionAgent
from backend.core.evidence import analyze_evidence


def test_high_volume_driver_is_not_medium_risk():
    # 2 disputes over 3,410 trips is a very low rate → low risk, not medium.
    risk = FraudDetectionAgent._score(dispute_history=2, trips=3410, account_age=720)
    assert risk < 0.2


def test_rate_based_high_risk():
    # 3 disputes over 30 trips = 10% rate → high.
    risk = FraudDetectionAgent._score(dispute_history=3, trips=30, account_age=400)
    assert risk >= 0.6


def test_insufficient_sample_uses_bounded_penalty():
    risk = FraudDetectionAgent._score(dispute_history=2, trips=5, account_age=500)
    # Small sample should not explode the score; stays modest.
    assert 0.0 <= risk <= 0.5


def test_analyze_returns_per_party_risk():
    dispute = {
        "category": "no_show",
        "trip": {},
        "gps": {"driver_arrival": {"closest_distance_to_pickup_m": 40, "wait_time_min": 2, "late_min": 3}},
        "fare": {"cancellation_fee": 5.0},
        "chat_log": [],
        "rider": {"dispute_history": 0, "trips_completed": 100, "account_age_days": 300},
        "driver": {"dispute_history": 2, "trips_completed": 3410, "account_age_days": 720},
    }
    evidence = analyze_evidence(dispute)
    result = FraudDetectionAgent().analyze(dispute, evidence)
    assert "rider_risk" in result
    assert "driver_risk" in result
    # No party-agnostic "overall" penalty field is consumed by the Judge anymore.
    assert result["driver_risk"] < 0.2
