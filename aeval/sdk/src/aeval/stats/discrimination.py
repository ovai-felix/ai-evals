"""Eval discrimination power analysis."""

from __future__ import annotations

import numpy as np


def discrimination_power(scores_by_model: dict[str, list[float]]) -> float:
    """Compute discrimination power of an eval across models.

    Discrimination = between-model variance / total variance.
    High discrimination (>0.15) means the eval differentiates models well.
    Low discrimination (<0.08) means models all score similarly (saturated).

    Args:
        scores_by_model: Dict mapping model name to list of task scores.

    Returns:
        Discrimination power between 0.0 and 1.0.
    """
    if len(scores_by_model) < 2:
        return 0.0

    all_scores = []
    model_means = []
    for scores in scores_by_model.values():
        if not scores:
            continue
        all_scores.extend(scores)
        model_means.append(np.mean(scores))

    if not all_scores or len(model_means) < 2:
        return 0.0

    total_var = float(np.var(all_scores))
    if total_var == 0:
        return 0.0

    between_var = float(np.var(model_means))
    return min(between_var / total_var, 1.0)


def detect_saturation(
    scores_by_model: dict[str, list[float]],
    *,
    ceiling_threshold: float = 0.95,
    floor_threshold: float = 0.10,
    ceiling_ratio: float = 0.90,
    floor_ratio: float = 0.90,
) -> dict:
    """Detect if an eval is saturated.

    Args:
        scores_by_model: Dict mapping model name to list of task scores.
        ceiling_threshold: Score above which a model is considered "at ceiling".
        floor_threshold: Score below which a model is considered "at floor".
        ceiling_ratio: Fraction of models that must be at ceiling to declare saturation.
        floor_ratio: Fraction of models at floor to declare floor saturation.

    Returns:
        Dict with saturation type and details.
    """
    if not scores_by_model:
        return {"saturated": False, "type": None}

    model_means = {
        name: float(np.mean(scores))
        for name, scores in scores_by_model.items()
        if scores
    }

    if not model_means:
        return {"saturated": False, "type": None}

    n_models = len(model_means)
    at_ceiling = sum(1 for m in model_means.values() if m > ceiling_threshold)
    at_floor = sum(1 for m in model_means.values() if m < floor_threshold)

    if at_ceiling / n_models >= ceiling_ratio:
        return {
            "saturated": True,
            "type": "ceiling",
            "models_at_ceiling": at_ceiling,
            "total_models": n_models,
        }

    if at_floor / n_models >= floor_ratio:
        return {
            "saturated": True,
            "type": "floor",
            "models_at_floor": at_floor,
            "total_models": n_models,
        }

    # Check noise: within-model variance > between-model variance
    disc = discrimination_power(scores_by_model)
    if disc < 0.08:
        return {
            "saturated": True,
            "type": "noise",
            "discrimination_power": disc,
        }

    return {
        "saturated": False,
        "type": None,
        "discrimination_power": disc,
    }
