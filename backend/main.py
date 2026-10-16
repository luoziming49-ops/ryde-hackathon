"""FastAPI backend for the Ryde Dispute AI prototype."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from copy import deepcopy

from fastapi import Body, FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError, BaseModel, ConfigDict

from .adapters.official_ticket import is_official_ticket, normalize_official_ticket
from .agents.orchestrator import DisputeOrchestrator
from .core.config import load_dotenv
from .core.llm import get_llm, LLMProvider, _config_from_env
from .live_smoke import BoundedLiveProvider, validate_destination
from .core.events import RunStore, RunCapacityError
from .core.simulation import SimulationProvider, SCENARIOS
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
    app.state.runs = RunStore()
    app.state.live_config = None
    app.state.last_live_status = None
    if os.getenv('LLM_LIVE_ENABLED') == 'true':
        try:
            config = _config_from_env()
            validate_destination(config, os.getenv('LLM_CONFIRMED_BASE_URL', ''))
            app.state.live_config = config
        except ValueError:
            pass
    try:
        yield
    finally:
        app.state.runs.close()


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


@app.exception_handler(ValidationError)
async def invalid_dispute_handler(request: Request, exc: ValidationError) -> JSONResponse:
    # Do not echo untrusted input, non-finite numbers, or validator exceptions.
    return JSONResponse(status_code=422, content={
        "detail": exc.errors(include_input=False, include_context=False, include_url=False)
    })


@app.get("/api/health")
def health() -> dict:
    try:
        provider_status = get_llm().status()
    except ValueError:
        provider_status = {**LLMProvider(use_env=False).status(),
                           'state': 'configuration_error', 'last_error': 'invalid_configuration'}
    config = app.state.live_config
    return {"status": "ok", **(app.state.last_live_status or provider_status),
            "live_enabled": config is not None,
            "live_model": config.model if config else None}


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
    # Preserve legacy response shape without bypassing the explicit live gate.
    offline = LLMProvider(use_env=False)
    # 1. Organiser's official ticket format.
    if is_official_ticket(payload):
        dispute = normalize_official_ticket(payload)
        return app.state.orchestrator.resolve(dispute, provider=offline)

    # 2. Known case by id (internal sample or official sample).
    case_id = payload.get("case_id")
    if case_id is not None:
        if not isinstance(case_id, str):
            raise HTTPException(status_code=422, detail="case_id must be a string")
        for d in app.state.disputes + app.state.official_disputes:
            if d["case_id"] == case_id:
                return app.state.orchestrator.resolve(d, is_simulated=True, provider=offline)
        raise HTTPException(status_code=404, detail="Dispute not found")

    # 3. Inline dispute — validate with typed nested models.
    req = ResolveRequest.model_validate(payload)

    if not (req.category and req.rider and req.driver):
        raise HTTPException(
            status_code=422,
            detail="Inline dispute requires 'category', 'rider' and 'driver'.",
        )
    return app.state.orchestrator.resolve(req.to_inline_dispute(), provider=offline)


@app.get("/api/policies")
def get_policies() -> dict:
    return {"policies": app.state.policies}


@app.get("/api/precedents")
def get_precedents() -> dict:
    return {"precedents": app.state.precedents}


class SimulationRunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    case_id: str
    scenario: Literal['success', 'rider_rejected', 'retry_success', 'provider_error'] = 'success'


@app.get('/api/simulation/scenarios')
def simulation_scenarios():
    return {'mode': 'simulation', 'scenarios': [{'id': key, 'label': label} for key, label in SCENARIOS.items()]}


@app.post('/api/runs', status_code=202)
def start_run(request: SimulationRunRequest):
    # This endpoint deliberately has no real-provider option. Local demo only.
    dispute = next((d for d in app.state.disputes + app.state.official_disputes
                    if d['case_id'] == request.case_id), None)
    if dispute is None:
        raise HTTPException(404, 'Dispute not found')
    case = deepcopy(dispute)
    def execute(recorder):
        return app.state.orchestrator.resolve(case, is_simulated=True,
                    provider=SimulationProvider(request.scenario), recorder=recorder)
    try:
        run_id = app.state.runs.start(execute)
    except RunCapacityError:
        raise HTTPException(503, 'Demo is busy; retry after an active run finishes') from None
    return {'run_id': run_id, 'status': 'running'}


class LiveRunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    case_id: str


@app.post('/api/live-runs', status_code=202)
def start_live_run(payload: LiveRunRequest, request: Request):
    # Browser calls must come from this local workbench, not a foreign page.
    origin = request.headers.get('origin')
    if origin is not None and origin.rstrip('/') != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Live runs require the local workbench origin')
    config = app.state.live_config
    if config is None:
        raise HTTPException(503, 'Live provider is not enabled and configured')
    dispute = next((d for d in app.state.disputes + app.state.official_disputes
                    if d['case_id'] == payload.case_id), None)
    if dispute is None:
        raise HTTPException(404, 'Dispute not found')
    case = deepcopy(dispute)

    def execute(recorder):
        provider = BoundedLiveProvider(config)
        result = app.state.orchestrator.resolve(case, is_simulated=True,
                                               provider=provider, recorder=recorder)
        result['execution'] = {'mode': 'live', 'scenario': None,
                               'http_attempts': provider.http_attempts,
                               'request_limit': provider.request_limit}
        app.state.last_live_status = provider.status()
        return result

    try:
        run_id = app.state.runs.start(execute, mode='live')
    except RunCapacityError:
        raise HTTPException(503, 'Workbench is busy; retry after an active run finishes') from None
    return {'run_id': run_id, 'status': 'running'}


@app.get('/api/runs/{run_id}')
def run_snapshot(run_id: str, after: int = Query(default=0, ge=0)):
    try:
        return app.state.runs.get(run_id, after)
    except KeyError:
        raise HTTPException(404, 'Run not found; demo runs are temporary') from None


# Static frontend.
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
