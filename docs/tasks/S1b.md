# Task S1b — three follow-up fixes from the S1 review

Branch: stay on feat/S1-robustness-official and add a new commit. Use the repo's .venv. Write a failing test first for each item, then fix. Canonical outcomes must not change (0001 partial_refund 7.87, 0002 full_refund 5.00, 0003 no_action, DISP-002 no_action).

The reviewer reproduced each issue with POST /api/resolve.

1. **Null money fields are silently treated as 0.**
   - Internal format: `fare.base_fare = null` on RYDE-2026-0001 gives partial_refund 6.37 (should not silently change the amount).
   - Internal format: `fare.cancellation_fee = null` on RYDE-2026-0002 gives `full_refund` with amount 0.0.
   - Official format: `backend/adapters/official_ticket.py` does `_to_float(trip.get("cancellation_fee")) or 0.0` and hard-codes `"base_fare": 0.0`.
   Fix: a money field that the decisive rule needs (base_fare and distance fares for route_deviation; cancellation_fee for no_show) and that is null/missing becomes an evidence gap -> insufficient_evidence, escalated. Do not invent 0.0 in the adapter; leave it missing. A genuine 0 is still a valid value.

2. **"Driver never arrived" is reported as insufficient evidence.** In an official ticket with gps_telemetry present but no `driver_arrived` event and no telemetry point with status "arrived"/"waiting", the driver clearly never reached the pickup, yet the ruling is insufficient_evidence. Fix `_derive_arrival`:
   - If there is a `driver_arrived` event or an arrived/waiting telemetry point -> arrived = True.
   - Else, if telemetry exists, compute the haversine distance from each telemetry point to `trip_data.pickup_location` (lat/lng). If the closest point is > 150 m (use the same 150 m threshold as policy NS-001.1/NS-001.2) and the telemetry covers the time up to cancellation_time -> arrived = False, and also pass the closest distance in metres as `closest_distance_to_pickup_m`. Closest point <= 150 m -> arrived = True.
   - Only when there is no telemetry and no events -> arrived unknown (gap).
   Expected: such a ticket resolves to full_refund of the cancellation fee under NS-001.2, not escalated.

3. **Two different sources for arrival time, no conflict check.** Wait time uses `trip_data.driver_wait_start / driver_arrival_time`, while lateness uses the `driver_arrived` event time. Use one resolved arrival time for both. If `trip_data.driver_arrival_time` and the event time differ by more than 2 minutes, record an evidence conflict ("arrival time conflict: trip_data X vs app_events Y") and escalate instead of silently picking one. Also: if `scheduled_time` is missing, lateness is unknown (a gap only when the decision depends on it), not 0.

Add the new behaviours to the mapping table in backend/adapters/README.md.

Run `python -m pytest`, commit, do not push. REPORT: one row per item with test names and real output, plus the final DISP-002 ruling.
