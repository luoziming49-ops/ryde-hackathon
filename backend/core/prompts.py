"""Load versioned instructions and keep case data outside the system message."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
_NAMES = {"rider", "driver", "judge"}


def render_prompt(name: str, data: dict, schema: dict) -> tuple[str, str, str]:
    """Return static trusted instructions, nonce-delimited JSON, and version.

    Boundaries help the model distinguish case data from instructions. Actual
    enforcement remains the schema and reference validator after generation.
    """
    if name not in _NAMES:
        raise ValueError("Unknown prompt template")
    source = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    if not source.startswith("---\n"):
        raise ValueError("Prompt metadata missing")
    metadata_text, body = source[4:].split("\n---\n", 1)
    metadata = dict(line.split(":", 1) for line in metadata_text.splitlines() if line.strip())
    metadata = {key.strip(): value.strip() for key, value in metadata.items()}
    if metadata.get("name") != name or not metadata.get("version") or not metadata.get("purpose"):
        raise ValueError("Prompt metadata invalid")
    nonce = uuid4().hex
    system = body.replace("{{schema}}", json.dumps(schema, ensure_ascii=False, sort_keys=True))
    system = system.replace("{{nonce}}", nonce).strip()
    user = f"<DATA_{nonce}>\n{json.dumps(data, ensure_ascii=False, allow_nan=False)}\n</DATA_{nonce}>"
    return system, user, f"{name}@{metadata['version']}"
