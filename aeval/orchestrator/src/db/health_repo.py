"""Repository for the eval_health table."""

from __future__ import annotations

import json
from typing import Any

from orchestrator.db.connection import get_cursor


def upsert_eval_health(
    eval_id: int,
    *,
    discrimination_power: float = 0.0,
    saturation_type: str | None = None,
    lifecycle_state: str = "active",
    scores_by_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert or update health metrics for an eval."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO eval_health
                (eval_id, discrimination_power, saturation_type,
                 lifecycle_state, scores_by_model, last_checked)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (eval_id) DO UPDATE SET
                discrimination_power = EXCLUDED.discrimination_power,
                saturation_type = EXCLUDED.saturation_type,
                lifecycle_state = CASE
                    WHEN eval_health.lifecycle_state != EXCLUDED.lifecycle_state
                    THEN EXCLUDED.lifecycle_state
                    ELSE eval_health.lifecycle_state
                END,
                scores_by_model = EXCLUDED.scores_by_model,
                last_checked = NOW(),
                state_changed_at = CASE
                    WHEN eval_health.lifecycle_state != EXCLUDED.lifecycle_state
                    THEN NOW()
                    ELSE eval_health.state_changed_at
                END,
                watch_entered_at = CASE
                    WHEN EXCLUDED.lifecycle_state = 'watch'
                         AND eval_health.lifecycle_state != 'watch'
                    THEN NOW()
                    WHEN EXCLUDED.lifecycle_state != 'watch'
                    THEN NULL
                    ELSE eval_health.watch_entered_at
                END
            RETURNING *
            """,
            (
                eval_id,
                discrimination_power,
                saturation_type,
                lifecycle_state,
                json.dumps(scores_by_model or {}),
            ),
        )
        return dict(cur.fetchone())


def get_eval_health(eval_id: int) -> dict[str, Any] | None:
    """Get health record for a single eval."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT h.*, e.name AS eval_name
            FROM eval_health h
            JOIN eval_definitions e ON h.eval_id = e.id
            WHERE h.eval_id = %s
            """,
            (eval_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_eval_health(
    lifecycle_state: str | None = None,
) -> list[dict[str, Any]]:
    """List all eval health records, optionally filtered by lifecycle state."""
    with get_cursor() as cur:
        if lifecycle_state:
            cur.execute(
                """
                SELECT h.*, e.name AS eval_name
                FROM eval_health h
                JOIN eval_definitions e ON h.eval_id = e.id
                WHERE h.lifecycle_state = %s
                ORDER BY e.name
                """,
                (lifecycle_state,),
            )
        else:
            cur.execute(
                """
                SELECT h.*, e.name AS eval_name
                FROM eval_health h
                JOIN eval_definitions e ON h.eval_id = e.id
                ORDER BY e.name
                """
            )
        return [dict(r) for r in cur.fetchall()]


def transition_lifecycle(eval_id: int, new_state: str) -> dict[str, Any] | None:
    """Transition an eval's lifecycle state with timestamp tracking."""
    valid = {"active", "watch", "saturated", "archived"}
    if new_state not in valid:
        raise ValueError(f"Invalid lifecycle state: {new_state}. Must be one of {valid}")

    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE eval_health SET
                lifecycle_state = %s,
                state_changed_at = NOW(),
                watch_entered_at = CASE
                    WHEN %s = 'watch' AND lifecycle_state != 'watch' THEN NOW()
                    WHEN %s != 'watch' THEN NULL
                    ELSE watch_entered_at
                END
            WHERE eval_id = %s
            RETURNING *
            """,
            (new_state, new_state, new_state, eval_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_health_summary() -> dict[str, Any]:
    """Get aggregate health statistics across all evals."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) AS total_evals,
                COUNT(CASE WHEN lifecycle_state = 'active' THEN 1 END) AS active_count,
                COUNT(CASE WHEN lifecycle_state = 'watch' THEN 1 END) AS watch_count,
                COUNT(CASE WHEN lifecycle_state = 'saturated' THEN 1 END) AS saturated_count,
                COUNT(CASE WHEN lifecycle_state = 'archived' THEN 1 END) AS archived_count,
                COALESCE(AVG(discrimination_power), 0) AS avg_discrimination
            FROM eval_health
            """
        )
        row = cur.fetchone()
        return dict(row) if row else {}
