"""Tool call accuracy scorer — compare predicted function calls against gold."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from aeval.core.result import TaskResult

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse


def _extract_text(pred: GenerateResponse | str) -> str:
    if isinstance(pred, str):
        return pred
    return pred.text


def _parse_tool_call(text: str) -> dict[str, Any] | None:
    """Parse a JSON tool call from text. Expected: {"function": str, "arguments": dict}."""
    text = text.strip()
    # Try to find JSON object in text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        parsed = json.loads(text[start:end])
        if "function" in parsed:
            return parsed
        return None
    except (json.JSONDecodeError, TypeError):
        return None


def _compare_args(pred_args: dict, gold_args: dict) -> dict[str, float]:
    """Compare predicted arguments against gold, returning per-arg scores."""
    if not gold_args:
        return {}

    scores: dict[str, float] = {}
    for key, gold_val in gold_args.items():
        pred_val = pred_args.get(key)
        if pred_val is None:
            scores[key] = 0.0
        elif type(pred_val) == type(gold_val) and pred_val == gold_val:
            scores[key] = 1.0
        elif str(pred_val).strip().lower() == str(gold_val).strip().lower():
            # Type-coerced string match
            scores[key] = 1.0
        else:
            scores[key] = 0.0

    return scores


def score_tool_call_accuracy(
    predictions: list[GenerateResponse | str],
    references: list[str],
) -> list[TaskResult]:
    """Score tool call predictions against gold-standard tool calls.

    Score breakdown: 0.5 for correct function name + 0.5 for argument accuracy.

    Args:
        predictions: Model outputs containing JSON tool calls.
        references: Gold-standard JSON tool calls.

    Returns:
        List of TaskResult with tool call accuracy scores.
    """
    if len(predictions) != len(references):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions vs {len(references)} references"
        )

    results = []
    for i, (pred, ref) in enumerate(zip(predictions, references)):
        pred_text = _extract_text(pred)
        pred_call = _parse_tool_call(pred_text)
        gold_call = _parse_tool_call(ref)

        if gold_call is None:
            # Invalid gold reference
            results.append(
                TaskResult(
                    task_id=str(i),
                    score=0.0,
                    passed=False,
                    prediction=pred_text,
                    reference=ref,
                    metadata={"error": "invalid gold reference"},
                )
            )
            continue

        if pred_call is None:
            results.append(
                TaskResult(
                    task_id=str(i),
                    score=0.0,
                    passed=False,
                    prediction=pred_text,
                    reference=ref,
                    metadata={
                        "function_correct": False,
                        "arg_scores": {},
                        "error": "could not parse prediction as tool call",
                    },
                )
            )
            continue

        # Function name check (exact match)
        function_correct = pred_call.get("function") == gold_call.get("function")
        name_score = 0.5 if function_correct else 0.0

        # Argument accuracy
        gold_args = gold_call.get("arguments", {})
        pred_args = pred_call.get("arguments", {})
        arg_scores = _compare_args(pred_args, gold_args)

        if arg_scores:
            arg_accuracy = sum(arg_scores.values()) / len(arg_scores)
        else:
            # No arguments expected — full marks for args if none predicted
            arg_accuracy = 1.0 if not pred_args else 0.0

        args_score = 0.5 * arg_accuracy
        total_score = name_score + args_score

        results.append(
            TaskResult(
                task_id=str(i),
                score=total_score,
                passed=total_score >= 0.5,
                prediction=pred_text,
                reference=ref,
                metadata={
                    "function_correct": function_correct,
                    "arg_scores": arg_scores,
                },
            )
        )

    return results
