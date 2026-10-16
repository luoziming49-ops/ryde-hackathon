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
| `app_events` (`driver_arrived`) | `gps.driver_arrival.arrived` | else derived from `gps_telemetry` status `arrived`/`waiting`, then validated GPS distance coverage |
| `trip_data.cancellation_time` − (`driver_wait_start` \|\| `driver_arrival_time` \|\| derived arrival) | `gps.driver_arrival.wait_time_min` | minutes; missing fields fall back, invalid supplied values do not |
| `max(0, arrival − scheduled_time)` | `gps.driver_arrival.late_min` | minutes |
| `chat_logs` (`sender`/`type`/`content`/`timestamp`) | `chat_log` (`from`/`type`/`text`/`ts`) | `system` never counts as a contact attempt |
| `chat_logs` `type == "call"` | `driver_call_attempts` | counted by the evidence engine |
| `trip_data.cancellation_fee` | `fare.cancellation_fee` | missing stays missing; explicit zero is valid |
| `cancellation_policy` | `cancellation_policy_override` | per-case thresholds; never mutates global config |
| `app_events` | `raw_app_events` | kept verbatim in the response |

External nested types and numeric inputs are validated before conversion, then
the result is validated as an internal dispute. Invalid shapes and negative or
non-finite fees produce HTTP 422, including when loading an official sample.

Time comparisons respect supplied UTC offsets; local and timezone-aware clocks
cannot be compared. Arrival records from the trip, arrival events and `arrived`
telemetry must agree. Later `waiting` telemetry is not another arrival. Missing
or invalid clocks, conflicting arrivals, waiting before arrival, or cancellation
before waiting add `normalization_gaps`, which the evidence and policy engines
carry into `insufficient_evidence` with null amount/confidence. Unreliable wait
and lateness values remain unknown. No timezone or zero duration is invented.
Waiting observations after cancellation, or a cancelled status before the trip's
cancellation time, are also conflicts. A later cancelled observation need not
have the exact cancellation timestamp. ISO `Z` timestamps are normalized to
`+00:00` for Python 3.10 compatibility.

## S1b GPS-only arrival integration

When no arrival event or arrival/waiting status exists, the adapter computes
Haversine distance from pickup using a 150 m arrival radius. Every telemetry
point must have valid finite latitude/longitude within geographic bounds and a
valid timestamp comparable to the known cancellation time. Pickup coordinates
must also be valid. There must be an observation before cancellation and one at
or after cancellation. Equivalent UTC offsets remain comparable.

A point within 150 m at or before cancellation establishes arrival at the earliest
such observation. Post-cancellation points cannot establish arrival. If all
observations are farther away, the recorded coverage supports nonarrival; this
is an inference from sampled telemetry, not proof of the driver's continuous
trajectory. A nearby point observed only after cancellation leaves arrival
unknown. Incomplete coverage, invalid coordinates/clocks and contradictory
cancelled-status chronology add normalization gaps. Inconclusive cases expose no
closest-distance field, preventing downstream distance fallback from treating an
unknown arrival as a definite boolean. Supplied arrival/wait timestamps that
contradict GPS nonarrival also escalate.

Confirmed nonarrival leaves wait and lateness unknown: those values are not
needed by NS-001.2, but the cancellation fee is required for its refund amount.
Existing strict arrival-source and chronology comparisons remain in place for
arrived cases. Coordinate problems become explicit evidence gaps; existing
schema rejection of invalid or non-finite monetary values is unchanged.

S1b compatibility choices retained from WB01: absent/null fees remain missing
(the normalized dictionary omits `None`); a no-action ruling does not need a
refund amount; conflicting arrival clocks are reported through
`normalization_gaps` / evidence `gaps`, not a separate `conflicts` field. Imported
S1b tests were adjusted only for those three contracts; never-arrived refund
assertions remain intact.
