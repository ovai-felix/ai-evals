"""JSON schema scorer — validates structured JSON output from models."""

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


def _extract_json(text: str) -> dict | list | None:
    """Extract JSON from text, including from markdown code fences."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try extracting from markdown code fences
    fence_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    matches = re.findall(fence_pattern, text)
    for match in matches:
        try:
            return json.loads(match.strip())
        except (json.JSONDecodeError, ValueError):
            continue

    # Try finding JSON object/array boundaries
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        # Find matching closing bracket
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except (json.JSONDecodeError, ValueError):
                        break

    return None


def score_json_schema(
    predictions: list[GenerateResponse | str],
    references: list[str],
    *,
    required_fields: list[str] | None = None,
) -> list[TaskResult]:
    """Score predictions by validating JSON structure and required fields.

    Scoring breakdown:
    - 0.4 for valid parseable JSON
    - 0.6 split across required field presence (if specified)
    - If no required_fields, 0.6 for being a non-empty dict/list

    Args:
        predictions: Model outputs to validate.
        references: Reference answers (used for metadata only).
        required_fields: List of top-level keys that must be present.

    Returns:
        List of TaskResult with scores 0.0 to 1.0.
    """
    if len(predictions) != len(references):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions vs {len(references)} references"
        )

    import aeval as _aeval
    total = len(predictions)

    if _aeval.VERBOSE:
        _rf = required_fields or []
        print(f"\n  Scoring {total} responses with json_schema (required: {_rf})...")

    results = []
    for i, (pred, ref) in enumerate(zip(predictions, references)):
        pred_text, latency_ms, tokens_used = _extract_response(pred)
        parsed = _extract_json(pred_text)

        if parsed is None:
            results.append(
                TaskResult(
                    task_id=str(i),
                    score=0.0,
                    passed=False,
                    prediction=pred_text,
                    reference=ref,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                    metadata={"error": "invalid_json"},
                )
            )
            continue

        score = 0.4  # Base score for valid JSON
        field_report: dict[str, bool] = {}

        if required_fields and isinstance(parsed, dict):
            per_field = 0.6 / len(required_fields) if required_fields else 0
            for field_name in required_fields:
                present = field_name in parsed and parsed[field_name] is not None
                field_report[field_name] = present
                if present:
                    score += per_field
        elif isinstance(parsed, dict) and parsed:
            score += 0.6
        elif isinstance(parsed, list) and parsed:
            score += 0.6

        score = min(score, 1.0)

        if _aeval.VERBOSE:
            _status = "PASS" if score >= 0.75 else "FAIL"
            _fields_str = " ".join(f"{k}={'ok' if v else 'miss'}" for k, v in field_report.items()) if field_report else "valid_json"
            print(f"  [{i+1}/{total}] score={score:.2f} [{_status}] {_fields_str}")

        results.append(
            TaskResult(
                task_id=str(i),
                score=score,
                passed=score >= 0.75,
                prediction=pred_text,
                reference=ref,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                metadata={
                    "parsed_type": type(parsed).__name__,
                    "field_report": field_report,
                    "num_keys": len(parsed) if isinstance(parsed, dict) else None,
                },
            )
        )

    return results
