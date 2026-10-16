"""Run the page's real JavaScript functions with DOM/network boundaries doubled.

This is a fast behavior regression suite, not a substitute for browser QA.
No HTTP requests or model calls leave the Node VM.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from backend.adapters.official_ticket import normalize_official_ticket


ROOT = Path(__file__).resolve().parent.parent
NODE = os.environ.get("RYDE_NODE") or shutil.which("node")
if not NODE:
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
    NODE = str(bundled) if bundled.is_file() else None


def run_behavior(scenario, data=None):
    if not NODE:
        pytest.skip("Node.js is required for frontend behavior tests (set RYDE_NODE)")
    result = subprocess.run(
        [NODE, str(ROOT / "tests/frontend_behavior.cjs"), scenario],
        input=json.dumps(data), text=True, capture_output=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_official_case_all_evidence_tabs():
    ticket = json.loads((ROOT / "sample_data/official/DISP-002.json").read_text())
    run_behavior("official_tabs", normalize_official_ticket(ticket))


@pytest.mark.parametrize("scenario", [
    "simulation_rerun", "simulation_case_failure", "simulation_event_escape",
    "simulation_metadata", "simulation_poll", "simulation_failure_retry",
    "simulation_stale_run", "simulation_stale_post", "simulation_stale_case", "simulation_references",
    "fare_missing_and_zero", "gps_missing_fields", "gps_route_without_endpoints",
    "escape_numeric_and_null", "escape_evidence", "resolve_http_error",
    "resolve_validation_error", "resolve_plain_http_error", "resolve_health_refresh",
    "resolve_health_unavailable", "architecture_states", "trace_replay",
    "agents_mixed_modes", "agents_unknown_legacy", "agents_fallback_reasons",
    "agents_escape_metadata", "guard_approved", "guard_rejected", "guard_escape",
    "trace_agent_result", "resolve_clear_agent_result",
    "live_availability", "live_unavailable", "live_poll", "live_fallback",
    "live_unknown_agents", "live_guard_rejected", "live_wrong_mode",
    "live_stale_post", "live_stale_poll", "live_stale_health", "live_switch_loading_case",
    "live_usage", "live_failure_retry", "live_startup_health_failure", "live_stale_simulation",
    "consent_input_statements", "consent_missing_statements", "consent_original_text",
    "consent_result_consistent_agreed", "consent_result_consistent_not_agreed",
    "consent_result_conflicting", "consent_result_unconfirmed", "consent_result_legacy",
    "review_questions_escape", "review_questions_absent", "review_flag_no_dispatch",
    "consent_no_show", "gps_input_provenance",
])
def test_frontend_behavior(scenario):
    run_behavior(scenario)
