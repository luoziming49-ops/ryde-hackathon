"""FastAPI backend for the Ryde Dispute AI prototype."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agents.orchestrator import DisputeOrchestrator
from .core.llm import get_llm
from .schemas import ResolveRequest

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "sample_data"
FRONTEND_DIR = ROOT / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.disputes = _load_json("disputes.json")
    policies = _load_json("policies.json")
    precedents = _load_json("precedents.json")
    app.state.policies = policies
    app.state.precedents = precedents
    app.state.orchestrator = DisputeOrchestrator(
        policies=policies["policies"],
        precedents=precedents["precedents"],
        config=policies.get("config", {}),
    )
    yield


app = FastAPI(title="Ryde Dispute AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_json(name: str) -> Any:
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@app.get("/api/health")
def health() -> dict:
    llm = get_llm()
    return {"status": "ok", **llm.status()}


@app.get("/api/disputes")
def list_disputes() -> list[dict]:
    return [
        {
            "case_id": d["case_id"],
            "category": d["category"],
            "rider_claim": d["rider"]["claim"],
            "driver_response": d["driver"]["response"],
            "priority": d.get("priority", "standard"),
        }
        for d in app.state.disputes
    ]


@app.get("/api/disputes/{case_id}")
def get_dispute(case_id: str) -> dict:
    for d in app.state.disputes:
        if d["case_id"] == case_id:
            return d
    raise HTTPException(status_code=404, detail="Dispute not found")


@app.post("/api/resolve")
def resolve_dispute(req: ResolveRequest) -> dict:
    if req.case_id:
        for d in app.state.disputes:
            if d["case_id"] == req.case_id:
                return app.state.orchestrator.resolve(d)
        raise HTTPException(status_code=404, detail="Dispute not found")

    # Inline dispute: category + rider + driver are required.
    if not (req.category and req.rider and req.driver):
        raise HTTPException(
            status_code=422,
            detail="Inline dispute requires 'category', 'rider' and 'driver'.",
        )
    dispute = req.to_inline_dispute()
    return app.state.orchestrator.resolve(dispute)


@app.get("/api/policies")
def get_policies() -> dict:
    return app.state.policies


@app.get("/api/precedents")
def get_precedents() -> dict:
    return app.state.precedents


# Static frontend.
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
