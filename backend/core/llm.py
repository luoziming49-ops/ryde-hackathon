"""LLM provider abstraction.

Uses an OpenAI-compatible chat completion endpoint when credentials are
available (works with Tencent Cloud Hunyuan, OpenAI, or any compatible API via
`OPENAI_BASE_URL` / `OPENAI_API_KEY` / `LLM_MODEL`). Falls back to a local,
deterministic template renderer so the demo always runs.

This mirrors a core design principle of the system: GenAI produces *drafts*,
while correctness-critical decisions are backed by deterministic logic.
"""

from __future__ import annotations

import json
import os
import math
import time
from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Optional

from backend.contracts import LLMResult

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    timeout: int = 30
    thinking: str | None = None
    json_mode: bool = False

    def __post_init__(self):
        if self.thinking not in (None, "enabled", "disabled") or type(self.json_mode) is not bool:
            raise ValueError("invalid_llm_configuration")


def _config_from_env() -> Optional[LLMConfig]:
    key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""
    base = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or "https://api.openai.com/v1"
    )
    model = os.getenv("LLM_MODEL") or "gpt-4o-mini"
    if not key:
        return None
    thinking = os.getenv("LLM_THINKING") or None
    json_mode = os.getenv("LLM_JSON_MODE") or "false"
    if json_mode not in ("true", "false"):
        raise ValueError("invalid_llm_configuration")
    return LLMConfig(base_url=base.rstrip("/"), api_key=key, model=model,
                     thinking=thinking, json_mode=json_mode == "true")


_USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")


class _ResponseText(str):
    """String-compatible content carrying only sanitized usage for this response."""

    def __new__(cls, content: str, usage):
        text = super().__new__(cls, content)
        text.usage = {
            key: usage[key] for key in _USAGE_FIELDS
            if isinstance(usage, dict) and type(usage.get(key)) is int and usage[key] >= 0
        } or None
        return text


class LLMProvider:
    """Chat-completion provider with graceful offline fallback.

    Tracks real call outcomes so `/api/health` and the UI badge can honestly
    report: grey = no key, amber = configured but failing/fallback,
    green = last call succeeded.
    """

    def __init__(self, config: Optional[LLMConfig] = None, *, use_env: bool = True):
        self.config = config if config is not None else (_config_from_env() if use_env else None)
        self.llm_configured = self.config is not None and requests is not None
        # Backward-compatible alias: "configured" (does NOT mean "working").
        self.available = self.llm_configured
        self.last_error: Optional[str] = None
        self.last_call_ok: Optional[bool] = None  # None = never attempted
        self.success_count: int = 0
        self.fail_count: int = 0
        self._status_lock = Lock()

    def status(self) -> dict:
        with self._status_lock:
            return self._status_unlocked()

    def _status_unlocked(self) -> dict:
        if not self.llm_configured:
            state = "no_key"
        elif self.last_call_ok is None:
            state = "configured"
        elif self.last_call_ok:
            state = "ok"
        else:
            state = "fallback"
        return {
            "llm_configured": self.llm_configured,
            "state": state,
            "last_call_ok": self.last_call_ok,
            "last_error": self.last_error,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "model": self.config.model if self.config else None,
        }

    def _record(self, error_code: Optional[str]) -> None:
        """Update aggregate health after a whole logical call completes."""
        with self._status_lock:
            self.last_call_ok = error_code is None
            self.last_error = error_code
            if error_code is None:
                self.success_count += 1
            else:
                self.fail_count += 1

    def _request(self, messages: list[dict], *, temperature: float, max_tokens: int,
                 json_mode: bool = False) -> str:
        if self.config is None or requests is None:
            raise RuntimeError("provider_unavailable")
        body = {"model": self.config.model, "temperature": temperature,
                "max_tokens": max_tokens, "messages": messages}
        if self.config.thinking is not None:
            body["thinking"] = {"type": self.config.thinking}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        resp = requests.post(
            f"{self.config.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self.config.api_key}",
                     "Content-Type": "application/json"},
            timeout=self.config.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("provider_response_shape")
        return _ResponseText(content.strip(), payload.get("usage"))

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
        fallback: str = "",
    ) -> str:
        """Return LLM output, or `fallback` if unavailable/erroring."""
        if not self.llm_configured or self.config is None:
            return fallback
        try:
            content = self._request([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ], temperature=temperature, max_tokens=max_tokens)
            self._record(None)
            return content
        except Exception:  # noqa: BLE001 - never expose remote exception text
            self._record("provider_error")
            return fallback

    def complete_json(
        self, system: str, user: str, *, fallback: dict, temperature: float = 0.1
    ) -> dict:
        if not self.llm_configured or self.config is None:
            return fallback
        try:
            text = self._request([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ], temperature=temperature, max_tokens=1200)
        except Exception:  # noqa: BLE001
            self._record("provider_error")
            return fallback
        # Strip markdown fences if present.
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            result = _json_object(cleaned)
            self._record(None)
            return result
        except (ValueError, TypeError):
            self._record("invalid_json")
            return fallback

    def complete_structured(
        self,
        system: str,
        user: str,
        *,
        fallback: dict,
        validate: Callable[[dict], dict],
        prompt_version: str,
        max_retries: int = 1,
    ) -> LLMResult:
        """Validate one call locally; reject unsafe output and repair at most once.

        Health fields are aggregate observations only. Every returned result is
        built from this invocation's variables, including when calls interleave.
        No raw model response or exception is retained in error metadata.
        """
        started = time.perf_counter()
        attempts = 0
        errors: list[str] = []
        usage: dict[str, int] = {}
        usage_complete = True

        def result(value, mode, status, error_code=None):
            return LLMResult(
                value=deepcopy(value), mode=mode, status=status,
                model=self.config.model if self.config else None,
                prompt_version=prompt_version,
                latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
                error_code=error_code, attempts=attempts, attempt_errors=errors,
                usage=usage or None, usage_complete=attempts > 0 and usage_complete,
            )

        if not self.llm_configured or self.config is None:
            return result(fallback, "fallback", "no_key", "no_key")

        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
        # Callers cannot accidentally turn a repair into unbounded API spend.
        limit = 2 if max_retries > 0 else 1
        for attempt in range(limit):
            attempts += 1
            try:
                # Existing string-only transports keep their original signature
                # unless JSON mode has been explicitly enabled for this provider.
                options = {"json_mode": True} if self.config.json_mode else {}
                text = self._request(messages, temperature=0.1, max_tokens=1800, **options)
            except Exception:  # noqa: BLE001
                usage_complete = False
                errors.append("provider_error")
                self._record("provider_error")
                return result(fallback, "fallback", "error", "provider_error")
            attempt_usage = text.usage if isinstance(text, _ResponseText) else None
            if attempt_usage is None or len(attempt_usage) != len(_USAGE_FIELDS):
                usage_complete = False
            for key, count in (attempt_usage or {}).items():
                usage[key] = usage.get(key, 0) + count
            try:
                value = _json_object(text)
            except (ValueError, TypeError):
                error_code = "invalid_json"
            else:
                try:
                    value = validate(value)
                    if not isinstance(value, dict):
                        raise ValueError("validator must return an object")
                except (ValueError, TypeError):
                    error_code = "invalid_output"
                else:
                    self._record(None)
                    return result(value, "llm", "ok")
            errors.append(error_code)
            if attempt + 1 < limit:
                # This code is trusted metadata, never the rejected model text.
                messages = messages + [{"role": "user", "content": json.dumps({
                    "validation_error": error_code, "retry": True,
                })}]
        self._record(errors[-1])
        return result(fallback, "fallback", "rejected", errors[-1])


def _json_object(text: str) -> dict:
    def unique_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate_key")
            value[key] = item
        return value

    def finite_float(raw):
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("nonfinite_json")
        return value

    def reject_constant(raw):
        raise ValueError("nonfinite_json")

    try:
        value = json.loads(text, object_pairs_hook=unique_keys,
                           parse_float=finite_float, parse_constant=reject_constant)
    except RecursionError:
        raise ValueError("json_too_deep") from None
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


_provider: Optional[LLMProvider] = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider
