"""Output contracts; input schemas intentionally remain in schemas.py."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Action = Literal["no_action", "partial_refund", "full_refund", "compensation", "escalate", "insufficient_evidence"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EvidenceItem(Contract):
    id: str
    case_id: str
    source: str
    source_path: str
    version: str
    value: Any
    text: str
    kind: Literal["derived", "reported"]
    observed_at: str | None = None
    is_simulated: bool | None = None


class Claim(Contract):
    text: str = Field(max_length=4000)
    evidence_ids: list[str] = Field(min_length=1, max_length=1)
    policy_ids: list[str] = Field(max_length=12)


class AgentClaim(Contract):
    party: Literal["rider", "driver", "judge"]
    claims: list[Claim] = Field(max_length=8)
    missing_evidence: list[str] = Field(max_length=64)
    proposed_action: Action


class LLMResult(Contract):
    value: dict
    mode: Literal["llm", "fallback"]
    status: Literal["ok", "no_key", "error", "rejected"]
    model: str | None = None
    prompt_version: str
    latency_ms: int = Field(ge=0)
    error_code: str | None = None
    attempts: int = Field(ge=0)
    attempt_errors: list[str] = Field(default_factory=list)
    # Known provider-reported counts; incomplete counts are only a lower bound.
    usage: dict[str, int] | None = None
    usage_complete: bool = False
    is_simulated: bool = False
    scenario: str | None = None

    def metadata(self) -> dict:
        return self.model_dump(exclude={"value"})


class GuardResult(Contract):
    status: Literal["approved", "rejected"]
    reasons: list[str]
    final_action: Action
    final_amount: float | None
    policy_version: str
    evidence_ids: list[str]
