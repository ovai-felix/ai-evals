"""Field extraction scorer — extracts and compares named fields from structured output."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from aeval.core.result import TaskResult

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse


def _extract_text(pred: GenerateResponse | str) -> str:
    if isinstance(pred, str):
        return pred
    return pred.text


def _extract_response(pred: GenerateResponse | str) -> tuple[str, float, int]:
    if isinstance(pred, str):
        return pred, 0.0, 0
    return pred.text, pred.latency_ms, pred.tokens_used


def _extract_json(text: str) -> dict | None:
    """Try to extract a JSON object from text."""
    text = text.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        pass

    # Try markdown fences
    fence_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    for match in re.findall(fence_pattern, text):
        try:
            parsed = json.loads(match.strip())
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue

    # Try finding JSON object
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start : i + 1])
                        if isinstance(parsed, dict):
                            return parsed
                    except (json.JSONDecodeError, ValueError):
                        break
    return None


def _normalize_text(s: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", s.strip().lower())


def _compare_numeric(pred_val, ref_val, tolerance: float) -> float:
    """Compare two numeric values with tolerance. Returns 0.0 or 1.0."""
    try:
        pred_num = float(pred_val)
        ref_num = float(ref_val)
        if ref_num == 0:
            return 1.0 if abs(pred_num) <= tolerance else 0.0
        relative_error = abs(pred_num - ref_num) / abs(ref_num)
        return 1.0 if relative_error <= tolerance else 0.0
    except (ValueError, TypeError):
        return 0.0


def _compare_field(pred_val, ref_val, tolerance: float) -> float:
    """Compare a single field value. Returns score 0.0 to 1.0."""
    if pred_val is None:
        return 0.0

    # Both numeric
    try:
        float(pred_val)
        float(ref_val)
        return _compare_numeric(pred_val, ref_val, tolerance)
    except (ValueError, TypeError):
        pass

    # Text comparison
    pred_str = _normalize_text(str(pred_val))
    ref_str = _normalize_text(str(ref_val))
    if pred_str == ref_str:
        return 1.0
    if ref_str in pred_str or pred_str in ref_str:
        return 0.8
    return 0.0


def score_field_extract(
    predictions: list[GenerateResponse | str],
    references: list[str],
    *,
    fields: list[str],
    numeric_tolerance: float = 0.05,
) -> list[TaskResult]:
    """Score by extracting named fields and comparing against reference values.

    Args:
        predictions: Model outputs (should contain JSON or structured data).
        references: Reference answers (JSON strings with expected field values).
        fields: List of field names to extract and compare.
        numeric_tolerance: Relative tolerance for numeric comparisons (default 5%).

    Returns:
        List of TaskResult with scores = mean accuracy across fields.
    """
    if len(predictions) != len(references):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions vs {len(references)} references"
        )

    import aeval as _aeval
    total = len(predictions)

    if _aeval.VERBOSE:
        print(f"\n  Scoring {total} responses with field_extract (fields: {fields})...")

    results = []
    for i, (pred, ref) in enumerate(zip(predictions, references)):
        pred_text, latency_ms, tokens_used = _extract_response(pred)
        pred_data = _extract_json(pred_text)

        # Parse reference
        ref_data = _extract_json(ref) if isinstance(ref, str) else None
        if ref_data is None:
            try:
                ref_data = json.loads(ref)
            except (json.JSONDecodeError, ValueError, TypeError):
                ref_data = {}

        if pred_data is None:
            results.append(
                TaskResult(
                    task_id=str(i),
                    score=0.0,
                    passed=False,
                    prediction=pred_text,
                    reference=ref,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                    metadata={"error": "no_json_in_prediction"},
                )
            )
            continue

        field_scores: dict[str, float] = {}
        for field_name in fields:
            pred_val = pred_data.get(field_name)
            ref_val = ref_data.get(field_name) if ref_data else None

            if ref_val is None:
                # No reference for this field — skip
                continue

            field_scores[field_name] = _compare_field(
                pred_val, ref_val, numeric_tolerance
            )

        if field_scores:
            score = sum(field_scores.values()) / len(field_scores)
        else:
            score = 0.0

        if _aeval.VERBOSE:
            _status = "PASS" if score >= 0.6 else "FAIL"
            _fields_str = " ".join(f"{k}={'ok' if v >= 0.6 else 'miss'}" for k, v in field_scores.items())
            print(f"  [{i+1}/{total}] score={score:.2f} [{_status}] {_fields_str}")

        results.append(
            TaskResult(
                task_id=str(i),
                score=score,
                passed=score >= 0.6,
                prediction=pred_text,
                reference=ref,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                metadata={"field_scores": field_scores},
            )
        )

    return results
