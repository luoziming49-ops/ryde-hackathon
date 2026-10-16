"""Minimal ``.env`` loader (no external dependency).

Parses ``KEY=VALUE`` lines from a ``.env`` file into ``os.environ``. A variable
that is **already present** in the environment is never overridden, so real
shell/CI secrets always win over the file.
"""

from __future__ import annotations

import os
from pathlib import Path

# Project root is two levels up from backend/core/config.py.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def default_dotenv_path() -> Path:
    return PROJECT_ROOT / ".env"


def load_dotenv(path: str | Path | None = None, override: bool = False) -> dict[str, str]:
    """Load a ``.env`` file and return the keys that were set.

    ``override=False`` (default) never replaces a variable already set in the
    environment. Lines are ``KEY=VALUE``; blank lines and ``#`` comments are
    skipped, and a leading ``export `` is stripped. Values may be wrapped in
    single or double quotes.
    """
    path = Path(path) if path is not None else default_dotenv_path()
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not key or not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    return loaded
