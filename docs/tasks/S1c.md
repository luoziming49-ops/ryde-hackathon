# Task S1c — last robustness gaps (small)

Branch: stay on feat/S1-robustness-official (S1 + S1b already committed there) and add one commit. Use the repo's .venv. Force LLM_API_KEY and OPENAI_API_KEY to empty strings in the test process. Write a failing test first for each item, then fix. Canonical outcomes unchanged (0001 partial_refund 7.87, 0002 full_refund 5.00, 0003 no_action, DISP-002 no_action).

The reviewer reproduced each issue on the current branch:

1. Malformed official tickets return HTTP 500: `{"dispute_ticket": "broken"}`, and DISP-002 with `"chat_logs": "x"`. Validate the official shape with pydantic (dispute_ticket / trip_data / profiles must be objects; chat_logs / app_events / gps_telemetry must be lists of objects) before normalising; invalid -> HTTP 422 JSON with a clear message.
2. Invalid money values are accepted: DISP-002 with `trip_data.cancellation_fee = -5` or `"NaN"` returns 200. Negative, NaN or Infinity money values (both formats) -> 422. Missing/null keeps the S1b behaviour (evidence gap), and an explicit 0 stays valid.
3. Frontend crashes on the official case: `frontend/index.html` calls `.toFixed()` on fare fields that are undefined/null for DISP-002 (fare tab), and the GPS tab assumes route data. Show "not provided" for missing values, "0.00" for real zeros.
4. Frontend treats an error response as a success: check `response.ok` before rendering the trace; on error show the message and re-enable the button.

Then open the page in a browser, click all four cases and every evidence tab, run Resolve on each, and report any console error. If you cannot use a browser, say "browser not verified".

Run the full test suite, commit, do not push. REPORT: one row per item with test names and real output.
