"""Local response generation through the normal schema, citation and retry checks.

This is a deterministic simulation of provider responses, not an external model.
It reads the same nonce-delimited prompt data as a model would receive; fallback
values are never used to construct successful simulated responses.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from backend.contracts import LLMResult
from .llm import LLMConfig, LLMProvider


SCENARIOS = {
    "success": "All agents succeed",
    "rider_rejected": "Rider citation rejected twice",
    "retry_success": "Rider JSON repaired on retry",
    "provider_error": "Rider provider error with fallback",
}


class SimulationProvider(LLMProvider):
    """An entirely local transport, independent of environment credentials.

    Instances should belong to one run. Retry position is derived exclusively
    from that invocation's messages, so reuse and concurrent calls cannot share
    a mutable attempt counter.
    """

    def __init__(self, scenario: str = "success"):
        if scenario not in SCENARIOS:
            raise ValueError("unknown_simulation_scenario")
        super().__init__(LLMConfig(base_url="local://simulation", api_key="", model="local-simulation"))
        self.scenario = scenario
        # The inherited validator needs an available transport, even if the
        # optional requests package is absent. This transport never uses it.
        self.llm_configured = self.available = True

    def complete_structured(
        self, system: str, user: str, *, fallback: dict,
        validate: Callable[[dict], dict], prompt_version: str, max_retries: int = 1,
    ) -> LLMResult:
        result = super().complete_structured(
            system, user, fallback=fallback, validate=validate,
            prompt_version=prompt_version, max_retries=max_retries,
        )
        return result.model_copy(update={"is_simulated": True, "scenario": self.scenario})

    def _request(self, messages: list[dict], *, temperature: float, max_tokens: int) -> str:
        # Match the entire outer envelope; strings embedded inside JSON remain
        # inert data, including fake closing markers or retry instructions.
        envelope = re.fullmatch(r"<DATA_([0-9a-f]{32})>\n(.*)\n</DATA_\1>",
                                messages[1]["content"], flags=re.DOTALL)
        if envelope is None:
            raise ValueError("invalid_simulation_prompt")
        data = json.loads(envelope.group(2))
        party = data["party"]
        if party not in ("rider", "driver", "judge"):
            raise ValueError("invalid_simulation_party")

        if party == "rider":
            if self.scenario == "provider_error":
                raise RuntimeError("simulated_provider_error")
            if self.scenario == "retry_success" and len(messages) == 2:
                return "{invalid simulated JSON"

        catalog = data["catalog"]
        selected = [item for item in catalog if item["kind"] == "derived"]
        if party != "judge":
            own_path = "rider.claim" if party == "rider" else "driver.response"
            selected = [item for item in catalog if item["kind"] == "reported"
                        and item["source_path"] == own_path] + selected
        allowed = set(data["allowed_policy_ids"])
        policy_ids = sorted({rule["id"] for rule in data.get("policy_context", {}).get("matched_rules", [])
                             if rule["id"] in allowed})[:12]
        category = next((item["value"] for item in catalog
                         if item["source_path"] == "analysis.category"), None)
        if party == "judge":
            action = data["expected_action"]
        elif category in ("route_deviation", "no_show"):
            action = "full_refund" if party == "rider" else "no_action"
        else:
            action = "escalate"
        claims = [{"text": item["text"], "evidence_ids": [item["id"]], "policy_ids": policy_ids}
                  for item in selected[:8]]
        if party == "rider" and self.scenario == "rider_rejected":
            # A syntactically valid claim with a guaranteed absent reference
            # exercises the real citation validator on both attempts.
            bad_id = "simulated-unknown-evidence"
            ids = {item["id"] for item in catalog}
            while bad_id in ids:
                bad_id += "-unknown"
            claims = [{"text": selected[0]["text"] if selected else "No evidence selected.",
                       "evidence_ids": [bad_id], "policy_ids": policy_ids}]
        return json.dumps({"party": party, "claims": claims,
                           "missing_evidence": list(dict.fromkeys(data["missing_evidence"]))[:64],
                           "proposed_action": action}, ensure_ascii=False, allow_nan=False)
