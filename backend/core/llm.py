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
from dataclasses import dataclass
from typing import Optional

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
    return LLMConfig(base_url=base.rstrip("/"), api_key=key, model=model)


class LLMProvider:
    """Chat-completion provider with graceful offline fallback.

    Tracks real call outcomes so `/api/health` and the UI badge can honestly
    report: grey = no key, amber = configured but failing/fallback,
    green = last call succeeded.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or _config_from_env()
        self.llm_configured = self.config is not None and requests is not None
        # Backward-compatible alias: "configured" (does NOT mean "working").
        self.available = self.llm_configured
        self.last_error: Optional[str] = None
        self.last_call_ok: Optional[bool] = None  # None = never attempted
        self.success_count: int = 0
        self.fail_count: int = 0

    def status(self) -> dict:
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
        url = f"{self.config.base_url}/chat/completions"
        payload = {
            "model": self.config.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            self.last_call_ok = True
            self.success_count += 1
            self.last_error = None
            return content
        except Exception as exc:  # noqa: BLE001
            self.last_call_ok = False
            self.fail_count += 1
            self.last_error = str(exc)
            return fallback

    def complete_json(
        self, system: str, user: str, *, fallback: dict, temperature: float = 0.1
    ) -> dict:
        text = self.complete(system, user, temperature=temperature, max_tokens=1200)
        if not text:
            return fallback
        # Strip markdown fences if present.
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except Exception:  # noqa: BLE001
            return fallback


_provider: Optional[LLMProvider] = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider
