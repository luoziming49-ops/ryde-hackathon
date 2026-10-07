# Ryde Dispute AI

A multi-agent autonomous dispute-resolution system for ride-hailing platforms — Rider Advocate, Driver Advocate and Judge agents gather evidence, build adversarial cases, apply company policy, and issue a fair ruling with a confidence score and plain-language explanation. A deterministic evidence + policy engine computes the facts (deviation %, wait time, refund amount) so the LLM can argue and explain but never fabricate the decision. Built for the Tencent Cloud × AI Singapore Hackathon 2026, Digital Native / Ryde track.

## Quick start

```bash
python -m venv .venv
pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn backend.main:app --port 8000
```

Then open http://localhost:8000 in a browser.

## Tests

```bash
pytest -q
```

## Documentation

See [docs/](docs/) — including the [project rules](PROJECT_RULES.md), [sprint plan](docs/SPRINT.md), and [status](docs/STATUS.md).
