"""Tests for backend.core.policy (bugs #2, #3, #4, #5 + regression)."""

from __future__ import annotations

import pytest

from backend.core.evidence import EvidenceAnalysis, analyze_evidence
from backend.core.policy import (
    apply_policy,
    NO_ACTION,
    PARTIAL_REFUND,
    FULL_REFUND,
    ESCALATE,
    INSUFFICIENT_EVIDENCE,
)


def _route_decision(optimal, actual, policies, config, *, traffic=False, stops=None):
    dispute = {
        "category": "route_deviation",
        "trip": {
            "optimal_distance_km": optimal,
            "actual_distance_km": actual,
            "traffic_detected": traffic,
            "unexpected_stops": stops or [],
        },
        "fare": {
            "base_fare": 3.0,
            "distance_fare_actual": 10.0,
            "distance_fare_optimal": 8.0,
            "surge_multiplier": 1.0,
        },
        "gps": {},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }
    return apply_policy(analyze_evidence(dispute), policies, config)


# --- Bug #2: boundary classification ---------------------------------------


@pytest.mark.parametrize(
    "optimal,actual,expected_action",
    [
        (100.0, 104.99, NO_ACTION),        # 4.99% → within tolerance
        (100.0, 105.0, PARTIAL_REFUND),     # exactly 5% → RD-001.3
        (100.0, 114.99, PARTIAL_REFUND),    # 14.99% → RD-001.3
        (19.8, 22.77, PARTIAL_REFUND),      # exactly 15% → RD-001.4 (higher band)
    ],
)
def test_route_deviation_boundaries(optimal, actual, expected_action, policies, config):
    decision = _route_decision(optimal, actual, policies, config)
    assert decision.action == expected_action


def test_route_deviation_15_percent_uses_rd_001_4(policies, config):
    decision = _route_decision(19.8, 22.77, policies, config)
    assert "RD-001.4" in decision.matched_policy_ids
    assert "RD-001.3" not in decision.matched_policy_ids


def test_route_deviation_5_percent_uses_rd_001_3(policies, config):
    decision = _route_decision(100.0, 105.0, policies, config)
    assert "RD-001.3" in decision.matched_policy_ids


# --- Bug #3: missing evidence escalates, never refunds ---------------------


def test_missing_no_show_arrival_escalates(policies, config):
    dispute = {
        "category": "no_show",
        "trip": {},
        "gps": {},
        "fare": {"cancellation_fee": 5.0},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }
    decision = apply_policy(analyze_evidence(dispute), policies, config)
    assert decision.action == INSUFFICIENT_EVIDENCE
    assert decision.escalate is True
    assert "closest_distance_to_pickup_m" in decision.explanation


def test_missing_optimal_distance_escalates(policies, config):
    dispute = {
        "category": "route_deviation",
        "trip": {"actual_distance_km": 10},
        "fare": {},
        "gps": {},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }
    decision = apply_policy(analyze_evidence(dispute), policies, config)
    assert decision.action == INSUFFICIENT_EVIDENCE
    assert decision.escalate is True


# --- Bug #4: NS-001.5 requires documented contact attempts -----------------


def test_no_show_no_contact_attempts_escalates(policies, config):
    dispute = {
        "category": "no_show",
        "trip": {},
        "gps": {"driver_arrival": {"closest_distance_to_pickup_m": 45, "wait_time_min": 6, "late_min": 1}},
        "fare": {"cancellation_fee": 5.0},
        "chat_log": [],  # no driver contact attempts
        "rider": {},
        "driver": {},
    }
    decision = apply_policy(analyze_evidence(dispute), policies, config)
    assert decision.action == ESCALATE
    assert "contact attempts not documented" in decision.explanation


def test_no_show_with_contact_attempts_upheld(policies, config):
    dispute = {
        "category": "no_show",
        "trip": {},
        "gps": {"driver_arrival": {"closest_distance_to_pickup_m": 45, "wait_time_min": 6, "late_min": 1}},
        "fare": {"cancellation_fee": 5.0},
        "chat_log": [{"from": "driver", "text": "I'm at the pickup point."}],
        "rider": {},
        "driver": {},
    }
    decision = apply_policy(analyze_evidence(dispute), policies, config)
    assert decision.action == NO_ACTION


# --- Bug #5: traffic does not blindly void refunds -------------------------


def test_traffic_within_tolerance_voids_refund(policies, config):
    decision = _route_decision(100.0, 120.0, policies, config, traffic=True)  # 20% ≤ 30%
    assert decision.action == NO_ACTION


def test_traffic_above_tolerance_escalates(policies, config):
    decision = _route_decision(100.0, 145.0, policies, config, traffic=True)  # 45% > 30%
    assert decision.action == ESCALATE
    assert "Conflicting evidence" in decision.explanation


def test_traffic_with_stop_still_applies_stop_clause(policies, config):
    decision = _route_decision(
        100.0, 110.0, policies, config, traffic=True, stops=[{"dwell_min": 5.0}]
    )
    assert decision.action == PARTIAL_REFUND
    assert "RD-001.4" in decision.matched_policy_ids


def test_traffic_tolerance_is_configurable(policies):
    config_low = {"traffic_tolerance": 0.10}
    # 20% deviation > 10% tolerance → escalate even with traffic.
    decision = _route_decision(100.0, 120.0, policies, config_low, traffic=True)
    assert decision.action == ESCALATE


# --- Regression: three original cases -------------------------------------


@pytest.mark.parametrize(
    "case_id,expected_action,expected_amount",
    [
        ("RYDE-2026-0001", PARTIAL_REFUND, 7.87),
        ("RYDE-2026-0002", FULL_REFUND, 5.00),
        ("RYDE-2026-0003", NO_ACTION, 0.0),
    ],
)
def test_original_cases_unchanged(case_id, expected_action, expected_amount, disputes, policies, config):
    case = next(d for d in disputes if d["case_id"] == case_id)
    decision = apply_policy(analyze_evidence(case), policies, config)
    assert decision.action == expected_action
    assert decision.amount == expected_amount
