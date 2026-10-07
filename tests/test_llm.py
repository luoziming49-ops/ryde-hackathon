"""Tests for the LLM provider status tracking (bug #8)."""

from __future__ import annotations

import pytest

from backend.core.llm import LLMConfig, LLMProvider


def test_status_no_key():
    p = LLMProvider(config=None)
    s = p.status()
    assert s["llm_configured"] is False
    assert s["state"] == "no_key"
    assert s["last_call_ok"] is None


def test_status_configured_but_never_called():
    p = LLMProvider(config=LLMConfig(base_url="http://x", api_key="k", model="m"))
    s = p.status()
    assert s["llm_configured"] is True
    assert s["state"] == "configured"
    assert s["last_call_ok"] is None


def test_success_sets_state_ok(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "hello"}}]}

    monkeypatch.setattr("backend.core.llm.requests.post", lambda *a, **k: FakeResp())
    p = LLMProvider(config=LLMConfig(base_url="http://x", api_key="k", model="m"))
    out = p.complete("sys", "usr", fallback="fb")
    assert out == "hello"
    assert p.last_call_ok is True
    assert p.success_count == 1
    assert p.status()["state"] == "ok"


def test_failure_sets_state_fallback(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("backend.core.llm.requests.post", boom)
    p = LLMProvider(config=LLMConfig(base_url="http://x", api_key="k", model="m"))
    out = p.complete("sys", "usr", fallback="fb")
    assert out == "fb"
    assert p.last_call_ok is False
    assert p.fail_count == 1
    assert p.last_error == "connection refused"
    assert p.status()["state"] == "fallback"


def test_no_key_never_records_call(monkeypatch):
    monkeypatch.setattr("backend.core.llm.requests.post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    p = LLMProvider(config=None)
    out = p.complete("sys", "usr", fallback="fb")
    assert out == "fb"
    assert p.last_call_ok is None  # never attempted, not a failure
    assert p.fail_count == 0
