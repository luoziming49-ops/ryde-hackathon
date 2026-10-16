"""Orchestrator: coordinates the multi-agent dispute-resolution pipeline.

Pipeline order:
  1. Evidence Collection (structured retrieval across GPS/chat/fare/history)
  2. Deterministic evidence analysis
  3. Fraud & Bad-Faith Detection   (deterministic risk signals)
  4. Policy & Precedent retrieval   (stretch)
  5. Rider Advocate  ─┐
  6. Driver Advocate ─┴─›  Judge  →  ruling + confidence + explanation
  7. Escalation protocol (low confidence → human review)

Every agent emits messages immediately to the run recorder. The legacy response
also retains the completed trace for compatibility.
"""

from __future__ import annotations

import time
from typing import Any

from ..core.evidence import EvidenceAnalysis, analyze_evidence
from ..core.guard import build_evidence_catalog, build_policy_context
from ..core.policy import apply_policy
from ..core.events import RunRecorder
from ..core.tools import CaseTools
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

    def resolve(self, dispute: dict, *, is_simulated: bool | None = None,
                provider=None, recorder=None) -> dict[str, Any]:
        started = time.time()
        trace: list[dict[str, Any]] = []
        recorder = recorder or RunRecorder()
        tools = CaseTools(dispute, recorder)
        dispute = tools.materialize()
        options = {"llm": provider, "event_sink": recorder.message}
        policies = tools.call('policy.read', lambda: self.policies,
                              lambda result: f'{len(result)} local policy documents read')

        # 1. Evidence collection + deterministic analysis.
        collector = EvidenceCollectionAgent(**options)
        evidence: EvidenceAnalysis = analyze_evidence(dispute)
        catalog = build_evidence_catalog(dispute, evidence, is_simulated=is_simulated)
        decision = apply_policy(evidence, policies, self.config)
        collector.collect(dispute, evidence)
        trace.extend(collector.trace)

        # 2. Fraud detection (stretch).
        fraud_agent = FraudDetectionAgent(**options)
        fraud = fraud_agent.analyze(dispute, evidence)
        trace.extend(fraud_agent.trace)

        # 3. Policy & precedent (stretch).
        pp_agent = PolicyPrecedentAgent(policies, self.precedents, **options)
        precedent = pp_agent.retrieve(dispute, evidence)
        trace.extend(pp_agent.trace)

        # 4. Advocates (core) — conceptually parallel.
        rider_agent = RiderAdvocateAgent(policies, self.config, **options)
        driver_agent = DriverAdvocateAgent(policies, self.config, **options)
        rider_case = rider_agent.build_case(dispute, evidence, catalog=catalog, decision=decision)
        driver_case = driver_agent.build_case(dispute, evidence, catalog=catalog, decision=decision)
        trace.extend(rider_agent.trace)
        trace.extend(driver_agent.trace)

        # 5. Judge (core).
        judge = JudgeAgent(policies, self.config, **options)
        ruling = judge.rule(dispute, evidence, rider_case, driver_case, fraud, precedent, catalog=catalog, decision=decision)
        trace.extend(judge.trace)

        duration_ms = int((time.time() - started) * 1000)
        policy_context = build_policy_context(policies, self.config, dispute, evidence, decision)
        policy_catalog = [{**rule, "version": policy_context['version'],
                           "source": 'local_demo_policy', "is_simulated": True,
                           "effective_free_wait_min": policy_context['effective_free_wait_min'],
                           "free_wait_source": policy_context['free_wait_source']}
                          for rule in policy_context['matched_rules']]

        return {
            "run_id": recorder.run_id,
            "execution": {"mode": "simulation", "scenario": provider.scenario}
                         if hasattr(provider, 'scenario') else {"mode": "provider", "scenario": None},
            "policy_catalog": policy_catalog,
            "case_id": catalog[0].case_id,
            "category": dispute.get("category"),
            "evidence": evidence.to_dict(),
            "evidence_catalog": [item.model_dump() for item in catalog],
            "policy_version": ruling["guard"]["policy_version"],
            "agent_results": {"rider": rider_case["llm_result"], "driver": driver_case["llm_result"],
                              "judge": ruling["llm_result"]},
            "fraud": fraud,
            "precedent": precedent,
            "rider_case": rider_case,
            "driver_case": driver_case,
            "ruling": ruling,
            "trace": [m.to_dict() for m in trace],
            "duration_ms": duration_ms,
            "raw_app_events": dispute.get("raw_app_events"),
        }
