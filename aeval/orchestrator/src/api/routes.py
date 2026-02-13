"""API route handlers for the orchestrator."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query

from orchestrator.api.schemas import (
    ConfidenceIntervalResponse,
    HealthResponse,
    ModelResponse,
    RunDetailResponse,
    RunSummary,
    SubmitRunRequest,
    SubmitRunResponse,
    TaskResultResponse,
)
from orchestrator.db.runs_repo import get_run, get_run_results, list_runs
from orchestrator.engine.queue import enqueue_run, get_redis_conn

router = APIRouter(prefix="/api/v1")


@router.post("/runs", response_model=SubmitRunResponse, status_code=202)
def submit_run(req: SubmitRunRequest):
    """Submit an eval run for async execution."""
    # Resolve eval file path
    eval_file = _resolve_eval_file(req.eval_name)
    if eval_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"Eval not found: {req.eval_name}",
        )

    # Fetch model info from Ollama if available
    model_name = req.model.removeprefix("ollama:")
    model_info = _fetch_model_info(model_name)

    run = enqueue_run(
        eval_name=_eval_name_from_file(req.eval_name, eval_file),
        eval_file=eval_file,
        model_name=model_name,
        threshold=req.threshold,
        model_family=model_info.get("family", ""),
        model_param_size=model_info.get("parameter_size", ""),
        model_quant=model_info.get("quantization", ""),
        model_multimodal=model_info.get("multimodal", False),
        model_digest=model_info.get("digest", ""),
        metadata=req.metadata,
    )

    return SubmitRunResponse(
        id=str(run["id"]),
        status="pending",
        message="Run submitted successfully",
    )


@router.get("/runs", response_model=list[RunSummary])
def list_runs_endpoint(
    eval_name: str | None = Query(None),
    model: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List eval runs with optional filters."""
    runs = list_runs(
        eval_name=eval_name,
        model=model,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [_run_to_summary(r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run_detail(run_id: str):
    """Get detailed info for a single run, including per-task results."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    results = get_run_results(run_id)
    summary = _run_to_summary(run)

    return RunDetailResponse(
        **summary.model_dump(),
        results=[
            TaskResultResponse(
                task_id=r["task_id"],
                score=r["score"],
                passed=r["passed"],
                prediction=r["prediction"],
                reference=r["reference"],
                latency_ms=r["latency_ms"],
                tokens_used=r["tokens_used"],
                metadata=r["metadata"] if isinstance(r["metadata"], dict) else {},
                time=r["time"],
            )
            for r in results
        ],
        metadata=run.get("metadata", {}) if isinstance(run.get("metadata"), dict) else {},
    )


@router.get("/results", response_model=list[RunSummary])
def query_results(
    eval_name: str | None = Query(None),
    model: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Query completed results across runs."""
    runs = list_runs(
        eval_name=eval_name,
        model=model,
        status="completed",
        limit=limit,
        offset=offset,
    )
    return [_run_to_summary(r) for r in runs]


@router.get("/models", response_model=list[ModelResponse])
def list_models():
    """Proxy to Ollama /api/tags to list available models."""
    ollama_host = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
    try:
        with httpx.Client(base_url=ollama_host, timeout=10) as client:
            resp = client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Cannot reach Ollama")

    models = []
    for m in data.get("models", []):
        details = m.get("details", {})
        families = details.get("families", [])
        models.append(
            ModelResponse(
                name=m.get("name", ""),
                family=details.get("family", ""),
                parameter_size=details.get("parameter_size", ""),
                quantization=details.get("quantization_level", ""),
                multimodal=any("clip" in f.lower() for f in families) if families else False,
                digest=m.get("digest", "")[:12],
            )
        )
    return models


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Check connectivity to DB, Redis, and Ollama."""
    db_ok = _check_db()
    redis_ok = _check_redis()
    ollama_ok = _check_ollama()

    all_ok = db_ok and redis_ok and ollama_ok
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        db=db_ok,
        redis=redis_ok,
        ollama=ollama_ok,
    )


# --- Helpers ---


def _run_to_summary(run: dict) -> RunSummary:
    ci = None
    if run.get("ci_lower") is not None and run.get("ci_upper") is not None:
        ci = ConfidenceIntervalResponse(
            lower=run["ci_lower"],
            upper=run["ci_upper"],
            level=run.get("ci_level", 0.95),
        )

    return RunSummary(
        id=str(run["id"]),
        eval_name=run["eval_name"],
        model_name=run["model_name"],
        status=run["status"],
        score=run.get("score"),
        ci=ci,
        num_tasks=run.get("num_tasks"),
        passed=run.get("passed"),
        threshold=run.get("threshold"),
        error=run.get("error"),
        submitted_at=run["submitted_at"],
        started_at=run.get("started_at"),
        completed_at=run.get("completed_at"),
    )


def _resolve_eval_file(eval_name: str) -> str | None:
    """Find an eval file by name or path."""
    # Direct path
    path = Path(eval_name)
    if path.exists() and path.suffix == ".py":
        return str(path)

    # Search in evals directory
    evals_dir = Path("/app/evals")
    if evals_dir.exists():
        for candidate in evals_dir.rglob("*.py"):
            if (
                candidate.stem == eval_name
                or candidate.stem.replace("_", "-") == eval_name
            ):
                return str(candidate)

    # Search in registry-data directory by meta.yaml name match
    registry_dir = Path("/app/registry-data")
    if registry_dir.exists():
        for meta_file in registry_dir.rglob("meta.yaml"):
            try:
                import yaml
                with open(meta_file) as f:
                    meta = yaml.safe_load(f) or {}
                if meta.get("name") == eval_name:
                    eval_file = meta_file.parent / "eval.py"
                    if eval_file.exists():
                        return str(eval_file)
            except Exception:
                continue

    # Try with evals/ prefix
    prefixed = Path("evals") / eval_name
    if prefixed.exists():
        return str(prefixed)
    if prefixed.with_suffix(".py").exists():
        return str(prefixed.with_suffix(".py"))

    return None


def _eval_name_from_file(eval_name: str, eval_file: str) -> str:
    """Derive a clean eval name."""
    # If the user provided a clean name (no path separators, no .py), use it
    if "/" not in eval_name and not eval_name.endswith(".py"):
        return eval_name

    # Otherwise derive from file stem
    stem = Path(eval_file).stem
    return stem.replace("_", "-")


def _fetch_model_info(model_name: str) -> dict:
    """Fetch model info from Ollama, returning empty dict on failure."""
    ollama_host = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
    try:
        with httpx.Client(base_url=ollama_host, timeout=5) as client:
            resp = client.post("/api/show", json={"model": model_name})
            resp.raise_for_status()
            data = resp.json()
            details = data.get("details", {})
            return {
                "family": details.get("family", ""),
                "parameter_size": details.get("parameter_size", ""),
                "quantization": details.get("quantization_level", ""),
                "multimodal": "clip" in str(details.get("families", [])).lower(),
                "digest": data.get("digest", ""),
            }
    except Exception:
        return {}


def _check_db() -> bool:
    try:
        from orchestrator.db.connection import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        conn = get_redis_conn()
        conn.ping()
        return True
    except Exception:
        return False


def _check_ollama() -> bool:
    ollama_host = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
    try:
        with httpx.Client(base_url=ollama_host, timeout=5) as client:
            resp = client.get("/")
            return resp.status_code == 200
    except Exception:
        return False
