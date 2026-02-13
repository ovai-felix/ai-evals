"""API routes for taxonomy, health monitoring, and intelligence."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query

from orchestrator.api.schemas import (
    CoverageSummaryResponse,
    EvalHealthResponse,
    GenerateRequest,
    GenerateResponse,
    TaxonomyNodeResponse,
)
from orchestrator.db.health_repo import list_eval_health
from orchestrator.db.taxonomy_repo import (
    get_node,
    get_node_evals,
    get_taxonomy_tree,
)
from orchestrator.intelligence.monitor import run_health_check
from orchestrator.intelligence.taxonomy import coverage_summary
from orchestrator.intelligence.generator import (
    generate_adversarial,
    generate_capability_probe,
    generate_difficulty_escalation,
    store_generated_eval,
)

logger = logging.getLogger(__name__)

health_router = APIRouter(prefix="/api/v1")


def _tree_to_response(node: dict) -> TaxonomyNodeResponse:
    """Convert a taxonomy tree dict to a response model."""
    return TaxonomyNodeResponse(
        id=node["id"],
        parent_id=node.get("parent_id"),
        name=node["name"],
        description=node.get("description", ""),
        level=node.get("level", 0),
        eval_count=node.get("eval_count", 0),
        avg_discrimination=node.get("avg_discrimination", 0.0),
        children=[_tree_to_response(c) for c in node.get("children", [])],
    )


@health_router.get("/taxonomy", response_model=list[TaxonomyNodeResponse])
def get_taxonomy():
    """Get the full capability taxonomy tree."""
    tree = get_taxonomy_tree()
    return [_tree_to_response(node) for node in tree]


@health_router.get("/taxonomy/{node_id}", response_model=TaxonomyNodeResponse)
def get_taxonomy_node(node_id: int):
    """Get a taxonomy node with its children and mapped evals."""
    node = get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Taxonomy node not found: {node_id}")

    evals = get_node_evals(node_id)
    node["eval_count"] = len(evals)
    avg_disc = (
        sum(e.get("discrimination_power") or 0 for e in evals) / len(evals)
        if evals
        else 0.0
    )
    node["avg_discrimination"] = avg_disc

    resp = _tree_to_response(node)
    resp.evals = [
        {
            "id": e["id"],
            "name": e["name"],
            "discrimination_power": e.get("discrimination_power"),
            "lifecycle_state": e.get("lifecycle_state"),
        }
        for e in evals
    ]
    return resp


@health_router.get("/health/evals", response_model=list[EvalHealthResponse])
def get_eval_health_list(
    lifecycle_state: str | None = Query(None),
):
    """List eval health records, optionally filtered by lifecycle state."""
    records = list_eval_health(lifecycle_state=lifecycle_state)
    return [
        EvalHealthResponse(
            eval_id=r["eval_id"],
            eval_name=r["eval_name"],
            discrimination_power=r["discrimination_power"],
            saturation_type=r.get("saturation_type"),
            lifecycle_state=r["lifecycle_state"],
            last_checked=r.get("last_checked"),
        )
        for r in records
    ]


@health_router.get("/health/coverage", response_model=CoverageSummaryResponse)
def get_coverage():
    """Get coverage summary across the taxonomy."""
    summary = coverage_summary()
    return CoverageSummaryResponse(**summary)


@health_router.post("/health/refresh")
def refresh_health():
    """Run health check on all evals and update metrics."""
    result = run_health_check()
    return {"status": "ok", "updated": result["updated"], "evals": result["evals"]}


@health_router.post("/intelligence/generate", response_model=GenerateResponse)
def generate_evals(req: GenerateRequest):
    """Generate candidate eval tasks using LLM."""
    method = req.method or "capability_probe"
    count = req.count or 5
    node_name = req.taxonomy_node

    if not node_name:
        raise HTTPException(
            status_code=400,
            detail="taxonomy_node is required for generation",
        )

    try:
        if method == "capability_probe":
            tasks = generate_capability_probe(
                node_name=node_name,
                node_description=f"Evaluation tasks for {node_name}",
                count=count,
            )
        elif method == "adversarial":
            tasks = generate_adversarial(
                node_name=node_name,
                existing_tasks=[],
                count=count,
            )
        elif method == "difficulty_escalation":
            tasks = generate_difficulty_escalation(
                eval_name=node_name,
                existing_tasks=[],
                count=count,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown method: {method}. Use capability_probe, adversarial, or difficulty_escalation",
            )

        if not tasks:
            return GenerateResponse(
                generated_evals=[],
                message="No tasks passed quality gates. Try again or use a different model.",
            )

        # Store as eval package
        safe_name = node_name.lower().replace(" ", "-").replace("/", "-")
        eval_name = f"gen-{safe_name}-{method}"
        store_generated_eval(
            tasks=tasks,
            eval_name=eval_name,
            generation_method=method,
            taxonomy_node=node_name,
        )

        return GenerateResponse(
            generated_evals=[eval_name],
            message=f"Generated {len(tasks)} tasks for '{node_name}' using {method}",
        )

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach LLM service: {e}",
        )
    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=str(e))
