"""Shared pytest fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "sample_data"


def _load(name: str):
    with (DATA_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def disputes():
    return _load("disputes.json")


@pytest.fixture(scope="session")
def policies():
    return _load("policies.json")["policies"]


@pytest.fixture(scope="session")
def config():
    return _load("policies.json").get("config", {})


@pytest.fixture(scope="session")
def precedents():
    return _load("precedents.json")["precedents"]


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def sample_case(disputes):
    """Return a sample case by id."""
    def _get(case_id: str) -> dict:
        for d in disputes:
            if d["case_id"] == case_id:
                return d
        raise KeyError(case_id)

    return _get
