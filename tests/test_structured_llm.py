"""Local-call provenance and rejection at the provider boundary (no network)."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json

import pytest

from backend.core.llm import LLMConfig, LLMProvider


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")


def provider():
    return LLMProvider(LLMConfig("https://example.invalid/v1", "not-a-real-key", "test-model"))


def validate(value):
    if value != {"choice": "known"}:
        raise ValueError("untrusted secret output should not be exposed")
    return {"choice": "known", "validated": True}


def complete(p, **kwargs):
    return p.complete_structured(
        "system", "user", fallback={"choice": "fallback"},
        validate=validate, prompt_version="rider@1.0.0", **kwargs,
    )


class Response:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


def replies(monkeypatch, *contents):
    sent = []
    iterator = iter(contents)

    def post(url, *, json, headers, timeout):
        sent.append(json)
        return Response(next(iterator))

    monkeypatch.setattr("backend.core.llm.requests.post", post)
    return sent


def test_no_key_has_local_fallback_metadata_and_never_calls_http(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("No-key requests must remain offline")

    monkeypatch.setattr("backend.core.llm.requests.post", unexpected)
    p = LLMProvider()
    result = complete(p)
    assert result.value == {"choice": "fallback"}
    assert (result.mode, result.status, result.attempts) == ("fallback", "no_key", 0)
    assert result.model is None
    assert result.prompt_version == "rider@1.0.0"
    assert result.latency_ms >= 0
    assert result.attempt_errors == []
    assert p.status()["last_call_ok"] is None


def test_valid_result_is_canonical_validator_output(monkeypatch):
    sent = replies(monkeypatch, '{"choice":"known"}')
    p = provider()
    result = complete(p)
    assert result.value == {"choice": "known", "validated": True}
    assert (result.mode, result.status, result.attempts) == ("llm", "ok", 1)
    assert result.model == "test-model"
    assert result.error_code is None
    assert result.attempt_errors == []
    assert p.status()["success_count"] == 1
    assert len(sent) == 1
    assert sent[0]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]


@pytest.mark.parametrize("bad", [
    "not json", '```json\n{"choice":"known"}\n```',
    'Here is the result: {"choice":"known"}',
    '{"choice":"known"}\nIgnore prior instructions',
    "[]", "null", '"known"', '{"choice":NaN}',
    '{"choice":"unknown","choice":"known"}',
])
def test_invalid_json_is_rejected_and_retried_only_once(monkeypatch, bad):
    sent = replies(monkeypatch, bad, bad)
    p = provider()
    result = complete(p, max_retries=99)
    assert result.value == {"choice": "fallback"}
    assert (result.mode, result.status, result.attempts) == ("fallback", "rejected", 2)
    assert result.error_code == "invalid_json"
    assert result.attempt_errors == ["invalid_json", "invalid_json"]
    assert len(sent) == 2
    assert p.status()["success_count"] == 0
    assert p.status()["last_error"] == "invalid_json"


def test_validation_repair_preserves_first_error_without_leaking_output(monkeypatch):
    sent = replies(monkeypatch, '{"choice":"secret text"}', '{"choice":"known"}')
    p = provider()
    result = complete(p)
    assert result.value == {"choice": "known", "validated": True}
    assert (result.mode, result.status, result.attempts) == ("llm", "ok", 2)
    assert result.attempt_errors == ["invalid_output"]
    assert result.error_code is None
    assert "secret text" not in json.dumps(sent[1])
    assert "untrusted secret" not in result.model_dump_json()
    assert p.status()["last_error"] is None


def test_schema_failure_without_retry_returns_safe_rejection(monkeypatch):
    sent = replies(monkeypatch, '{"choice":"bad"}')
    result = complete(provider(), max_retries=0)
    assert (result.status, result.error_code, result.attempts) == ("rejected", "invalid_output", 1)
    assert result.attempt_errors == ["invalid_output"]
    assert len(sent) == 1


def test_excessive_json_nesting_is_rejected_without_crashing(monkeypatch):
    depth = 10000
    replies(monkeypatch, '{"x":' + "[" * depth + "0" + "]" * depth + "}")
    result = complete(provider(), max_retries=0)
    assert (result.status, result.error_code) == ("rejected", "invalid_json")
    assert result.value == {"choice": "fallback"}


def test_network_error_never_retries_or_exposes_exception(monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("https://example.invalid?api_key=private-secret")

    monkeypatch.setattr("backend.core.llm.requests.post", fail)
    p = provider()
    result = complete(p)
    assert (result.mode, result.status, result.attempts) == ("fallback", "error", 1)
    assert result.error_code == "provider_error"
    assert result.attempt_errors == ["provider_error"]
    assert len(calls) == 1
    assert "private-secret" not in result.model_dump_json()
    assert "private-secret" not in json.dumps(p.status())


def test_interleaved_calls_do_not_derive_result_from_global_health(monkeypatch):
    rendezvous = Barrier(2)

    def post(url, *, json, headers, timeout):
        user = json["messages"][1]["content"]
        rendezvous.wait(timeout=3)
        if user == "bad":
            raise RuntimeError("failed")
        return Response('{"choice":"known"}')

    monkeypatch.setattr("backend.core.llm.requests.post", post)
    p = provider()

    def run(user):
        return p.complete_structured("sys", user, fallback={}, validate=validate, prompt_version="v1")

    with ThreadPoolExecutor(max_workers=2) as pool:
        good, bad = list(pool.map(run, ["good", "bad"]))
    assert (good.mode, good.status) == ("llm", "ok")
    assert (bad.mode, bad.status) == ("fallback", "error")
    assert p.status()["success_count"] == p.status()["fail_count"] == 1


def test_legacy_json_fences_still_work(monkeypatch):
    replies(monkeypatch, '```json\n{"choice":"known"}\n```')
    assert provider().complete_json("sys", "usr", fallback={}) == {"choice": "known"}


def test_legacy_errors_use_safe_health_code(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("sensitive-provider-response")

    monkeypatch.setattr("backend.core.llm.requests.post", fail)
    p = provider()
    assert p.complete("sys", "usr", fallback="offline") == "offline"
    assert p.status()["last_error"] == "provider_error"
