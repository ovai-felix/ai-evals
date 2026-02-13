"""Pydantic models for the registry API."""

from __future__ import annotations

from pydantic import BaseModel


class EvalMeta(BaseModel):
    """Eval metadata as stored in meta.yaml."""

    name: str
    version: str = ""
    description: str = ""
    category: str = ""
    tags: list[str] = []
    threshold: float | None = None
    dataset: str = ""


class EvalDetail(EvalMeta):
    """Eval detail with code preview."""

    code_preview: str = ""
    dataset_size: int = 0


class SuiteResponse(BaseModel):
    """Suite definition."""

    name: str
    description: str = ""
    evals: list[str] = []
    timeout: str = "30m"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    registry_data: bool
    eval_count: int
