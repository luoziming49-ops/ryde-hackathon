"""Tests for the tiny .env loader in backend.core.config."""

from __future__ import annotations

import os

import pytest

from backend.core.config import load_dotenv

_ENV_KEYS = ("LLM_API_KEY", "LLM_MODEL", "PORT", "QUOTED")


@pytest.fixture(autouse=True)
def _isolate_env():
    """Snapshot and restore the env vars touched by these tests, so a direct
    ``os.environ`` write from ``load_dotenv`` never leaks into other tests."""
    saved = {k: os.environ.get(k) for k in _ENV_KEYS}
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_load_dotenv_sets_missing_vars(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "LLM_API_KEY=sk-test-123\n"
        "# a comment\n"
        'LLM_MODEL="hunyuan-turbo"\n'
        "export PORT=9000\n"
        "QUOTED='single-quoted'\n",
        encoding="utf-8",
    )

    loaded = load_dotenv(env)

    assert os.environ["LLM_API_KEY"] == "sk-test-123"
    assert os.environ["LLM_MODEL"] == "hunyuan-turbo"
    assert os.environ["PORT"] == "9000"
    assert os.environ["QUOTED"] == "single-quoted"
    assert loaded["LLM_API_KEY"] == "sk-test-123"


def test_load_dotenv_never_overrides_existing_env(tmp_path):
    env = tmp_path / ".env"
    env.write_text("LLM_API_KEY=from-file\nPORT=8000\n", encoding="utf-8")
    os.environ["LLM_API_KEY"] = "from-shell"

    loaded = load_dotenv(env)

    assert os.environ["LLM_API_KEY"] == "from-shell"  # not overridden
    assert os.environ["PORT"] == "8000"  # missing var still loaded
    assert "LLM_API_KEY" not in loaded


def test_load_dotenv_missing_file_returns_empty(tmp_path):
    assert load_dotenv(tmp_path / "does-not-exist.env") == {}
