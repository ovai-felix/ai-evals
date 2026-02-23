"""Scorer facade — convenience interface for all built-in scorers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aeval.core.result import TaskResult

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse


class Scorer:
    """Facade for all built-in scoring methods.

    Scorers take model predictions and references, and return a list of TaskResult
    or a list of scores (floats from 0.0 to 1.0).
    """

    @staticmethod
    def exact_match(
        predictions: list[GenerateResponse] | list[str],
        references: list[str],
        *,
        normalize: bool = True,
    ) -> list[TaskResult]:
        """Score by exact string match with optional normalization."""
        from aeval.scorers.exact_match import score_exact_match

        return score_exact_match(predictions, references, normalize=normalize)

    @staticmethod
    def multiple_choice(
        predictions: list[GenerateResponse] | list[str],
        answers: list[str],
    ) -> list[TaskResult]:
        """Score multiple choice (A/B/C/D) extraction and match."""
        from aeval.scorers.multiple_choice import score_multiple_choice

        return score_multiple_choice(predictions, answers)

    @staticmethod
    def llm_judge(
        predictions: list[GenerateResponse] | list[str],
        references: list[str],
        *,
        judge_model: str = "ollama:gpt-oss:20b",
        rubric: str = "",
        scale: int = 5,
    ) -> list[TaskResult]:
        """Score using an LLM as a judge.

        The judge_model default can be overridden globally via aeval.JUDGE_MODEL
        (set by CLI --judge flag) without changing individual eval files.
        """
        import aeval as _aeval
        from aeval.scorers.llm_judge import score_llm_judge

        effective_judge = _aeval.JUDGE_MODEL or judge_model
        return score_llm_judge(
            predictions,
            references,
            judge_model=effective_judge,
            rubric=rubric,
            scale=scale,
        )

    @staticmethod
    def safety_refusal(
        predictions: list[GenerateResponse] | list[str],
        expected_refusals: list[str] | list[bool] | None = None,
    ) -> list[TaskResult]:
        """Score whether model correctly refused unsafe prompts."""
        from aeval.scorers.safety_refusal import score_safety_refusal

        return score_safety_refusal(predictions, expected_refusals=expected_refusals)

    @staticmethod
    def json_schema(
        predictions: list[GenerateResponse] | list[str],
        references: list[str],
        *,
        required_fields: list[str] | None = None,
    ) -> list[TaskResult]:
        """Score by validating JSON structure and required fields."""
        from aeval.scorers.json_schema import score_json_schema

        return score_json_schema(predictions, references, required_fields=required_fields)

    @staticmethod
    def field_extract(
        predictions: list[GenerateResponse] | list[str],
        references: list[str],
        *,
        fields: list[str],
        numeric_tolerance: float = 0.05,
    ) -> list[TaskResult]:
        """Score by extracting named fields and comparing against references."""
        from aeval.scorers.field_extract import score_field_extract

        return score_field_extract(
            predictions, references, fields=fields, numeric_tolerance=numeric_tolerance
        )

    @staticmethod
    def semantic_similarity(
        predictions: list[GenerateResponse] | list[str],
        references: list[str],
        *,
        threshold: float = 0.6,
    ) -> list[TaskResult]:
        """Score by TF-IDF cosine similarity between prediction and reference."""
        from aeval.scorers.semantic_similarity import score_semantic_similarity

        return score_semantic_similarity(predictions, references, threshold=threshold)

    @staticmethod
    def pii_leakage(
        predictions: list[GenerateResponse] | list[str],
    ) -> list[TaskResult]:
        """Score whether model output contains PII (emails, phones, SSNs, etc.)."""
        from aeval.scorers.pii_leakage import score_pii_leakage

        return score_pii_leakage(predictions)

    @staticmethod
    def toxicity(
        predictions: list[GenerateResponse] | list[str],
    ) -> list[TaskResult]:
        """Score whether model output contains toxic or harmful content."""
        from aeval.scorers.toxicity import score_toxicity

        return score_toxicity(predictions)

    @staticmethod
    def constraint_satisfaction(
        predictions: list[GenerateResponse] | list[str],
        constraints: list[list[str]],
        *,
        judge_model: str = "ollama:gpt-oss:20b",
    ) -> list[TaskResult]:
        """Score how many per-task constraints each prediction satisfies."""
        import aeval as _aeval
        from aeval.scorers.constraint_satisfaction import score_constraint_satisfaction

        effective_judge = _aeval.JUDGE_MODEL or judge_model
        return score_constraint_satisfaction(
            predictions, constraints, judge_model=effective_judge
        )

    @staticmethod
    def tool_call_accuracy(
        predictions: list[GenerateResponse] | list[str],
        references: list[str],
    ) -> list[TaskResult]:
        """Score tool call predictions against gold-standard function calls."""
        from aeval.scorers.tool_call_accuracy import score_tool_call_accuracy

        return score_tool_call_accuracy(predictions, references)
