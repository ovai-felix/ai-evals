"""Shared utilities for scorers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse


def extract_response(pred: GenerateResponse | str) -> tuple[str, float, int]:
    """Extract text, latency_ms, and tokens_used from a prediction.

    Returns:
        (text, latency_ms, tokens_used)
    """
    if isinstance(pred, str):
        return pred, 0.0, 0
    return pred.text, pred.latency_ms, pred.tokens_used
