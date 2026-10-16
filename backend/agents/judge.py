"""Judge Agent for the hackathon demo.

Applies the local demonstration rules and escalation checks, then selects
catalog evidence for a controlled explanation. Party reports remain reports;
the model neither verifies oral consent nor controls the monetary calculation.
"""

from __future__ import annotations

from typing import Any

from ..core.evidence import EvidenceAnalysis
from ..core.policy import (
    PolicyDecision,
    apply_policy,
    ESCALATE,
    PARTIAL_REFUND,
    FULL_REFUND,
    COMPENSATION,
    INSUFFICIENT_EVIDENCE,
)
from .base import BaseAgent, format_money
from ..core.guard import build_evidence_catalog, build_policy_context, guard_result, policy_version

ESCALATION_THRESHOLD = 0.60


class JudgeAgent(BaseAgent):
    name = "Judge"
    description = "Impartial arbitrator issuing final rulings with confidence and reasoning."

    def __init__(self, policies: list[dict], config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.policies = policies
        self.config = config or {}

    def rule(
        self,
        dispute: dict,
        evidence: EvidenceAnalysis,
        rider_case: dict,
        driver_case: dict,
        fraud: dict | None = None,
        precedent: dict | None = None,
        *, catalog=None, decision: PolicyDecision | None = None,
    ) -> dict[str, Any]:
        # 1. Deterministic policy prior.
        if decision is None:
            decision = apply_policy(evidence, self.policies, self.config)
        amount_note = "amount unavailable" if decision.escalate else format_money(decision.amount)
        self.emit("deliberate", f"Applying policy prior: {decision.action} ({amount_note}).")

        # 2. Adjust confidence from per-party fraud risk (bug #7).
        confidence = decision.confidence
        adjustment_notes: list[str] = []
        if fraud:
            # Only the party who would *benefit* from the ruling is penalised.
            if decision.action in (PARTIAL_REFUND, FULL_REFUND, COMPENSATION):
                beneficiary = "rider"
            elif decision.action == "no_action":
                beneficiary = "driver"
            else:
                beneficiary = None
            if beneficiary and not decision.escalate:
                risk = fraud.get(f"{beneficiary}_risk", 0.0)
                if risk >= 0.6:
                    confidence -= 0.15
                    adjustment_notes.append(
                        f"High bad-faith risk ({risk:.2f}) for the benefiting party ({beneficiary}) reduces confidence."
                    )
                elif risk >= 0.3:
                    confidence -= 0.05
                    adjustment_notes.append(
                        f"Elevated bad-faith risk ({risk:.2f}) for the benefiting party ({beneficiary}) slightly reduces confidence."
                    )
            for flag in fraud.get("flags", []):
                adjustment_notes.append(f"Fraud flag: {flag}")

        # 3. Precedent agreement nudges confidence — but never on an escalated
        #    decision (bug: insufficient_evidence showed 0.03 confidence).
        if not decision.escalate:
            if precedent and precedent.get("precedents"):
                confidence = min(confidence + 0.03, 1.0)
                adjustment_notes.append("Consistent with prior precedent; confidence increased.")
            confidence = max(0.0, min(confidence, 1.0))

        # 4. Escalation. Preserve the *reason* (insufficient_evidence, safety,
        #    conflicting evidence) instead of flattening everything to "escalate".
        if decision.escalate:
            escalate = True
            action = decision.action
        elif confidence < ESCALATION_THRESHOLD:
            escalate = True
            action = ESCALATE
            adjustment_notes.append(
                f"Confidence {confidence:.2f} below threshold {ESCALATION_THRESHOLD}; flagged for human review. No support case has been dispatched."
            )
        else:
            escalate = False
            action = decision.action

        # Insufficient evidence has no meaningful confidence — report null.
        confidence_value = None if action == INSUFFICIENT_EVIDENCE else round(confidence, 3)

        ruling = {
            "action": action,
            "amount": decision.amount if not escalate else None,
            "currency": decision.currency,
            "confidence": confidence_value,
            "escalated": escalate,
            "matched_policy_ids": decision.matched_policy_ids,
            "missing_fields": decision.missing_fields,
            "review_questions": list(decision.review_questions),
            "reasoning_source": "verified_template",
            "adjustment_notes": adjustment_notes,
        }

        if catalog is None:
            catalog = build_evidence_catalog(dispute, evidence)
        version = policy_version(self.policies, self.config, dispute.get("cancellation_policy_override") or {})
        result = self.grounded_result(
            "judge", catalog, set(decision.matched_policy_ids), decision.missing_fields, action,
            context={"rider_case": rider_case.get("structured", {}),
                     "driver_case": driver_case.get("structured", {}),
                     "final_decision": {k: v for k, v in ruling.items() if k != "adjustment_notes"},
                     "policy_version": version,
                     "policy_context": build_policy_context(self.policies, self.config, dispute, evidence, decision)},
        )
        ruling["agent_output"] = result.value
        ruling["llm_result"] = result.metadata()
        ruling["guard"] = guard_result(result, ruling, version).model_dump()
        ruling["reasoning"] = self._verified_reasoning(ruling, decision, result.value, evidence)

        self.emit(
            "rule",
            self._verdict_line(ruling),
            action=action,
            amount=ruling["amount"],
            confidence=ruling["confidence"],
            escalated=escalate,
            llm=result.metadata(),
        )
        return ruling

    # ------------------------------------------------------------------ #
    @staticmethod
    def _fmt_conf(confidence) -> str:
        return "n/a" if confidence is None else f"{confidence:.0%}"

    def _verdict_line(self, ruling: dict) -> str:
        if ruling["escalated"]:
            return f"Flagged for human review ({ruling['action']}). No support case has been dispatched."
        action = ruling["action"].replace("_", " ").title()
        if ruling["amount"]:
            return f"Ruling: {action} of {format_money(ruling['amount'])} (confidence {self._fmt_conf(ruling['confidence'])})."
        return f"Ruling: {action} (confidence {self._fmt_conf(ruling['confidence'])})."

    def _verified_reasoning(self, ruling, decision, selected, evidence) -> str:
        if ruling["escalated"]:
            text = f"Flagged for human review ({ruling['action']}). No support case has been dispatched. No automatic payment has been applied."
            if ruling["missing_fields"]:
                text += " Missing or conflicting evidence: " + ", ".join(ruling["missing_fields"]) + "."
            elif decision.action == ruling["action"] and evidence.category in ("route_deviation", "no_show"):
                text += " " + decision.explanation
        else:
            text = (f"Final decision: {ruling['action'].replace('_', ' ')}. "
                    f"Amount: {format_money(ruling['amount'], ruling['currency'])}. " + decision.explanation)
        facts = " ".join(claim["text"] for claim in selected["claims"])
        if facts:
            text += " Selected evidence: " + facts
        if evidence.category == "no_show":
            threshold = evidence.free_wait_min if evidence.free_wait_min is not None else 5.0
            source = "case override" if evidence.free_wait_min is not None else "default policy"
            text += f" Effective free-wait threshold: {threshold:g} minutes ({source})."
        text += f" Overall confidence: {self._fmt_conf(ruling['confidence'])}."
        return text
