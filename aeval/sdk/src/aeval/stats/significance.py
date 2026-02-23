"""Statistical significance testing for aeval."""

from __future__ import annotations

import math

import numpy as np
from scipy import stats as sp_stats

from aeval.core.result import ConfidenceInterval


def confidence_interval(
    scores: list[float],
    *,
    level: float = 0.95,
    method: str = "bootstrap",
    n_bootstrap: int = 10000,
) -> ConfidenceInterval:
    """Compute a confidence interval for the mean score.

    Args:
        scores: List of individual task scores.
        level: Confidence level (default 0.95 for 95% CI).
        method: "bootstrap" or "normal".
        n_bootstrap: Number of bootstrap samples (only for bootstrap method).

    Returns:
        ConfidenceInterval with lower and upper bounds.
    """
    arr = np.array(scores, dtype=float)
    n = len(arr)

    if n < 2:
        mean = float(arr.mean())
        return ConfidenceInterval(lower=mean, upper=mean, level=level)

    if method == "bootstrap":
        return _bootstrap_ci(arr, level=level, n_bootstrap=n_bootstrap)
    else:
        return _normal_ci(arr, level=level)


def _bootstrap_ci(
    arr: np.ndarray, *, level: float, n_bootstrap: int
) -> ConfidenceInterval:
    """Bootstrap confidence interval for the mean."""
    rng = np.random.default_rng(42)
    n = len(arr)
    boot_means = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means[i] = sample.mean()

    alpha = 1 - level
    lower = float(np.percentile(boot_means, 100 * alpha / 2))
    upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return ConfidenceInterval(lower=lower, upper=upper, level=level)


def _normal_ci(arr: np.ndarray, *, level: float) -> ConfidenceInterval:
    """Normal approximation confidence interval for the mean."""
    n = len(arr)
    mean = float(arr.mean())
    se = float(arr.std(ddof=1) / math.sqrt(n))
    alpha = 1 - level
    z = float(sp_stats.norm.ppf(1 - alpha / 2))
    return ConfidenceInterval(lower=mean - z * se, upper=mean + z * se, level=level)


def significance_test(
    scores_a: list[float],
    scores_b: list[float],
    *,
    method: str = "welch",
    alpha: float = 0.05,
) -> dict:
    """Test whether two sets of scores are significantly different.

    Args:
        scores_a: Scores from model A.
        scores_b: Scores from model B.
        method: "welch" (Welch's t-test) or "permutation".
        alpha: Significance level.

    Returns:
        Dict with p_value, significant, statistic, effect_size, method.
    """
    a = np.array(scores_a, dtype=float)
    b = np.array(scores_b, dtype=float)

    if len(a) < 2 or len(b) < 2:
        return {
            "p_value": 1.0,
            "significant": False,
            "statistic": 0.0,
            "effect_size": 0.0,
            "method": method,
        }

    if method == "permutation":
        result = _permutation_test(a, b, alpha=alpha)
    else:
        result = _welch_t_test(a, b, alpha=alpha)

    result["effect_size"] = cohens_d(scores_a, scores_b)
    return result


def _welch_t_test(a: np.ndarray, b: np.ndarray, *, alpha: float) -> dict:
    """Welch's t-test (unequal variances)."""
    stat, p_value = sp_stats.ttest_ind(a, b, equal_var=False)
    return {
        "p_value": float(p_value),
        "significant": float(p_value) < alpha,
        "statistic": float(stat),
        "method": "welch",
    }


def _permutation_test(
    a: np.ndarray, b: np.ndarray, *, alpha: float, n_permutations: int = 10000
) -> dict:
    """Permutation test for difference in means."""
    rng = np.random.default_rng(42)
    observed_diff = abs(float(a.mean() - b.mean()))
    combined = np.concatenate([a, b])
    n_a = len(a)
    count = 0

    for _ in range(n_permutations):
        rng.shuffle(combined)
        perm_diff = abs(combined[:n_a].mean() - combined[n_a:].mean())
        if perm_diff >= observed_diff:
            count += 1

    p_value = (count + 1) / (n_permutations + 1)
    return {
        "p_value": p_value,
        "significant": p_value < alpha,
        "statistic": observed_diff,
        "method": "permutation",
    }


def cohen_kappa(ratings_a: list, ratings_b: list) -> float:
    """Compute Cohen's kappa for inter-rater agreement.

    Args:
        ratings_a: Categorical ratings from rater A.
        ratings_b: Categorical ratings from rater B.

    Returns:
        Kappa statistic: 1.0 = perfect agreement, 0.0 = chance, <0 = worse than chance.
    """
    if len(ratings_a) != len(ratings_b):
        raise ValueError(
            f"Length mismatch: {len(ratings_a)} vs {len(ratings_b)} ratings"
        )

    n = len(ratings_a)
    if n == 0:
        return 0.0

    categories = sorted(set(ratings_a) | set(ratings_b))
    cat_index = {c: i for i, c in enumerate(categories)}
    k = len(categories)

    # Build confusion matrix
    matrix = [[0] * k for _ in range(k)]
    for a, b in zip(ratings_a, ratings_b):
        matrix[cat_index[a]][cat_index[b]] += 1

    # Observed agreement
    p_o = sum(matrix[i][i] for i in range(k)) / n

    # Expected agreement by chance
    p_e = 0.0
    for i in range(k):
        row_sum = sum(matrix[i][j] for j in range(k))
        col_sum = sum(matrix[j][i] for j in range(k))
        p_e += (row_sum * col_sum) / (n * n)

    if p_e == 1.0:
        return 1.0

    return (p_o - p_e) / (1 - p_e)


def cohens_d(scores_a: list[float], scores_b: list[float]) -> float:
    """Compute Cohen's d effect size between two groups.

    Returns:
        Effect size. Conventions: small=0.2, medium=0.5, large=0.8.
    """
    a = np.array(scores_a, dtype=float)
    b = np.array(scores_b, dtype=float)

    n_a, n_b = len(a), len(b)
    if n_a < 2 or n_b < 2:
        return 0.0

    mean_diff = float(a.mean() - b.mean())
    # Pooled standard deviation
    var_a = float(a.var(ddof=1))
    var_b = float(b.var(ddof=1))
    pooled_std = math.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))

    if pooled_std == 0:
        return 0.0

    return mean_diff / pooled_std
