"""API route handlers for the registry service."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from registry.src.schemas import EvalDetail, EvalMeta, HealthResponse, SuiteResponse
from registry.src.storage import get_eval, list_evals, list_suites, search_evals

router = APIRouter(prefix="/api/v1")


@router.get("/evals", response_model=list[EvalMeta])
def list_evals_endpoint():
    """List all registered evals."""
    return list_evals()


@router.get("/evals/{name}", response_model=EvalDetail)
def get_eval_endpoint(name: str):
    """Get detailed info for a specific eval."""
    result = get_eval(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Eval not found: {name}")
    return result


@router.get("/search", response_model=list[EvalMeta])
def search_endpoint(q: str = Query(..., min_length=1)):
    """Search for evals by name, tag, category, or description."""
    return search_evals(q)


@router.get("/suites", response_model=list[SuiteResponse])
def list_suites_endpoint():
    """List all available eval suites."""
    return list_suites()


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check for the registry service."""
    evals = list_evals()
    return HealthResponse(
        status="healthy",
        registry_data=len(evals) > 0,
        eval_count=len(evals),
    )
