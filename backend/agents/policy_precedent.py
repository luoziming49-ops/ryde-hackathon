"""Policy & Precedent Agent (stretch goal).

Maintains a lightweight knowledge base of company policies and past rulings and
retrieves the most relevant entries for the Judge to promote ruling
consistency. This is a deterministic keyword/overlap retriever so it runs
without an embedding model; it can be swapped for a vector RAG store.
"""

from __future__ import annotations

import re
from typing import Any

from ..core.evidence import EvidenceAnalysis
from .base import BaseAgent


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class PolicyPrecedentAgent(BaseAgent):
    name = "Policy & Precedent"
    description = "Retrieves relevant policy clauses and past rulings for consistent decisions."

    def __init__(self, policies: list[dict], precedents: list[dict], **kwargs):
        super().__init__(**kwargs)
        self.policies = policies
        self.precedents = precedents

    def retrieve(self, dispute: dict, evidence: EvidenceAnalysis) -> dict[str, Any]:
        category = dispute.get("category", "")
        query = " ".join(
            [
                dispute.get("rider", {}).get("claim", ""),
                dispute.get("driver", {}).get("response", ""),
                category,
            ]
        )

        clauses = []
        for policy in self.policies:
            if policy.get("category") != category:
                continue
            for clause in policy.get("clauses", []):
                overlap = len(_tokens(query) & _tokens(clause["text"]))
                clauses.append((overlap, clause["id"], clause["text"], policy.get("title", "")))

        clauses.sort(key=lambda x: -x[0])
        top_clauses = [
            {"id": c[1], "text": c[2], "policy": c[3]} for c in clauses[:6]
        ]

        related = [p for p in self.precedents if p.get("category") == category]
        top_precedents = related[:3]

        self.emit(
            "retrieve",
            f"Retrieved {len(top_clauses)} policy clause(s) and {len(top_precedents)} precedent(s).",
            clauses=top_clauses,
            precedents=top_precedents,
        )

        return {"clauses": top_clauses, "precedents": top_precedents}
