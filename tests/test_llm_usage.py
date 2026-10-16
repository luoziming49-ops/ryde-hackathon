"""Provider-reported usage stays local to each structured call (no network)."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from backend.core.llm import LLMConfig, LLMProvider, _config_from_env


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.delenv("LLM_THINKING", raising=False)
    monkeypatch.delenv("LLM_JSON_MODE", raising=False)

    def unexpected(*args, **kwargs):
        pytest.fail("Real network is forbidden")

    monkeypatch.setattr("backend.core.llm.requests.post", unexpected)


def provider():
    return LLMProvider(LLMConfig("https://example.invalid/v1", "test-key", "test-model"))


def complete(p, user="case", **kwargs):
    def validate(value):
        if value != {"choice": "known"}:
            raise ValueError("invalid choice")
        return value

    return p.complete_structured(
        "system", user, fallback={"choice": "fallback"}, validate=validate,
        prompt_version="rider@1.0.0", **kwargs,
    )


class Response:
    def __init__(self, content='{"choice":"known"}', usage=None):
        self.payload = {"choices": [{"message": {"content": content}}], "usage": usage}

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def replies(monkeypatch, *responses):
    pending = iter(responses)

    def post(*args, **kwargs):
        response = next(pending)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("backend.core.llm.requests.post", post)


def test_complete_usage_appears_in_safe_metadata(monkeypatch):
    replies(monkeypatch, Response(usage={
        "prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18,
        "provider_secret": "do-not-retain", "completion_tokens_details": {"reasoning_tokens": 4},
    }))
    result = complete(provider())
    assert result.status == "ok"
    assert result.metadata()["usage"] == {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}
    assert result.metadata()["usage_complete"] is True
    assert "do-not-retain" not in result.model_dump_json()
    assert "reasoning_tokens" not in result.model_dump_json()


def test_usage_includes_rejected_attempt_before_success(monkeypatch):
    replies(monkeypatch,
            Response("invalid JSON", {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}),
            Response(usage={"prompt_tokens": 13, "completion_tokens": 5, "total_tokens": 18}))
    result = complete(provider())
    assert (result.status, result.attempts) == ("ok", 2)
    assert result.usage == {"prompt_tokens": 24, "completion_tokens": 12, "total_tokens": 36}
    assert result.usage_complete is True


@pytest.mark.parametrize("usage,expected", [
    (None, None), ({}, None), ("private-provider-data", None), ([1, 2, 3], None),
    ({"prompt_tokens": 11}, {"prompt_tokens": 11}),
    ({"prompt_tokens": True, "completion_tokens": -1, "total_tokens": "12"}, None),
    ({"prompt_tokens": 11, "completion_tokens": 2.0, "total_tokens": None}, {"prompt_tokens": 11}),
    ({"prompt_tokens": float("nan"), "completion_tokens": float("inf")}, None),
])
def test_missing_partial_or_malformed_usage_does_not_reject_content(monkeypatch, usage, expected):
    replies(monkeypatch, Response(usage=usage))
    result = complete(provider())
    assert result.status == "ok"
    assert result.usage == expected
    assert result.usage_complete is False


def test_reported_zero_usage_is_distinct_from_missing_usage(monkeypatch):
    replies(monkeypatch, Response(usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}))
    result = complete(provider())
    assert result.usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    assert result.usage_complete is True


@pytest.mark.parametrize("second,expected", [
    (Response(), {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}),
    (Response(usage={"completion_tokens": 5}), {"prompt_tokens": 11, "completion_tokens": 12, "total_tokens": 18}),
    (TimeoutError("private-provider-url-and-key"), {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}),
])
def test_missing_retry_usage_keeps_known_counts_but_marks_incomplete(monkeypatch, second, expected):
    replies(monkeypatch,
            Response("invalid JSON", {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}),
            second)
    result = complete(provider())
    assert result.attempts == 2
    assert result.usage == expected
    assert result.usage_complete is False
    assert "private-provider" not in result.model_dump_json()


def test_both_rejected_attempts_still_report_usage(monkeypatch):
    replies(monkeypatch,
            Response("invalid JSON", {"total_tokens": 18}),
            Response('{"choice":"bad"}', {"total_tokens": 20}))
    result = complete(provider())
    assert (result.mode, result.status) == ("fallback", "rejected")
    assert result.usage == {"total_tokens": 38}
    assert result.usage_complete is False


def test_no_key_usage_is_unknown_without_a_request():
    result = complete(LLMProvider())
    assert (result.status, result.attempts) == ("no_key", 0)
    assert result.usage is None
    assert result.usage_complete is False


def test_interleaved_calls_do_not_share_usage(monkeypatch):
    rendezvous = Barrier(2)

    def post(url, *, json, **kwargs):
        rendezvous.wait(timeout=3)
        tokens = 11 if json["messages"][1]["content"] == "first" else 27
        return Response(usage={"prompt_tokens": tokens, "completion_tokens": 3, "total_tokens": tokens + 3})

    monkeypatch.setattr("backend.core.llm.requests.post", post)
    p = provider()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda user: complete(p, user), ["first", "second"]))
    assert first.usage == {"prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14}
    assert second.usage == {"prompt_tokens": 27, "completion_tokens": 3, "total_tokens": 30}
    assert first.usage_complete is second.usage_complete is True


def test_string_transport_override_remains_compatible(monkeypatch):
    monkeypatch.setattr(LLMProvider, "_request", lambda *args, **kwargs: '{"choice":"known"}')
    result = complete(provider())
    assert result.status == "ok"
    assert result.usage is None
    assert result.usage_complete is False


def test_optional_provider_features_only_change_requested_body(monkeypatch):
    sent = []

    def post(url, *, json, **kwargs):
        sent.append(json)
        return Response()

    monkeypatch.setattr("backend.core.llm.requests.post", post)
    configured = LLMProvider(LLMConfig(
        "https://example.invalid/v1", "test-key", "test-model",
        thinking="disabled", json_mode=True,
    ))
    assert complete(configured).status == "ok"
    assert sent[0]["thinking"] == {"type": "disabled"}
    assert sent[0]["response_format"] == {"type": "json_object"}
    assert configured.complete("system", "user") == '{"choice":"known"}'
    assert "response_format" not in sent[1]
    assert sent[1]["thinking"] == {"type": "disabled"}
    assert complete(provider()).status == "ok"
    assert "thinking" not in sent[2]
    assert "response_format" not in sent[2]


@pytest.mark.parametrize("thinking,json_mode,expected_thinking,expected_json", [
    ("", "", None, False),
    ("disabled", "true", "disabled", True),
    ("enabled", "false", "enabled", False),
])
def test_optional_configuration_from_environment(monkeypatch, thinking, json_mode,
                                               expected_thinking, expected_json):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_THINKING", thinking)
    monkeypatch.setenv("LLM_JSON_MODE", json_mode)
    config = _config_from_env()
    assert config.thinking == expected_thinking
    assert config.json_mode is expected_json


@pytest.mark.parametrize("field,value", [
    ("LLM_THINKING", "private-invalid-thinking"),
    ("LLM_JSON_MODE", "private-invalid-json-mode"),
    ("LLM_JSON_MODE", "1"),
])
def test_invalid_optional_environment_fails_closed_without_echo(monkeypatch, field, value):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv(field, value)
    with pytest.raises(ValueError) as failure:
        _config_from_env()
    assert str(failure.value) == "invalid_llm_configuration"


@pytest.mark.parametrize("options", [
    {"thinking": "private-invalid-thinking"},
    {"json_mode": "false"},
])
def test_invalid_direct_configuration_fails_closed_without_echo(options):
    with pytest.raises(ValueError) as failure:
        LLMConfig("https://example.invalid/v1", "test-key", "test-model", **options)
    assert str(failure.value) == "invalid_llm_configuration"
