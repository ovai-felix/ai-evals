"""Tests for statistical functions."""

import pytest

from aeval.core.result import ConfidenceInterval
from aeval.stats.significance import confidence_interval, significance_test, cohens_d
from aeval.stats.discrimination import discrimination_power, detect_saturation


class TestConfidenceInterval:
    def test_bootstrap_ci(self):
        scores = [0.8, 0.85, 0.9, 0.75, 0.82, 0.88, 0.79, 0.91, 0.83, 0.87]
        ci = confidence_interval(scores, method="bootstrap")
        assert isinstance(ci, ConfidenceInterval)
        assert ci.lower < ci.upper
        assert ci.lower > 0.0
        assert ci.upper < 1.0
        assert ci.level == 0.95

    def test_normal_ci(self):
        scores = [0.8, 0.85, 0.9, 0.75, 0.82, 0.88, 0.79, 0.91, 0.83, 0.87]
        ci = confidence_interval(scores, method="normal")
        assert ci.lower < ci.upper
        mean = sum(scores) / len(scores)
        assert ci.lower < mean < ci.upper

    def test_single_score(self):
        ci = confidence_interval([0.5])
        assert ci.lower == ci.upper == 0.5

    def test_ci_margin(self):
        ci = ConfidenceInterval(lower=0.75, upper=0.85, level=0.95)
        assert ci.margin == pytest.approx(0.05)


class TestSignificanceTest:
    def test_significant_difference(self):
        scores_a = [0.9, 0.92, 0.88, 0.91, 0.93, 0.89, 0.90, 0.92, 0.88, 0.91]
        scores_b = [0.5, 0.52, 0.48, 0.51, 0.53, 0.49, 0.50, 0.52, 0.48, 0.51]
        result = significance_test(scores_a, scores_b)
        assert result["significant"] is True
        assert result["p_value"] < 0.05
        assert abs(result["effect_size"]) > 0.8  # large effect

    def test_no_significant_difference(self):
        scores_a = [0.80, 0.82, 0.79, 0.81, 0.83]
        scores_b = [0.81, 0.80, 0.82, 0.79, 0.81]
        result = significance_test(scores_a, scores_b)
        assert result["significant"] is False

    def test_permutation_method(self):
        scores_a = [0.9, 0.92, 0.88, 0.91, 0.93]
        scores_b = [0.5, 0.52, 0.48, 0.51, 0.53]
        result = significance_test(scores_a, scores_b, method="permutation")
        assert result["significant"] is True
        assert result["method"] == "permutation"

    def test_insufficient_data(self):
        result = significance_test([0.5], [0.6])
        assert result["significant"] is False
        assert result["p_value"] == 1.0


class TestCohensD:
    def test_large_effect(self):
        a = [0.9, 0.91, 0.89, 0.92, 0.88]
        b = [0.5, 0.51, 0.49, 0.52, 0.48]
        d = cohens_d(a, b)
        assert abs(d) > 0.8  # large effect

    def test_no_effect(self):
        a = [0.5, 0.5, 0.5, 0.5]
        b = [0.5, 0.5, 0.5, 0.5]
        d = cohens_d(a, b)
        assert d == 0.0

    def test_insufficient_data(self):
        assert cohens_d([0.5], [0.6]) == 0.0


class TestDiscriminationPower:
    def test_high_discrimination(self):
        scores = {
            "model_a": [0.9, 0.92, 0.88],
            "model_b": [0.5, 0.52, 0.48],
            "model_c": [0.3, 0.32, 0.28],
        }
        dp = discrimination_power(scores)
        assert dp > 0.15  # discriminative

    def test_low_discrimination(self):
        scores = {
            "model_a": [0.80, 0.81, 0.79, 0.80, 0.82],
            "model_b": [0.80, 0.80, 0.81, 0.79, 0.80],
            "model_c": [0.80, 0.79, 0.80, 0.81, 0.80],
        }
        dp = discrimination_power(scores)
        assert dp < 0.15  # not discriminative

    def test_single_model(self):
        assert discrimination_power({"a": [0.5]}) == 0.0


class TestSaturationDetection:
    def test_ceiling_saturation(self):
        scores = {
            "a": [0.98, 0.99, 0.97],
            "b": [0.96, 0.97, 0.98],
            "c": [0.99, 0.98, 0.97],
        }
        result = detect_saturation(scores)
        assert result["saturated"] is True
        assert result["type"] == "ceiling"

    def test_floor_saturation(self):
        scores = {
            "a": [0.02, 0.03, 0.01],
            "b": [0.04, 0.03, 0.02],
            "c": [0.01, 0.02, 0.03],
        }
        result = detect_saturation(scores)
        assert result["saturated"] is True
        assert result["type"] == "floor"

    def test_not_saturated(self):
        scores = {
            "a": [0.9, 0.88, 0.91],
            "b": [0.5, 0.52, 0.48],
            "c": [0.3, 0.28, 0.32],
        }
        result = detect_saturation(scores)
        assert result["saturated"] is False
