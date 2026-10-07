"""Tests for backend.core.evidence (bugs #1, #2, #3, #6)."""

from __future__ import annotations

import pytest

from backend.core.evidence import analyze_evidence


def _route_case(optimal, actual, **kwargs):
    base = {
        "category": "route_deviation",
        "trip": {
            "optimal_distance_km": optimal,
            "actual_distance_km": actual,
            "traffic_detected": False,
            "unexpected_stops": [],
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
    base["trip"].update(kwargs)
    return base


# --- Bug #1: no crash on missing/zero data ---------------------------------


def test_route_deviation_missing_trip_does_not_crash():
    dispute = {"category": "route_deviation", "rider": {"claim": "x"}, "driver": {"response": "y"}}
    result = analyze_evidence(dispute)
    assert result.deviation_ratio is None
    assert "trip.optimal_distance_km" in result.gaps
    assert "trip.actual_distance_km" in result.gaps


def test_route_deviation_zero_optimal_distance_does_not_crash():
    result = analyze_evidence(_route_case(0, 10))
    assert result.deviation_ratio is None
    assert "trip.optimal_distance_km" in result.gaps


def test_route_deviation_non_numeric_distance_does_not_crash():
    result = analyze_evidence(_route_case("abc", "xyz"))
    assert result.deviation_ratio is None
    assert "trip.optimal_distance_km" in result.gaps


# --- Bug #2: float boundary rounding ---------------------------------------


@pytest.mark.parametrize(
    "optimal,actual,expected_ratio",
    [
        (19.8, 20.79, 0.05),     # exactly 5%
        (19.8, 22.77, 0.15),     # exactly 15%
        (100.0, 104.99, 0.0499),  # just under 5%
        (100.0, 114.99, 0.1499),  # just under 15%
    ],
)
def test_deviation_ratio_rounded_to_4_decimals(optimal, actual, expected_ratio):
    result = analyze_evidence(_route_case(optimal, actual))
    assert result.deviation_ratio == expected_ratio


# --- Bug #3: missing no-show data is a gap, not "did not arrive" -----------


def test_no_show_missing_arrival_is_gap_not_refund():
    dispute = {
        "category": "no_show",
        "trip": {},
        "gps": {},
        "fare": {"cancellation_fee": 5.0},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }
    result = analyze_evidence(dispute)
    assert result.driver_arrived is None  # NOT False
    assert "gps.driver_arrival.closest_distance_to_pickup_m" in result.gaps
    assert "gps.driver_arrival.wait_time_min" in result.gaps


def test_no_show_missing_wait_time_is_gap():
    dispute = {
        "category": "no_show",
        "trip": {},
        "gps": {"driver_arrival": {"closest_distance_to_pickup_m": 40}},
        "fare": {"cancellation_fee": 5.0},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }
    result = analyze_evidence(dispute)
    assert result.driver_arrived is True
    assert "gps.driver_arrival.wait_time_min" in result.gaps


def test_no_show_present_data_is_not_gap():
    dispute = {
        "category": "no_show",
        "trip": {},
        "gps": {"driver_arrival": {"closest_distance_to_pickup_m": 45, "wait_time_min": 6, "late_min": 1}},
        "fare": {"cancellation_fee": 5.0},
        "chat_log": [],
        "rider": {},
        "driver": {},
    }
    result = analyze_evidence(dispute)
    assert result.gaps == []
    assert result.driver_arrived is True


# --- Bug #6: stop disclosure is computed from chat, never assumed ----------


def test_driver_stop_disclosure_false_when_replied_after_rider_asked():
    # Mirrors RYDE-2026-0001: rider asks first, driver replies after.
    dispute = _route_case(19.8, 28.4)
    dispute["trip"]["unexpected_stops"] = [{"dwell_min": 6.2}]
    dispute["chat_log"] = [
        {"ts": "08:48", "from": "rider", "text": "We've stopped. Everything ok?"},
        {"ts": "08:54", "from": "driver", "text": "Quick break, sorry."},
    ]
    result = analyze_evidence(dispute)
    assert result.driver_disclosed_stop is False
    assert result.driver_stop_mentions == 1


def test_driver_stop_disclosure_true_when_proactive():
    dispute = _route_case(19.8, 28.4)
    dispute["trip"]["unexpected_stops"] = [{"dwell_min": 6.2}]
    dispute["chat_log"] = [
        {"ts": "08:40", "from": "driver", "text": "Need a quick toilet break, sorry."},
        {"ts": "08:48", "from": "rider", "text": "Why are we stopped?"},
    ]
    result = analyze_evidence(dispute)
    assert result.driver_disclosed_stop is True
