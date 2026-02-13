"""LLM-as-judge scorer — use a local Ollama model to evaluate responses."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aeval.core.result import TaskResult

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse


_DEFAULT_RUBRIC = (
    "Rate the following response on a scale of 1 to {scale}.\n"
    "Consider accuracy, completeness, and clarity.\n"
    "Respond with ONLY a single number between 1 and {scale}."
)

_JUDGE_PROMPT_TEMPLATE = """You are an expert evaluator. {rubric}

**Reference answer:**
{reference}

**Model response to evaluate:**
{prediction}

Rating (1-{scale}):"""


def _extract_text(pred: GenerateResponse | str) -> str:
    if isinstance(pred, str):
        return pred
    return pred.text


def _extract_rating(text: str, scale: int) -> float | None:
    """Extract a numeric rating from judge output."""
    # Look for a number in the text
    numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", text)
    for num_str in numbers:
        num = float(num_str)
        if 1 <= num <= scale:
            return num
    return None


def _parse_model_spec(model_spec: str) -> tuple[str, str | None]:
    """Parse a model spec like 'ollama:gpt-oss:20b' into (model_name, host)."""
    if model_spec.startswith("ollama:"):
        model_name = model_spec[len("ollama:"):]
        return model_name, None
    return model_spec, None


def score_llm_judge(
    predictions: list[GenerateResponse | str],
    references: list[str],
    *,
    judge_model: str = "ollama:gpt-oss:20b",
    rubric: str = "",
    scale: int = 5,
) -> list[TaskResult]:
    """Score predictions using an LLM judge model.

    Args:
        predictions: Model outputs to evaluate.
        references: Reference/expected answers for context.
        judge_model: Model to use as judge (e.g., "ollama:gpt-oss:20b").
        rubric: Custom evaluation rubric. Defaults to a general quality rubric.
        scale: Rating scale (default 1-5).

    Returns:
        List of TaskResult with normalized scores (0.0 to 1.0).
    """
    from aeval.core.model import Model

    if len(predictions) != len(references):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions vs {len(references)} references"
        )

    rubric_text = rubric or _DEFAULT_RUBRIC.format(scale=scale)
    model_name, host = _parse_model_spec(judge_model)
    kwargs = {"host": host} if host else {}
    judge = Model.from_ollama(model_name, **kwargs)

    results = []
    for i, (pred, ref) in enumerate(zip(predictions, references)):
        pred_text = _extract_text(pred)

        judge_prompt = _JUDGE_PROMPT_TEMPLATE.format(
            rubric=rubric_text,
            reference=ref,
            prediction=pred_text,
            scale=scale,
        )

        judge_responses = judge.generate(judge_prompt, temperature=0.0)
        judge_text = judge_responses[0].text if judge_responses else ""

        rating = _extract_rating(judge_text, scale)
        if rating is None:
            # Could not parse a rating — assign score 0.0
            normalized_score = 0.0
        else:
            # Normalize to 0-1 range
            normalized_score = (rating - 1) / (scale - 1) if scale > 1 else 1.0

        results.append(
            TaskResult(
                task_id=str(i),
                score=normalized_score,
                passed=normalized_score >= 0.6,
                prediction=pred_text,
                reference=ref,
                metadata={
                    "judge_model": judge_model,
                    "judge_output": judge_text,
                    "raw_rating": rating,
                    "scale": scale,
                },
            )
        )

    return results
