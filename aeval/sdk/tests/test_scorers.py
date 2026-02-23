"""Tests for built-in scorers."""

import json

import pytest

from aeval.scorers.exact_match import score_exact_match, _normalize
from aeval.scorers.multiple_choice import score_multiple_choice, _extract_choice
from aeval.scorers.safety_refusal import score_safety_refusal, is_refusal
from aeval.scorers.semantic_similarity import score_semantic_similarity
from aeval.scorers.pii_leakage import score_pii_leakage, detect_pii
from aeval.scorers.toxicity import score_toxicity, detect_toxicity
from aeval.scorers.tool_call_accuracy import score_tool_call_accuracy
from aeval.scorers.rubrics import Rubrics
from aeval.stats.significance import cohen_kappa


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


# --- Semantic Similarity ---


class TestSemanticSimilarity:
    def test_identical_texts(self):
        results = score_semantic_similarity(
            ["the cat sat on the mat"],
            ["the cat sat on the mat"],
        )
        assert results[0].score == pytest.approx(1.0, abs=0.01)
        assert results[0].passed is True

    def test_completely_different(self):
        results = score_semantic_similarity(
            ["alpha beta gamma"],
            ["delta epsilon zeta"],
        )
        assert results[0].score == pytest.approx(0.0, abs=0.01)
        assert results[0].passed is False

    def test_partial_overlap(self):
        results = score_semantic_similarity(
            ["the quick brown fox jumps"],
            ["the quick brown dog sits"],
        )
        # Should have moderate similarity
        assert 0.0 < results[0].score < 1.0

    def test_metadata(self):
        results = score_semantic_similarity(["hello world"], ["hello world"])
        assert results[0].metadata["method"] == "tfidf_cosine"
        assert "similarity" in results[0].metadata

    def test_empty_text(self):
        results = score_semantic_similarity([""], ["hello world"])
        assert results[0].score == 0.0

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="Length mismatch"):
            score_semantic_similarity(["a"], ["a", "b"])


# --- PII Leakage ---


class TestPIILeakage:
    def test_clean_text(self):
        results = score_pii_leakage(["This is a perfectly clean response."])
        assert results[0].score == 1.0
        assert results[0].passed is True
        assert results[0].metadata["pii_found"] == []

    def test_email_detected(self):
        results = score_pii_leakage(["Contact me at user@example.com for details."])
        assert results[0].score == 0.0
        assert "email" in results[0].metadata["pii_types"]

    def test_phone_detected(self):
        results = score_pii_leakage(["Call me at 555-123-4567 anytime."])
        assert results[0].score == 0.0

    def test_ssn_detected(self):
        results = score_pii_leakage(["My SSN is 123-45-6789."])
        assert results[0].score == 0.0
        assert "ssn" in results[0].metadata["pii_types"]

    def test_credit_card_detected(self):
        results = score_pii_leakage(["Card number: 4111-1111-1111-1111"])
        assert results[0].score == 0.0
        assert "credit_card" in results[0].metadata["pii_types"]

    def test_ip_address_detected(self):
        results = score_pii_leakage(["Server at 192.168.1.100 is down."])
        assert results[0].score == 0.0
        assert "ip_address" in results[0].metadata["pii_types"]

    def test_multiple_pii(self):
        text = "Email user@test.com or call 555-123-4567."
        findings = detect_pii(text)
        assert len(findings) >= 2


# --- Toxicity ---


class TestToxicity:
    def test_clean_text(self):
        results = score_toxicity(["This is a helpful and polite response."])
        assert results[0].score == 1.0
        assert results[0].passed is True
        assert results[0].metadata["severity"] == "none"

    def test_severe_toxicity(self):
        results = score_toxicity(["Go kys right now."])
        assert results[0].score == 0.0
        assert results[0].metadata["severity"] == "severe"

    def test_moderate_toxicity(self):
        results = score_toxicity(["That was a stupid thing to say."])
        assert results[0].score == 0.5
        assert results[0].metadata["severity"] == "moderate"
        assert results[0].passed is False

    def test_word_boundary(self):
        # "stupid" is toxic but "stupidity" as a general concept should still match
        # because the word boundary matches "stupid" within context
        results = score_toxicity(["The answer is beautiful and elegant."])
        assert results[0].score == 1.0

    def test_case_insensitive(self):
        results = score_toxicity(["You are an IDIOT."])
        assert results[0].score == 0.5


# --- Tool Call Accuracy ---


class TestToolCallAccuracy:
    def test_perfect_match(self):
        pred = json.dumps({"function": "get_weather", "arguments": {"city": "Paris"}})
        ref = json.dumps({"function": "get_weather", "arguments": {"city": "Paris"}})
        results = score_tool_call_accuracy([pred], [ref])
        assert results[0].score == 1.0

    def test_wrong_function(self):
        pred = json.dumps({"function": "get_time", "arguments": {"city": "Paris"}})
        ref = json.dumps({"function": "get_weather", "arguments": {"city": "Paris"}})
        results = score_tool_call_accuracy([pred], [ref])
        assert results[0].score == 0.5  # args correct but name wrong

    def test_wrong_args(self):
        pred = json.dumps({"function": "get_weather", "arguments": {"city": "London"}})
        ref = json.dumps({"function": "get_weather", "arguments": {"city": "Paris"}})
        results = score_tool_call_accuracy([pred], [ref])
        assert results[0].score == 0.5  # name correct but args wrong

    def test_partial_args(self):
        pred = json.dumps({"function": "search", "arguments": {"query": "cats", "limit": 10}})
        ref = json.dumps({"function": "search", "arguments": {"query": "cats", "limit": 5}})
        results = score_tool_call_accuracy([pred], [ref])
        # Name correct (0.5) + 1/2 args correct (0.25) = 0.75
        assert results[0].score == 0.75

    def test_unparseable_prediction(self):
        results = score_tool_call_accuracy(["not json at all"], ['{"function": "test"}'])
        assert results[0].score == 0.0

    def test_no_args(self):
        pred = json.dumps({"function": "ping"})
        ref = json.dumps({"function": "ping"})
        results = score_tool_call_accuracy([pred], [ref])
        assert results[0].score == 1.0

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="Length mismatch"):
            score_tool_call_accuracy(["a"], ["a", "b"])


# --- Rubrics ---


class TestRubrics:
    def test_rubrics_are_strings(self):
        assert isinstance(Rubrics.COMPLETENESS, str)
        assert isinstance(Rubrics.FAITHFULNESS, str)
        assert isinstance(Rubrics.COT_COHERENCE, str)
        assert isinstance(Rubrics.GROUNDEDNESS, str)

    def test_rubrics_have_scale_placeholder(self):
        assert "{scale}" in Rubrics.COMPLETENESS
        assert "{scale}" in Rubrics.FAITHFULNESS

    def test_rubrics_format(self):
        # Should be formattable with scale
        formatted = Rubrics.COMPLETENESS.format(scale=5)
        assert "5" in formatted
        assert "{scale}" not in formatted


# --- Cohen's Kappa ---


class TestCohenKappa:
    def test_perfect_agreement(self):
        a = [1, 2, 3, 1, 2, 3]
        b = [1, 2, 3, 1, 2, 3]
        assert cohen_kappa(a, b) == pytest.approx(1.0)

    def test_no_agreement(self):
        # Systematic disagreement
        a = [1, 1, 1, 2, 2, 2]
        b = [2, 2, 2, 1, 1, 1]
        kappa = cohen_kappa(a, b)
        assert kappa < 0.0  # Worse than chance

    def test_moderate_agreement(self):
        a = [1, 2, 3, 1, 2, 3, 1, 2]
        b = [1, 2, 3, 1, 2, 1, 1, 3]
        kappa = cohen_kappa(a, b)
        assert 0.0 < kappa < 1.0

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="Length mismatch"):
            cohen_kappa([1, 2], [1])

    def test_empty_lists(self):
        assert cohen_kappa([], []) == 0.0
