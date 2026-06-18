"""API routes over the pipeline + result store."""

from __future__ import annotations

import json
import shutil
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from .. import datagen
from ..ai import briefing as ai_briefing
from ..config.schema import Config
from ..loaders.base import load_all
from ..loaders.validate import EXPECTED_COLUMNS, REQUIRED_FILES, validate_upload
from ..models.borrowing_base import BorrowingBaseCertificate
from ..models.fccr import FccrReport
from ..models.verification import VerificationReport
from ..pipeline import (
    DEFAULT_LEVERS,
    _deep_merge,
    compute_with_overrides,
    goal_seek,
    load_scenario,
    run_pipeline,
    sensitivity,
)
from ..rendering import renderer
from ..store.db import connect, init_schema
from ..store.repository import FactRepository, ResultRepository
from .deps import get_conn

router = APIRouter()

# User uploads live under <repo>/uploads/<id>/ (gitignored).
UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB per file


class ComputeRequest(BaseModel):
    scenario: str = "baseline"
    upload_id: str | None = None              # use an uploaded dataset instead of a scenario
    config_overrides: dict = Field(default_factory=dict)


class ComputeResponse(BaseModel):
    run_id: str
    summary: dict
    verification: VerificationReport
    borrowing_base: BorrowingBaseCertificate
    fccr: FccrReport


class SensitivityRequest(BaseModel):
    scenario: str = "baseline"
    upload_id: str | None = None              # use an uploaded dataset instead of a scenario
    config_overrides: dict = Field(default_factory=dict)


class GoalSeekRequest(BaseModel):
    scenario: str = "baseline"
    upload_id: str | None = None              # use an uploaded dataset instead of a scenario
    config_overrides: dict = Field(default_factory=dict)
    lever: str                                # one of the goal-seekable rate/pct levers
    target_value: str                         # desired excess availability (Decimal string)


class AskRequest(ComputeRequest):
    question: str                             # free-text question, answered from the live figures


class ScenarioInfo(BaseModel):
    id: str
    label: str
    description: str


_SCENARIOS = [
    ScenarioInfo(
        id="baseline",
        label="Baseline (clean)",
        description="Healthy quarter; FCCR compliant at 1.20x with thin headroom and three reconciliation exceptions.",
    ),
    ScenarioInfo(
        id="stress",
        label="Stress (distressed)",
        description="NOLV haircuts, reserves, a cross-aged obligor, a sprung covenant, and a 0.89x FCCR breach.",
    ),
]

_ENGINE_BY_PATH = {
    "verification": "verification",
    "borrowing-base": "borrowing_base",
    "fccr": "fccr",
}
_RENDERERS = {
    "verification": renderer.render_verification,
    "borrowing_base": renderer.render_certificate,
    "fccr": renderer.render_fccr,
}


def _ensure_scenario_data(scenario: str) -> Config:
    """Load a scenario's config, generating its dataset if absent."""
    config = load_scenario(scenario)
    if not (Path(config.settings.data_dir) / "ar_aging.csv").exists():
        datagen.generate(scenario=scenario)
    return config


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #
@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/scenarios", response_model=list[ScenarioInfo])
def list_scenarios():
    return _SCENARIOS


@router.get("/config")
def get_config_route(scenario: str = Query("baseline")):
    """The resolved loan-agreement-as-config for a scenario (drives the what-if panel)."""
    return load_scenario(scenario).model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Uploads — bring your own data (fixed schema, validated)
# --------------------------------------------------------------------------- #
def _upload_data_dir(upload_id: str) -> Path:
    data_dir = UPLOADS_DIR / upload_id
    if not (data_dir / "ar_aging.csv").exists():
        raise HTTPException(404, f"upload not found: {upload_id}")
    return data_dir


@router.get("/templates/{name}")
def get_template(name: str):
    """A filled CSV example (the baseline data) showing the exact required format."""
    if name not in EXPECTED_COLUMNS:
        raise HTTPException(404, f"unknown template: {name}")
    config = _ensure_scenario_data("baseline")
    path = Path(config.settings.data_dir) / name
    content = path.read_text(encoding="utf-8") if path.exists() else ",".join(EXPECTED_COLUMNS[name]) + "\n"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"content-disposition": f'attachment; filename="{name}"'},
    )


@router.post("/uploads")
async def create_upload(files: list[UploadFile] = File(...)):
    """Accept the dataset CSVs, validate the fixed schema, persist under uploads/<id>/."""
    upload_id = uuid4().hex[:12]
    dest = UPLOADS_DIR / upload_id
    dest.mkdir(parents=True, exist_ok=True)
    try:
        for f in files:
            name = Path(f.filename or "").name
            if name not in EXPECTED_COLUMNS:
                raise HTTPException(400, f"unexpected file: {name or '(unnamed)'} "
                                         f"(expected one of {REQUIRED_FILES})")
            content = await f.read()
            if len(content) > MAX_UPLOAD_BYTES:
                raise HTTPException(400, f"{name}: exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")
            (dest / name).write_bytes(content)
        errors = validate_upload(dest)
        if errors:
            raise HTTPException(400, {"errors": errors})
    except HTTPException:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return {"upload_id": upload_id, "files": sorted(p.name for p in dest.glob("*.csv")), "ok": True}


# --------------------------------------------------------------------------- #
# Compute (the what-if workhorse) + persisted runs
# --------------------------------------------------------------------------- #
@router.post("/compute", response_model=ComputeResponse)
def compute(req: ComputeRequest) -> ComputeResponse:
    """Recompute with config overrides (live what-if) — no persistence.

    Runs all three engines against a built-in scenario OR an uploaded dataset.
    """
    if req.upload_id:
        base = load_scenario("baseline")  # baseline rules are the template for custom data
        data_dir = str(_upload_data_dir(req.upload_id))
    else:
        base = _ensure_scenario_data(req.scenario)
        data_dir = base.settings.data_dir
    result = compute_with_overrides(req.config_overrides, base_config=base, data_dir=data_dir)
    return ComputeResponse(
        run_id=result.run_id,
        summary=result.summary(),
        verification=result.verification,
        borrowing_base=result.certificate,
        fccr=result.fccr,
    )


@router.post("/compute/certificate.html", response_class=HTMLResponse)
def compute_certificate_html(req: ComputeRequest) -> str:
    """Render the bank-ready borrowing-base certificate for the LIVE what-if state.

    Same source resolution as ``/compute``, but returns the print-styled standalone
    HTML (the persisted-run renderer, applied to live results) — the downloadable
    deliverable, reflecting any config overrides.
    """
    base, data_dir = _resolve_source(req)
    result = compute_with_overrides(req.config_overrides, base_config=base, data_dir=data_dir)
    return renderer.render_certificate(result.certificate.model_dump(mode="json"))


@router.post("/sensitivity")
def sensitivity_route(req: SensitivityRequest) -> dict:
    """One-at-a-time sensitivity on the headline outputs (tornado-chart fodder).

    Resolves the base config + dataset exactly like /compute, applies
    config_overrides onto the base first, then varies each default lever by
    a relative -10% (the covenant threshold by +10%) and reports the impact.
    """
    if req.upload_id:
        base = load_scenario("baseline")  # baseline rules are the template for custom data
        data_dir = str(_upload_data_dir(req.upload_id))
    else:
        base = _ensure_scenario_data(req.scenario)
        data_dir = base.settings.data_dir

    if req.config_overrides:
        merged = _deep_merge(base.model_dump(mode="json"), req.config_overrides)
        base = Config.model_validate(merged)

    levers = sensitivity(base, data_dir, DEFAULT_LEVERS)
    return {"levers": levers}


@router.post("/goal-seek")
def goal_seek_route(req: GoalSeekRequest) -> dict:
    """Reverse-solve a single lever for a target excess availability.

    Resolves the base config + dataset exactly like /sensitivity (applying
    config_overrides onto the base first), then binary-searches the lever's
    [0, 1] domain for the smallest value that meets the target.
    """
    if req.upload_id:
        base = load_scenario("baseline")  # baseline rules are the template for custom data
        data_dir = str(_upload_data_dir(req.upload_id))
    else:
        base = _ensure_scenario_data(req.scenario)
        data_dir = base.settings.data_dir

    if req.config_overrides:
        merged = _deep_merge(base.model_dump(mode="json"), req.config_overrides)
        base = Config.model_validate(merged)

    try:
        target = Decimal(req.target_value)
    except (InvalidOperation, ValueError):
        raise HTTPException(400, f"invalid target_value: {req.target_value!r}") from None

    try:
        return goal_seek(base, data_dir, req.lever, target)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# --------------------------------------------------------------------------- #
# AI briefing + ask-the-data
# --------------------------------------------------------------------------- #
def _resolve_source(req) -> tuple[Config, str]:
    """(base config, data_dir) for a scenario or an uploaded dataset — same rule as /compute."""
    if req.upload_id:
        return load_scenario("baseline"), str(_upload_data_dir(req.upload_id))
    base = _ensure_scenario_data(req.scenario)
    return base, base.settings.data_dir


@router.post("/briefing")
def briefing_route(req: ComputeRequest) -> dict:
    """Executive briefing over the live results (AI when a key is set, else a rule-generated memo)."""
    base, data_dir = _resolve_source(req)
    result = compute_with_overrides(req.config_overrides, base_config=base, data_dir=data_dir)
    text, generated_by = ai_briefing.generate_briefing(ai_briefing.build_context(result))
    return {"briefing": text, "generated_by": generated_by}


@router.post("/ask")
def ask_route(req: AskRequest):
    """Stream an answer to a free-text question, grounded in the live results (SSE)."""
    base, data_dir = _resolve_source(req)
    result = compute_with_overrides(req.config_overrides, base_config=base, data_dir=data_dir)
    context = ai_briefing.build_context(result)

    def event_stream():
        for delta in ai_briefing.answer_question_stream(context, req.question):
            yield f"data: {json.dumps({'delta': delta})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/pipeline/run")
def pipeline_run(generate: bool = Query(True, description="Regenerate synthetic data first")):
    if generate:
        datagen.generate()
    result = run_pipeline(render=True)
    return {"run_id": result.run_id, "summary": result.summary(), "artifacts": result.artifacts}


@router.get("/runs")
def list_runs(conn=Depends(get_conn)):
    return ResultRepository(conn).list_runs()


def _fetch(conn, run_id: str, path_key: str) -> dict:
    engine = _ENGINE_BY_PATH.get(path_key)
    if engine is None:
        raise HTTPException(404, f"unknown engine: {path_key}")
    payload = ResultRepository(conn).get_result(run_id, engine)
    if payload is None:
        raise HTTPException(404, f"no {engine} result for run {run_id}")
    return payload


@router.get("/runs/{run_id}/verification", response_model=VerificationReport)
def get_verification(run_id: str, conn=Depends(get_conn)):
    return _fetch(conn, run_id, "verification")


@router.get("/runs/{run_id}/borrowing-base", response_model=BorrowingBaseCertificate)
def get_borrowing_base(run_id: str, conn=Depends(get_conn)):
    return _fetch(conn, run_id, "borrowing-base")


@router.get("/runs/{run_id}/fccr", response_model=FccrReport)
def get_fccr(run_id: str, conn=Depends(get_conn)):
    return _fetch(conn, run_id, "fccr")


@router.get("/runs/{run_id}/verification.html", response_class=HTMLResponse)
def get_verification_html(run_id: str, conn=Depends(get_conn)):
    return _RENDERERS["verification"](_fetch(conn, run_id, "verification"))


@router.get("/runs/{run_id}/borrowing-base.html", response_class=HTMLResponse)
def get_borrowing_base_html(run_id: str, conn=Depends(get_conn)):
    return _RENDERERS["borrowing_base"](_fetch(conn, run_id, "borrowing-base"))


@router.get("/runs/{run_id}/fccr.html", response_class=HTMLResponse)
def get_fccr_html(run_id: str, conn=Depends(get_conn)):
    return _RENDERERS["fccr"](_fetch(conn, run_id, "fccr"))


# --------------------------------------------------------------------------- #
# Provenance drill-down (scenario-aware)
# --------------------------------------------------------------------------- #
@router.get("/facts")
def get_facts(
    scenario: str = Query("baseline"),
    upload_id: str | None = Query(None),
    dataset: str | None = Query(None),
    metric: str | None = Query(None),
    entity: str | None = Query(None),
):
    """The source facts behind the numbers — for a scenario or an upload (UI provenance)."""
    if upload_id:
        config = load_scenario("baseline")
        data_dir = _upload_data_dir(upload_id)
    else:
        config = _ensure_scenario_data(scenario)
        data_dir = config.settings.data_dir
    conn = connect(":memory:")
    init_schema(conn)
    repo = FactRepository(conn)
    repo.add_many(load_all(data_dir, config.facility.as_of_date))
    facts = repo.query(dataset=dataset, metric=metric, entity=entity)
    return [f.model_dump(mode="json") for f in facts]
