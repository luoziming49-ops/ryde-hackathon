"""Ryde Dispute AI — Multi-Agent Autonomous Dispute Resolution System.

A hackathon prototype that resolves ride-hailing disputes (route deviation,
no-show charges, etc.) using a multi-agent architecture:

    Rider Advocate  <--->  Judge  <--->  Driver Advocate
                                ^
              (Fraud Detection / Policy & Precedent / Escalation)

The three core agents operate on text & structured evidence. Reasoning is
produced by an optional LLM provider with a deterministic template fallback so
the system is fully demoable with or without an API key.
"""

__version__ = "1.0.0"
