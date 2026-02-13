"""Repository for taxonomy_nodes and taxonomy_eval_map tables."""

from __future__ import annotations

from typing import Any

from orchestrator.db.connection import get_cursor


def get_taxonomy_tree() -> list[dict[str, Any]]:
    """Return the full taxonomy as a nested tree structure."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, parent_id, name, description, level
            FROM taxonomy_nodes
            ORDER BY level ASC, name ASC
            """
        )
        rows = [dict(r) for r in cur.fetchall()]

    # Build tree from flat list
    nodes_by_id: dict[int, dict] = {}
    roots: list[dict] = []

    for row in rows:
        row["children"] = []
        nodes_by_id[row["id"]] = row

    for row in rows:
        if row["parent_id"] is None:
            roots.append(row)
        else:
            parent = nodes_by_id.get(row["parent_id"])
            if parent:
                parent["children"].append(row)

    return roots


def get_node(node_id: int) -> dict[str, Any] | None:
    """Get a single taxonomy node with its children."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, parent_id, name, description, level FROM taxonomy_nodes WHERE id = %s",
            (node_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        node = dict(row)

        cur.execute(
            """
            SELECT id, parent_id, name, description, level
            FROM taxonomy_nodes
            WHERE parent_id = %s
            ORDER BY name ASC
            """,
            (node_id,),
        )
        node["children"] = [dict(r) for r in cur.fetchall()]
        return node


def get_node_evals(node_id: int) -> list[dict[str, Any]]:
    """Get all evals mapped to a taxonomy node."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT e.id, e.name, e.description, e.tags, e.threshold,
                   h.discrimination_power, h.lifecycle_state, h.saturation_type
            FROM taxonomy_eval_map m
            JOIN eval_definitions e ON m.eval_id = e.id
            LEFT JOIN eval_health h ON e.id = h.eval_id
            WHERE m.taxonomy_id = %s
            ORDER BY e.name
            """,
            (node_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def map_eval_to_node(eval_id: int, taxonomy_id: int) -> None:
    """Create a mapping between an eval and a taxonomy node."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO taxonomy_eval_map (taxonomy_id, eval_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (taxonomy_id, eval_id),
        )


def get_coverage_stats() -> list[dict[str, Any]]:
    """Get per-leaf-node coverage statistics.

    Returns leaf nodes (no children) with eval count,
    average discrimination, and lifecycle state distribution.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                t.id,
                t.parent_id,
                t.name,
                t.description,
                t.level,
                p.name AS parent_name,
                COUNT(DISTINCT m.eval_id) AS eval_count,
                COALESCE(AVG(h.discrimination_power), 0) AS avg_discrimination,
                COUNT(CASE WHEN h.lifecycle_state = 'active' THEN 1 END) AS active_count,
                COUNT(CASE WHEN h.lifecycle_state = 'watch' THEN 1 END) AS watch_count,
                COUNT(CASE WHEN h.lifecycle_state = 'saturated' THEN 1 END) AS saturated_count,
                COUNT(CASE WHEN h.lifecycle_state = 'archived' THEN 1 END) AS archived_count
            FROM taxonomy_nodes t
            LEFT JOIN taxonomy_nodes p ON t.parent_id = p.id
            LEFT JOIN taxonomy_eval_map m ON t.id = m.taxonomy_id
            LEFT JOIN eval_health h ON m.eval_id = h.eval_id
            WHERE NOT EXISTS (
                SELECT 1 FROM taxonomy_nodes c WHERE c.parent_id = t.id
            )
            GROUP BY t.id, t.parent_id, t.name, t.description, t.level, p.name
            ORDER BY p.name NULLS FIRST, t.name
            """
        )
        return [dict(r) for r in cur.fetchall()]
