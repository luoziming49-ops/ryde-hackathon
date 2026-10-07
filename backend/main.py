"""FastAPI backend for the Ryde Dispute AI prototype."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .adapters.official_ticket import is_official_ticket, normalize_official_ticket
from .agents.orchestrator import DisputeOrchestrator
from .core.config import load_dotenv
from .core.llm import get_llm
from .schemas import Dispute, ResolveRequest, dump_dispute

# Load a local .env if present (never overrides already-set env vars).
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "sample_data"
OFFICIAL_DIR = DATA_DIR / "official"
FRONTEND_DIR = ROOT / "frontend"


def _load_json(name: str) -> Any:
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_disputes() -> list[dict]:
    raw = _load_json("disputes.json")
    return [dump_dispute(Dispute.model_validate(d)) for d in raw]


def _load_official_disputes() -> list[dict]:
    out: list[dict] = []
    if not OFFICIAL_DIR.exists():
        return out
    for path in sorted(OFFICIAL_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        out.append(normalize_official_ticket(raw))
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.disputes = _load_disputes()
    app.state.official_disputes = _load_official_disputes()
    policies = _load_json("policies.json")
    precedents = _load_json("precedents.json")
    app.state.policies = policies["policies"]
    app.state.precedents = precedents["precedents"]
    app.state.orchestrator = DisputeOrchestrator(
        policies=policies["policies"],
        precedents=precedents["precedents"],
        config=policies.get("config", {}),
    )
    yield


app = FastAPI(title="Ryde Dispute AI", version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak a stack trace to the client.
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
def health() -> dict:
    llm = get_llm()
    return {"status": "ok", **llm.status()}


def _summarize(d: dict, source: str) -> dict:
    return {
        "case_id": d["case_id"],
        "category": d["category"],
        "rider_claim": (d.get("rider") or {}).get("claim"),
        "driver_response": (d.get("driver") or {}).get("response"),
        "priority": d.get("priority", "standard"),
        "source": source,
    }


@app.get("/api/disputes")
def list_disputes() -> list[dict]:
    result = [_summarize(d, "internal") for d in app.state.disputes]
    result += [_summarize(d, "official") for d in app.state.official_disputes]
    return result


@app.get("/api/disputes/{case_id}")
def get_dispute(case_id: str) -> dict:
    for d in app.state.disputes + app.state.official_disputes:
        if d["case_id"] == case_id:
            return d
    raise HTTPException(status_code=404, detail="Dispute not found")


@app.post("/api/resolve")
def resolve_dispute(payload: dict = Body(...)) -> dict:
    # 1. Organiser's official ticket format.
    if is_official_ticket(payload):
        dispute = normalize_official_ticket(payload)
        return app.state.orchestrator.resolve(dispute)

    # 2. Known case by id (internal sample or official sample).
    case_id = payload.get("case_id")
    if case_id is not None:
        if not isinstance(case_id, str):
            raise HTTPException(status_code=422, detail="case_id must be a string")
        for d in app.state.disputes + app.state.official_disputes:
            if d["case_id"] == case_id:
                return app.state.orchestrator.resolve(d)
        raise HTTPException(status_code=404, detail="Dispute not found")

    # 3. Inline dispute — validate with typed nested models.
    try:
        req = ResolveRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors())) from exc

    if not (req.category and req.rider and req.driver):
        raise HTTPException(
            status_code=422,
            detail="Inline dispute requires 'category', 'rider' and 'driver'.",
        )
    return app.state.orchestrator.resolve(req.to_inline_dispute())


@app.get("/api/policies")
def get_policies() -> dict:
    return {"policies": app.state.policies}


@app.get("/api/precedents")
def get_precedents() -> dict:
    return {"precedents": app.state.precedents}


# Static frontend.
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
