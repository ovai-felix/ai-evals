"""Repository for eval_runs and eval_results tables."""

from __future__ import annotations

import json
from typing import Any

from orchestrator.db.connection import get_cursor


def create_run(
    eval_id: int,
    model_id: int,
    threshold: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new eval run in pending state."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO eval_runs (eval_id, model_id, threshold, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (eval_id, model_id, threshold, json.dumps(metadata or {})),
        )
        return dict(cur.fetchone())


def update_run_status(
    run_id: str,
    status: str,
    *,
    score: float | None = None,
    ci_lower: float | None = None,
    ci_upper: float | None = None,
    ci_level: float | None = None,
    num_tasks: int | None = None,
    passed: bool | None = None,
    tier: str | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update a run's status and optional result fields."""
    with get_cursor() as cur:
        set_clauses = ["status = %s"]
        params: list[Any] = [status]

        if status == "running":
            set_clauses.append("started_at = NOW()")
        elif status in ("completed", "failed"):
            set_clauses.append("completed_at = NOW()")

        if score is not None:
            set_clauses.append("score = %s")
            params.append(score)
        if ci_lower is not None:
            set_clauses.append("ci_lower = %s")
            params.append(ci_lower)
        if ci_upper is not None:
            set_clauses.append("ci_upper = %s")
            params.append(ci_upper)
        if ci_level is not None:
            set_clauses.append("ci_level = %s")
            params.append(ci_level)
        if num_tasks is not None:
            set_clauses.append("num_tasks = %s")
            params.append(num_tasks)
        if passed is not None:
            set_clauses.append("passed = %s")
            params.append(passed)
        if tier is not None:
            set_clauses.append("tier = %s")
            params.append(tier)
        if error is not None:
            set_clauses.append("error = %s")
            params.append(error)
        if metadata is not None:
            set_clauses.append("metadata = metadata || %s::jsonb")
            params.append(json.dumps(metadata))

        params.append(run_id)
        cur.execute(
            f"UPDATE eval_runs SET {', '.join(set_clauses)} WHERE id = %s RETURNING *",
            params,
        )
        row = cur.fetchone()
        return dict(row) if row else {}


def store_results(run_id: str, task_results: list[dict[str, Any]]) -> int:
    """Bulk-insert per-task results for a run."""
    if not task_results:
        return 0
    with get_cursor() as cur:
        values = []
        params: list[Any] = []
        for tr in task_results:
            values.append("(NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            params.extend([
                run_id,
                tr.get("task_id", ""),
                tr.get("score", 0.0),
                tr.get("passed"),
                tr.get("prediction", ""),
                tr.get("reference", ""),
                tr.get("latency_ms", 0.0),
                tr.get("tokens_used", 0),
                json.dumps(tr.get("metadata", {})),
            ])
        cur.execute(
            f"""
            INSERT INTO eval_results (time, run_id, task_id, score, passed, prediction, reference, latency_ms, tokens_used, metadata)
            VALUES {', '.join(values)}
            """,
            params,
        )
        return len(task_results)


def get_run(run_id: str) -> dict[str, Any] | None:
    """Get a single run with eval and model names."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT r.*, e.name AS eval_name, m.name AS model_name
            FROM eval_runs r
            JOIN eval_definitions e ON r.eval_id = e.id
            JOIN models m ON r.model_id = m.id
            WHERE r.id = %s
            """,
            (run_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_runs(
    eval_name: str | None = None,
    model: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List runs with optional filters."""
    with get_cursor() as cur:
        conditions = []
        params: list[Any] = []

        if eval_name:
            conditions.append("e.name = %s")
            params.append(eval_name)
        if model:
            conditions.append("m.name = %s")
            params.append(model)
        if status:
            conditions.append("r.status = %s")
            params.append(status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        params.extend([limit, offset])
        cur.execute(
            f"""
            SELECT r.*, e.name AS eval_name, m.name AS model_name
            FROM eval_runs r
            JOIN eval_definitions e ON r.eval_id = e.id
            JOIN models m ON r.model_id = m.id
            {where}
            ORDER BY r.submitted_at DESC
            LIMIT %s OFFSET %s
            """,
            params,
        )
        return [dict(row) for row in cur.fetchall()]


def get_run_results(run_id: str) -> list[dict[str, Any]]:
    """Get per-task results for a run."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT task_id, score, passed, prediction, reference,
                   latency_ms, tokens_used, metadata, time
            FROM eval_results
            WHERE run_id = %s
            ORDER BY time ASC
            """,
            (run_id,),
        )
        return [dict(row) for row in cur.fetchall()]
