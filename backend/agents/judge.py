"""Judge Agent (core).

Impartial arbitrator: weighs both advocates' cases, applies company policy,
considers fraud signals and precedent, and issues a final ruling (refund /
compensation / no action) with a confidence score and a natural-language
explanation. Falls back to human escalation when confidence is low.
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
)
from .base import BaseAgent, format_money

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
    ) -> dict[str, Any]:
        # 1. Deterministic policy prior.
        decision: PolicyDecision = apply_policy(evidence, self.policies, self.config)
        self.emit("deliberate", f"Applying policy prior: {decision.action} ({format_money(decision.amount)}).")

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
            if beneficiary:
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

        # 3. Precedent agreement nudges confidence.
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
                f"Confidence {confidence:.2f} below threshold {ESCALATION_THRESHOLD}; escalating to human review."
            )
        else:
            escalate = False
            action = decision.action

        # 5. Natural-language reasoning (LLM if available, else template).
        reasoning = self._write_reasoning(
            dispute, evidence, decision, rider_case, driver_case, fraud, adjustment_notes, action, confidence
        )

        ruling = {
            "action": action,
            "amount": decision.amount if not escalate else None,
            "currency": decision.currency,
            "confidence": round(confidence, 3),
            "escalated": escalate,
            "matched_policy_ids": decision.matched_policy_ids,
            "reasoning": reasoning,
            "adjustment_notes": adjustment_notes,
        }

        self.emit(
            "rule",
            self._verdict_line(ruling),
            action=action,
            amount=ruling["amount"],
            confidence=ruling["confidence"],
            escalated=escalate,
        )
        return ruling

    # ------------------------------------------------------------------ #
    def _verdict_line(self, ruling: dict) -> str:
        if ruling["escalated"]:
            return f"Escalating to human review ({ruling['action']})."
        action = ruling["action"].replace("_", " ").title()
        if ruling["amount"]:
            return f"Ruling: {action} of {format_money(ruling['amount'])} (confidence {ruling['confidence']:.0%})."
        return f"Ruling: {action} (confidence {ruling['confidence']:.0%})."

    def _write_reasoning(
        self, dispute, evidence, decision, rider_case, driver_case, fraud, notes, action, confidence
    ) -> str:
        system = (
            "You are the Judge in a ride-hailing dispute. Weigh both advocates' arguments, "
            "apply policy, and write a fair, concise explanation of your ruling. "
            "Mention the key evidence that decided the outcome."
        )
        user = (
            f"Category: {dispute.get('category')}\n"
            f"Rider argument: {rider_case.get('argument')}\n"
            f"Driver argument: {driver_case.get('argument')}\n"
            f"Policy decision: {decision.action} {format_money(decision.amount)}\n"
            f"Confidence: {confidence:.2f}\n"
            f"Fraud/adjustment notes: {'; '.join(notes) if notes else 'none'}\n\n"
            "Write a 3-5 sentence ruling explanation addressed to both parties."
        )
        fallback = self._fallback_reasoning(dispute, decision, notes, action, confidence)
        return self.llm_or(system, user, fallback, temperature=0.2)

    def _fallback_reasoning(self, dispute, decision, notes, action, confidence) -> str:
        cat = dispute.get("category", "").replace("_", " ")
        base = f"After weighing both sides in this {cat} dispute, the {decision.action.replace('_', ' ')}"
        if decision.amount:
            base += f" of {format_money(decision.amount)}"
        base += " was applied."
        if decision.explanation:
            base += f" {decision.explanation}"
        if notes:
            base += " " + " ".join(notes)
        base += f" Overall confidence: {confidence:.0%}."
        return base
