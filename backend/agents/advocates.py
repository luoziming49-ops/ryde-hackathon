"""Bounded advocates select attributable claims, never amounts or new facts."""

from ..core.guard import build_evidence_catalog, build_policy_context
from ..core.policy import apply_policy
from .base import BaseAgent


class AdvocateAgent(BaseAgent):
    party = "rider"
    opponent = "driver"

    def __init__(self, policies: list[dict], config=None, **kwargs):
        super().__init__(**kwargs)
        self.policies = policies
        self.config = config or {}

    def build_case(self, dispute, evidence, *, catalog=None, decision=None):
        if catalog is None:
            catalog = build_evidence_catalog(dispute, evidence)
        if decision is None:
            decision = apply_policy(evidence, self.policies, self.config)
        allowed = set(decision.matched_policy_ids)
        missing = list(dict.fromkeys(evidence.gaps + evidence.missing_fares))
        action = ("full_refund" if self.party == "rider" else "no_action") if evidence.category in (
            "route_deviation", "no_show") else "escalate"
        self.emit("gather", f"Selecting {self.party}-side claims from the versioned evidence catalog.")
        result = self.grounded_result(self.party, catalog, allowed, missing, action,
            context={"policy_context": build_policy_context(self.policies, self.config, dispute, evidence, decision)})
        points = [claim["text"] for claim in result.value["claims"]]
        for claim in result.value["claims"]:
            self.emit("evidence", claim["text"], evidence_ids=claim["evidence_ids"],
                      policy_ids=claim["policy_ids"])
        desired = result.value["proposed_action"].replace("_", " ")
        argument = f"{self.party.title()} position: {desired}. " + " ".join(points)
        if result.value["missing_evidence"]:
            argument += " Missing evidence: " + ", ".join(result.value["missing_evidence"]) + "."
        citations = sorted({p for claim in result.value["claims"] for p in claim["policy_ids"]})
        self.emit("argue", argument, desired_outcome=desired, policy_citations=citations, llm=result.metadata())
        return {"party": self.party, "desired_outcome": desired, "points": points,
                "policy_citations": citations, "argument": argument,
                "structured": result.value, "llm_result": result.metadata()}


class RiderAdvocateAgent(AdvocateAgent):
    name = "Rider Advocate"
    description = "Selects evidence supporting a rider-side position."
    party = "rider"
    opponent = "driver"


class DriverAdvocateAgent(AdvocateAgent):
    name = "Driver Advocate"
    description = "Selects evidence supporting a driver-side position."
    party = "driver"
    opponent = "rider"
