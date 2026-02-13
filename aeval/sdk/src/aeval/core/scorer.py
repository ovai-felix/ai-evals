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
        """Score using an LLM as a judge (via Ollama)."""
        from aeval.scorers.llm_judge import score_llm_judge

        return score_llm_judge(
            predictions,
            references,
            judge_model=judge_model,
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
