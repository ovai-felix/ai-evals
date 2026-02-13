"""Multiple choice scorer — extract A/B/C/D answer and match."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aeval.core.result import TaskResult

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse


def _extract_choice(text: str) -> str | None:
    """Extract the chosen answer letter from model output.

    Handles patterns like:
    - "A" / "B" / "C" / "D"
    - "The answer is A"
    - "(A)" / "[A]"
    - "Answer: A"
    """
    text = text.strip()

    # Pattern 1: Standalone letter at start
    m = re.match(r"^([A-Da-d])\b", text)
    if m:
        return m.group(1).upper()

    # Pattern 2: "The answer is X" or "Answer: X"
    m = re.search(r"(?:answer|choice)\s*(?:is|:)\s*([A-Da-d])\b", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # Pattern 3: "(X)" or "[X]"
    m = re.search(r"[(\[]([A-Da-d])[)\]]", text)
    if m:
        return m.group(1).upper()

    # Pattern 4: Last standalone letter in the text
    matches = re.findall(r"\b([A-Da-d])\b", text)
    if matches:
        return matches[-1].upper()

    return None


def _extract_text(pred: GenerateResponse | str) -> str:
    if isinstance(pred, str):
        return pred
    return pred.text


def score_multiple_choice(
    predictions: list[GenerateResponse | str],
    answers: list[str],
) -> list[TaskResult]:
    """Score multiple choice answers by extracting the chosen letter.

    Args:
        predictions: Model outputs containing answer choice.
        answers: Correct answer letters (e.g., ["A", "B", "C"]).

    Returns:
        List of TaskResult with score 1.0 (correct) or 0.0 (incorrect).
    """
    if len(predictions) != len(answers):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions vs {len(answers)} answers"
        )

    results = []
    for i, (pred, answer) in enumerate(zip(predictions, answers)):
        pred_text = _extract_text(pred)
        extracted = _extract_choice(pred_text)
        expected = answer.strip().upper()
        match = extracted == expected

        results.append(
            TaskResult(
                task_id=str(i),
                score=1.0 if match else 0.0,
                passed=match,
                prediction=pred_text,
                reference=expected,
                metadata={"extracted_choice": extracted},
            )
        )

    return results
