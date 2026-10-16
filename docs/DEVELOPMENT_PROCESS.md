# Development process — how we built Ryde Dispute AI with WorkBuddy

This is the written development-process description accepted by the handbook as proof of product usage. Every step below can be checked against the git history of this repository and the task specs in `docs/tasks/`.

## Roles

- **WorkBuddy** (model: DeepSeek-V4-Pro) — the coding agent. It wrote the prototype and every code change, ran the tests and reported real command output.
- **Team** — wrote the task specifications, reviewed every WorkBuddy report against the actual code (re-running tests and probing edge cases), and decided what to fix next.
- **Claude (Anthropic)** — used by the team as a reviewing assistant: drafting task specs, independently reproducing bugs, and drafting submission text. It did not replace WorkBuddy as the builder.

## Working loop

1. Write a task spec (`docs/tasks/S*.md`) listing concrete, reproduced problems and the tests that must prove each fix.
2. Send WorkBuddy a one-line instruction: *"read docs/tasks/SX.md and do exactly what it says, then reply with the REPORT it asks for."*
3. WorkBuddy writes failing tests first, fixes the code, runs the full test suite, commits on a feature branch and returns a report with real outputs.
4. The team re-runs the tests and probes edge cases independently; anything still wrong becomes the next task spec.

## Timeline

| Date | Step | Result |
|---|---|---|
| Sep 20 | **V1** — WorkBuddy built the first prototype from the handbook challenge: FastAPI backend, Rider Advocate / Driver Advocate / Judge agents, evidence + policy engines, fraud and precedent agents, single-page UI, 3 sample cases | Ran end-to-end. Review found it crashed on incomplete input, treated missing data as "driver never arrived", had float boundary errors at exactly 5%/15%, and an advocate claimed facts not in the evidence |
| Sep 20 | **V2 / P1** — WorkBuddy fixed 10 reproduced bugs test-first and added the first test suite | 51 tests passing |
| Oct 7 | **S0** (commit `a5cc5a0`) — WorkBuddy imported V2 into this team repo, updated the project rules, verified tests and API | 51 tests; canonical rulings unchanged |
| Oct 7 | **S1** (`6d7ad6d`) — typed input validation (no more HTTP 500s), `.env` loader, precise stop-disclosure detection, and an **adapter for the organiser's official ticket format** (DISP-002) | 79 tests; DISP-002 → fee upheld, matching the organiser's expected ruling |
| Oct 12 | **S1b** (`449ccea`) — missing money fields become evidence gaps instead of 0; "driver never arrived" derived from GPS telemetry (haversine distance to pickup); conflicting arrival times escalate | 91 tests |
| Oct 12 | **S1c** (`68b575a`) — malformed official tickets return 422; negative/NaN money rejected; frontend null-safety and error handling | 106 tests |

Code produced through this process: 35 files and about 4,600 lines in `backend/`, `frontend/`, `tests/` and `sample_data/`.

## Examples of the review loop catching real problems

- An advocate stated "the stop was communicated to the rider via chat" although the driver only replied after the rider asked → stop disclosure is now computed from the chat log with word-boundary matching and parsed timestamps.
- The organiser's official sample had no arrival-distance field, so the first version escalated it as "insufficient evidence" → WorkBuddy built the official-format adapter, and the ruling now matches the organiser's expected answer.
- A null cancellation fee produced "full refund of SGD 0.00" → missing money now escalates to a human.

## Prompt usage

The engineering rules WorkBuddy followed are in `PROJECT_RULES.md`; every task prompt is kept verbatim in `docs/tasks/`. Inside the product, each agent (Rider Advocate, Driver Advocate, Judge) has a role prompt that limits it to the computed evidence and policy clauses.
