"""Pydantic request/response models for the orchestrator API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Requests ---


class SubmitRunRequest(BaseModel):
    eval_name: str = Field(..., description="Eval name or path to .py file")
    model: str = Field(..., description="Model spec (e.g., 'gemma3:4b')")
    threshold: float | None = Field(None, description="Override pass/fail threshold")
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Responses ---


class ConfidenceIntervalResponse(BaseModel):
    lower: float
    upper: float
    level: float = 0.95


class RunSummary(BaseModel):
    id: str
    eval_name: str
    model_name: str
    status: str
    score: float | None = None
    ci: ConfidenceIntervalResponse | None = None
    num_tasks: int | None = None
    passed: bool | None = None
    threshold: float | None = None
    error: str | None = None
    submitted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskResultResponse(BaseModel):
    task_id: str
    score: float
    passed: bool | None = None
    prediction: str = ""
    reference: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    time: datetime | None = None


class RunDetailResponse(RunSummary):
    results: list[TaskResultResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubmitRunResponse(BaseModel):
    id: str
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    db: bool
    redis: bool
    ollama: bool


class ModelResponse(BaseModel):
    name: str
    family: str = ""
    parameter_size: str = ""
    quantization: str = ""
    multimodal: bool = False
    digest: str = ""


# --- Taxonomy & Health ---


class TaxonomyNodeResponse(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    description: str = ""
    level: int = 0
    eval_count: int = 0
    avg_discrimination: float = 0.0
    children: list["TaxonomyNodeResponse"] = Field(default_factory=list)
    evals: list[dict[str, Any]] = Field(default_factory=list)


class EvalHealthResponse(BaseModel):
    eval_id: int
    eval_name: str
    discrimination_power: float = 0.0
    saturation_type: str | None = None
    lifecycle_state: str = "active"
    last_checked: datetime | None = None


class CoverageSummaryResponse(BaseModel):
    total_categories: int = 0
    total_nodes: int = 0
    covered_nodes: int = 0
    gap_count: int = 0
    coverage_pct: float = 0.0
    saturation_rate: float = 0.0
    avg_discrimination: float = 0.0
    active_count: int = 0
    watch_count: int = 0
    saturated_count: int = 0
    archived_count: int = 0


class GenerateRequest(BaseModel):
    taxonomy_node: str | None = Field(None, description="Taxonomy node name to generate evals for")
    method: str | None = Field(None, description="Generation method: capability_probe, adversarial, difficulty_escalation")
    count: int | None = Field(5, description="Number of tasks to generate", ge=1, le=20)


class GenerateResponse(BaseModel):
    generated_evals: list[str] = Field(default_factory=list)
    message: str = ""
