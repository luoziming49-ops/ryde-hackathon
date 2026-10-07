"""Orchestrator: coordinates the multi-agent dispute-resolution pipeline.

Pipeline order:
  1. Evidence Collection (structured retrieval across GPS/chat/fare/history)
  2. Deterministic evidence analysis
  3. Fraud & Bad-Faith Detection   (stretch, in parallel with advocates)
  4. Policy & Precedent retrieval   (stretch)
  5. Rider Advocate  ─┐
  6. Driver Advocate ─┴─›  Judge  →  ruling + confidence + explanation
  7. Escalation protocol (low confidence → human review)

Every agent emits observable messages so the frontend can render the inter-agent
communication log in real time.
"""

from __future__ import annotations

import time
from typing import Any

from ..core.evidence import EvidenceAnalysis, analyze_evidence
from .base import BaseAgent
from .advocates import RiderAdvocateAgent, DriverAdvocateAgent
from .fraud_detection import FraudDetectionAgent
from .judge import JudgeAgent
from .policy_precedent import PolicyPrecedentAgent


class EvidenceCollectionAgent(BaseAgent):
    """Gathers and normalizes structured evidence from all data sources."""

    name = "Evidence Collection"
    description = "Retrieves GPS, chat, fare and history evidence for both advocates."

    def collect(self, dispute: dict, evidence: EvidenceAnalysis) -> dict[str, Any]:
        self.emit("gather", "Retrieving trip GPS/telemetry, chat logs, fare breakdown and account history.")
        sources = {
            "gps": bool(dispute.get("gps")),
            "chat_log": len(dispute.get("chat_log", [])),
            "fare": bool(dispute.get("fare")),
            "history": {
                "rider_disputes": evidence.rider_dispute_history,
                "driver_disputes": evidence.driver_dispute_history,
            },
        }
        self.emit(
            "gather",
            f"Evidence indexed: {sources['chat_log']} chat messages, "
            f"rider/driver history {sources['history']['rider_disputes']}/{sources['history']['driver_disputes']} disputes.",
            sources=sources,
        )
        return sources


class DisputeOrchestrator:
    def __init__(self, policies: list[dict], precedents: list[dict], config: dict | None = None):
        self.policies = policies
        self.precedents = precedents
        self.config = config or {}

    def resolve(self, dispute: dict) -> dict[str, Any]:
        started = time.time()
        trace: list[dict[str, Any]] = []

        # 1. Evidence collection + deterministic analysis.
        collector = EvidenceCollectionAgent()
        evidence: EvidenceAnalysis = analyze_evidence(dispute)
        collector.collect(dispute, evidence)
        trace.extend(collector.trace)

        # 2. Fraud detection (stretch).
        fraud_agent = FraudDetectionAgent()
        fraud = fraud_agent.analyze(dispute, evidence)
        trace.extend(fraud_agent.trace)

        # 3. Policy & precedent (stretch).
        pp_agent = PolicyPrecedentAgent(self.policies, self.precedents)
        precedent = pp_agent.retrieve(dispute, evidence)
        trace.extend(pp_agent.trace)

        # 4. Advocates (core) — conceptually parallel.
        rider_agent = RiderAdvocateAgent(self.policies)
        driver_agent = DriverAdvocateAgent(self.policies)
        rider_case = rider_agent.build_case(dispute, evidence)
        driver_case = driver_agent.build_case(dispute, evidence)
        trace.extend(rider_agent.trace)
        trace.extend(driver_agent.trace)

        # 5. Judge (core).
        judge = JudgeAgent(self.policies, self.config)
        ruling = judge.rule(dispute, evidence, rider_case, driver_case, fraud, precedent)
        trace.extend(judge.trace)

        duration_ms = int((time.time() - started) * 1000)

        return {
            "case_id": dispute.get("case_id"),
            "category": dispute.get("category"),
            "evidence": evidence.to_dict(),
            "fraud": fraud,
            "precedent": precedent,
            "rider_case": rider_case,
            "driver_case": driver_case,
            "ruling": ruling,
            "trace": [m.to_dict() for m in trace],
            "duration_ms": duration_ms,
        }
