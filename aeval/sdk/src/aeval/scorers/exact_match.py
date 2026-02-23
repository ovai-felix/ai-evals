"""Exact match scorer with normalization."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

from aeval.core.result import TaskResult

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace, remove articles."""
    text = unicodedata.normalize("NFKD", text)
    text = text.lower().strip()
    # Remove articles
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    return text


def _extract_text(pred: GenerateResponse | str) -> str:
    if isinstance(pred, str):
        return pred
    return pred.text


def _extract_response(pred: GenerateResponse | str) -> tuple[str, float, int]:
    if isinstance(pred, str):
        return pred, 0.0, 0
    return pred.text, pred.latency_ms, pred.tokens_used


def score_exact_match(
    predictions: list[GenerateResponse | str],
    references: list[str],
    *,
    normalize: bool = True,
) -> list[TaskResult]:
    """Score predictions against references by exact string match.

    Uses a two-tier strategy when normalize=True:
    1. Exact match on normalized text.
    2. Contains check — the normalized reference appears within the
       normalized prediction (handles verbose model responses).

    Args:
        predictions: Model outputs (GenerateResponse or raw strings).
        references: Expected correct answers.
        normalize: If True, normalize text before comparing (lowercase, strip, etc.).

    Returns:
        List of TaskResult with score 1.0 (match) or 0.0 (no match).
    """
    if len(predictions) != len(references):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions vs {len(references)} references"
        )

    results = []
    for i, (pred, ref) in enumerate(zip(predictions, references)):
        pred_text, latency_ms, tokens_used = _extract_response(pred)

        if normalize:
            norm_pred = _normalize(pred_text)
            norm_ref = _normalize(ref)
            match = norm_pred == norm_ref or norm_ref in norm_pred
        else:
            match = pred_text == ref

        results.append(
            TaskResult(
                task_id=str(i),
                score=1.0 if match else 0.0,
                passed=match,
                prediction=pred_text,
                reference=ref,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
            )
        )

    return results
