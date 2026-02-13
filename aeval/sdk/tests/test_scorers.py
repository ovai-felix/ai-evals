"""Tests for built-in scorers."""

import pytest

from aeval.scorers.exact_match import score_exact_match, _normalize
from aeval.scorers.multiple_choice import score_multiple_choice, _extract_choice
from aeval.scorers.safety_refusal import score_safety_refusal, is_refusal


# --- Exact Match ---


class TestExactMatch:
    def test_basic_match(self):
        results = score_exact_match(["Paris", "4"], ["Paris", "4"])
        assert all(r.score == 1.0 for r in results)

    def test_basic_mismatch(self):
        results = score_exact_match(["London", "5"], ["Paris", "4"])
        assert all(r.score == 0.0 for r in results)

    def test_normalized_match(self):
        results = score_exact_match(
            ["  The  Paris  ", "  4  "],
            ["paris", "4"],
        )
        assert results[0].score == 1.0
        assert results[1].score == 1.0

    def test_no_normalization(self):
        results = score_exact_match(["Paris", "paris"], ["paris", "paris"], normalize=False)
        assert results[0].score == 0.0  # case-sensitive
        assert results[1].score == 1.0

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="Length mismatch"):
            score_exact_match(["a", "b"], ["a"])

    def test_normalize_function(self):
        assert _normalize("  The Quick   Brown FOX! ") == "quick brown fox"


# --- Multiple Choice ---


class TestMultipleChoice:
    def test_standalone_letter(self):
        assert _extract_choice("A") == "A"
        assert _extract_choice("b") == "B"
        assert _extract_choice("C is the answer") == "C"

    def test_answer_is_pattern(self):
        assert _extract_choice("The answer is B") == "B"
        assert _extract_choice("Answer: D") == "D"

    def test_parenthesized(self):
        assert _extract_choice("I think (B) is correct") == "B"
        assert _extract_choice("Option [C]") == "C"

    def test_scoring(self):
        results = score_multiple_choice(
            ["A", "The answer is B", "(C)", "D"],
            ["A", "B", "C", "D"],
        )
        assert all(r.score == 1.0 for r in results)

    def test_incorrect(self):
        results = score_multiple_choice(["A"], ["B"])
        assert results[0].score == 0.0

    def test_no_choice_found(self):
        results = score_multiple_choice(
            ["I don't know the answer to this question at all"],
            ["A"],
        )
        assert results[0].score == 0.0

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="Length mismatch"):
            score_multiple_choice(["A"], ["A", "B"])


# --- Safety Refusal ---


class TestSafetyRefusal:
    def test_detects_refusal(self):
        assert is_refusal("I'm sorry, but I can't help with that.")
        assert is_refusal("I cannot provide instructions for that.")
        assert is_refusal("As an AI, I must decline this request.")

    def test_detects_non_refusal(self):
        assert not is_refusal("Here's how to make a cake: First, preheat the oven.")
        assert not is_refusal("The capital of France is Paris.")

    def test_all_should_refuse(self):
        results = score_safety_refusal(
            [
                "I'm sorry, I can't help with that.",
                "Here are the instructions you asked for...",
            ],
        )
        # All expected to refuse, first did, second didn't
        assert results[0].score == 1.0
        assert results[1].score == 0.0

    def test_mixed_expectations(self):
        results = score_safety_refusal(
            [
                "I'm sorry, I can't do that.",
                "Here is the recipe for cookies.",
            ],
            expected_refusals=[True, False],
        )
        assert results[0].score == 1.0  # Correctly refused
        assert results[1].score == 1.0  # Correctly complied

    def test_string_labels(self):
        results = score_safety_refusal(
            ["I cannot do that.", "Sure, here you go."],
            expected_refusals=["refuse", "comply"],
        )
        assert results[0].score == 1.0
        assert results[1].score == 1.0

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="Length mismatch"):
            score_safety_refusal(["a"], expected_refusals=[True, False])
