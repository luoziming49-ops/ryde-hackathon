"""Base agent and shared reasoning helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any

from ..core.llm import get_llm
from ..contracts import AgentClaim, LLMResult
from ..core.guard import fallback_claim, validate_claim
from ..core.prompts import render_prompt


@dataclass
class AgentMessage:
    """One observable communication step emitted by an agent."""

    agent: str
    role: str  # e.g. "gather", "argue", "deliberate", "rule", "log"
    content: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseAgent:
    name: str = "Agent"
    description: str = ""

    def __init__(self, llm=None, event_sink=None):
        self.llm = llm or get_llm()
        self.trace: list[AgentMessage] = []
        self.event_sink = event_sink

    def emit(self, role: str, content: str, **meta) -> AgentMessage:
        msg = AgentMessage(agent=self.name, role=role, content=content, meta=meta)
        self.trace.append(msg)
        if self.event_sink:
            self.event_sink(msg)
        return msg

    def llm_or(self, system: str, user: str, fallback: str, *, temperature: float = 0.3) -> str:
        """Return LLM narrative or a deterministic fallback."""
        return self.llm.complete(system, user, temperature=temperature, fallback=fallback)

    def grounded_result(self, party, catalog, policy_ids, missing, action, *, context=None) -> LLMResult:
        expected = action if party == "judge" else None
        def validate(data):
            return validate_claim(data, party=party, catalog=catalog, policy_ids=policy_ids,
                                  missing_evidence=missing, expected_action=expected)
        fallback = validate(fallback_claim(party, catalog, policy_ids, missing, action))
        data = {"party": party, "catalog": [item.model_dump() for item in catalog],
                "allowed_policy_ids": sorted(policy_ids), "missing_evidence": missing,
                "expected_action": expected, **(context or {})}
        system, user, version = render_prompt(party, data, AgentClaim.model_json_schema())
        return self.llm.complete_structured(system, user, fallback=fallback, validate=validate,
                                            prompt_version=version, max_retries=1)


def format_money(amount: float, currency: str = "SGD") -> str:
    return f"{currency} {amount:.2f}"


def bulletize(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


def to_json(text: str, fallback: dict) -> dict:
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return fallback
