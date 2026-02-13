"""Background health-check worker for eval discrimination and saturation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from orchestrator.db.connection import get_cursor, init_pool
from orchestrator.db.health_repo import upsert_eval_health

logger = logging.getLogger(__name__)

# Thresholds for lifecycle transitions
DISCRIMINATION_ACTIVE = 0.15
DISCRIMINATION_WATCH = 0.08
WATCH_DAYS_TO_SATURATE = 90


def run_health_check() -> dict[str, Any]:
    """Compute discrimination and saturation for all evals with completed runs.

    Reuses the same algorithms as sdk/src/aeval/stats/discrimination.py
    (inlined to avoid cross-package import in the orchestrator container).

    Returns summary of updates.
    """
    init_pool()

    evals = _get_evals_with_runs()
    updated = 0
    results: list[dict[str, Any]] = []

    for ev in evals:
        eval_id = ev["id"]
        eval_name = ev["name"]

        scores_by_model = _gather_scores(eval_id)
        if len(scores_by_model) < 2:
            continue

        disc = _discrimination_power(scores_by_model)
        sat = _detect_saturation(scores_by_model)

        new_state = _determine_lifecycle(eval_id, disc)

        record = upsert_eval_health(
            eval_id,
            discrimination_power=disc,
            saturation_type=sat.get("type"),
            lifecycle_state=new_state,
            scores_by_model={
                model: float(sum(scores) / len(scores))
                for model, scores in scores_by_model.items()
            },
        )
        updated += 1
        results.append({
            "eval_name": eval_name,
            "discrimination": disc,
            "saturation_type": sat.get("type"),
            "lifecycle_state": new_state,
        })

    return {"updated": updated, "evals": results}


def _get_evals_with_runs() -> list[dict[str, Any]]:
    """Get all eval definitions that have at least one completed run."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT e.id, e.name
            FROM eval_definitions e
            JOIN eval_runs r ON e.id = r.eval_id
            WHERE r.status = 'completed'
            ORDER BY e.name
            """
        )
        return [dict(r) for r in cur.fetchall()]


def _gather_scores(eval_id: int) -> dict[str, list[float]]:
    """Gather per-model scores for an eval from completed runs."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT m.name AS model_name, er.score
            FROM eval_results er
            JOIN eval_runs r ON er.run_id = r.id
            JOIN models m ON r.model_id = m.id
            WHERE r.eval_id = %s AND r.status = 'completed'
            ORDER BY m.name
            """,
            (eval_id,),
        )
        scores_by_model: dict[str, list[float]] = {}
        for row in cur.fetchall():
            model = row["model_name"]
            if model not in scores_by_model:
                scores_by_model[model] = []
            scores_by_model[model].append(float(row["score"]))
        return scores_by_model


def _determine_lifecycle(eval_id: int, discrimination: float) -> str:
    """Determine the lifecycle state based on discrimination and current state."""
    if discrimination > DISCRIMINATION_ACTIVE:
        return "active"

    if discrimination >= DISCRIMINATION_WATCH:
        return "watch"

    # Below DISCRIMINATION_WATCH — check if in watch long enough
    current = _get_current_state(eval_id)
    if current and current.get("lifecycle_state") == "watch":
        entered = current.get("watch_entered_at")
        if entered:
            if isinstance(entered, str):
                entered = datetime.fromisoformat(entered)
            days_in_watch = (datetime.now(timezone.utc) - entered).days
            if days_in_watch >= WATCH_DAYS_TO_SATURATE:
                return "saturated"
        return "watch"

    # Not yet in watch — transition to watch first
    if current and current.get("lifecycle_state") == "saturated":
        return "saturated"
    if current and current.get("lifecycle_state") == "archived":
        return "archived"
    return "watch"


def _get_current_state(eval_id: int) -> dict[str, Any] | None:
    """Get the current health record for an eval."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT lifecycle_state, watch_entered_at FROM eval_health WHERE eval_id = %s",
            (eval_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


# ---- Inlined stat functions (mirror sdk/src/aeval/stats/discrimination.py) ----


def _discrimination_power(scores_by_model: dict[str, list[float]]) -> float:
    """Compute discrimination power = between-model variance / total variance."""
    if len(scores_by_model) < 2:
        return 0.0

    all_scores: list[float] = []
    model_means: list[float] = []
    for scores in scores_by_model.values():
        if not scores:
            continue
        all_scores.extend(scores)
        model_means.append(sum(scores) / len(scores))

    if not all_scores or len(model_means) < 2:
        return 0.0

    total_mean = sum(all_scores) / len(all_scores)
    total_var = sum((s - total_mean) ** 2 for s in all_scores) / len(all_scores)
    if total_var == 0:
        return 0.0

    between_mean = sum(model_means) / len(model_means)
    between_var = sum((m - between_mean) ** 2 for m in model_means) / len(model_means)
    return min(between_var / total_var, 1.0)


def _detect_saturation(
    scores_by_model: dict[str, list[float]],
    ceiling_threshold: float = 0.95,
    floor_threshold: float = 0.10,
    ceiling_ratio: float = 0.90,
    floor_ratio: float = 0.90,
) -> dict[str, Any]:
    """Detect eval saturation (ceiling, floor, or noise)."""
    if not scores_by_model:
        return {"saturated": False, "type": None}

    model_means: dict[str, float] = {}
    for name, scores in scores_by_model.items():
        if scores:
            model_means[name] = sum(scores) / len(scores)

    if not model_means:
        return {"saturated": False, "type": None}

    n_models = len(model_means)
    at_ceiling = sum(1 for m in model_means.values() if m > ceiling_threshold)
    at_floor = sum(1 for m in model_means.values() if m < floor_threshold)

    if at_ceiling / n_models >= ceiling_ratio:
        return {"saturated": True, "type": "ceiling"}

    if at_floor / n_models >= floor_ratio:
        return {"saturated": True, "type": "floor"}

    disc = _discrimination_power(scores_by_model)
    if disc < 0.08:
        return {"saturated": True, "type": "noise"}

    return {"saturated": False, "type": None}
