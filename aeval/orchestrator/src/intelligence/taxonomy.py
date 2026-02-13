"""Coverage analyzer — gaps between taxonomy and evals."""

from __future__ import annotations

from typing import Any

from orchestrator.db.taxonomy_repo import get_coverage_stats, get_taxonomy_tree
from orchestrator.db.health_repo import get_health_summary


def compute_coverage() -> list[dict[str, Any]]:
    """Compute per-leaf-node coverage statistics.

    Returns list of leaf nodes with:
    - eval_count, avg_discrimination, lifecycle distribution
    - gap flag (True if no active evals or low discrimination)
    """
    stats = get_coverage_stats()
    for node in stats:
        node["is_gap"] = (
            node["eval_count"] == 0
            or (node["avg_discrimination"] < 0.15 and node["active_count"] == 0)
        )
    return stats


def find_gaps() -> list[dict[str, Any]]:
    """Find taxonomy nodes with no active evals or low discrimination."""
    coverage = compute_coverage()
    return [n for n in coverage if n["is_gap"]]


def coverage_summary() -> dict[str, Any]:
    """Aggregate coverage summary across the full taxonomy."""
    coverage = compute_coverage()
    health = get_health_summary()
    tree = get_taxonomy_tree()

    total_leaves = len(coverage)
    covered = sum(1 for n in coverage if not n["is_gap"])
    gaps = total_leaves - covered
    avg_disc = (
        sum(n["avg_discrimination"] for n in coverage) / total_leaves
        if total_leaves > 0
        else 0.0
    )

    total_evals = health.get("total_evals", 0)
    saturation_rate = (
        health.get("saturated_count", 0) / total_evals
        if total_evals > 0
        else 0.0
    )

    return {
        "total_categories": len(tree),
        "total_nodes": total_leaves,
        "covered_nodes": covered,
        "gap_count": gaps,
        "coverage_pct": round(covered / total_leaves * 100, 1) if total_leaves else 0,
        "saturation_rate": round(saturation_rate, 3),
        "avg_discrimination": round(avg_disc, 4),
        "active_count": health.get("active_count", 0),
        "watch_count": health.get("watch_count", 0),
        "saturated_count": health.get("saturated_count", 0),
        "archived_count": health.get("archived_count", 0),
    }
