# Adapters — official ticket format

`official_ticket.py` normalises the organiser's official dispute-ticket format
(top-level `dispute_ticket` key) into our internal dispute dict.

## Mapping table

| Official field | Internal field | Notes |
|---|---|---|
| `dispute_ticket.dispute_id` | `case_id` | falls back to `trip_id` |
| `dispute_ticket.dispute_type` | `category` | via `{"no_show_charge": "no_show"}`; unknown type → `category` = raw value → escalated |
| `dispute_ticket.description` | `rider.claim` | |
| `rider_profile` / `driver_profile` | `rider` / `driver` | `total_trips` → `trips_completed`; `dispute_history.total_disputes` → `dispute_history` (int) |
| `*.fraud_flags` + `fraud_flag_details` | `*.fraud_flags_list` | becomes a fraud flag |
| `dispute_history` `{total_disputes, upheld\|upheld_against, rejected}` | fraud flag | `total >= 3` and `rejected/total >= 0.5` → `"high rate of rejected disputes"` |
| `app_events` (`driver_arrived`) | `gps.driver_arrival.arrived` | else derived from `gps_telemetry` status `arrived`/`waiting` |
| `trip_data.cancellation_time` − (`driver_wait_start` \|\| `driver_arrival_time`) | `gps.driver_arrival.wait_time_min` | minutes |
| `max(0, arrival − scheduled_time)` | `gps.driver_arrival.late_min` | minutes |
| `chat_logs` (`sender`/`type`/`content`/`timestamp`) | `chat_log` (`from`/`type`/`text`/`ts`) | `system` never counts as a contact attempt |
| `chat_logs` `type == "call"` | `driver_call_attempts` | counted by the evidence engine |
| `trip_data.cancellation_fee` | `fare.cancellation_fee` | |
| `cancellation_policy` | `cancellation_policy_override` | per-case thresholds; never mutates global config |
| `app_events` | `raw_app_events` | kept verbatim in the response |
