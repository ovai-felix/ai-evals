"""Constraint satisfaction scorer — LLM judge evaluates per-task constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aeval.core.result import TaskResult

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse

_CONSTRAINT_PROMPT = """You are an evaluator. Does the following response satisfy this constraint?

**Constraint:** {constraint}

**Response:**
{prediction}

Answer with ONLY "YES" or "NO"."""


def _extract_text(pred: GenerateResponse | str) -> str:
    if isinstance(pred, str):
        return pred
    return pred.text


def score_constraint_satisfaction(
    predictions: list[GenerateResponse | str],
    constraints: list[list[str]],
    *,
    judge_model: str = "ollama:gpt-oss:20b",
) -> list[TaskResult]:
    """Score how many constraints each prediction satisfies.

    Args:
        predictions: Model outputs.
        constraints: Per-task list of constraint strings.
        judge_model: Model to use for constraint evaluation.

    Returns:
        List of TaskResult with fraction of constraints satisfied.
    """
    import aeval as _aeval
    from aeval.scorers.llm_judge import _parse_model_spec

    if len(predictions) != len(constraints):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions vs {len(constraints)} constraint lists"
        )

    effective_judge = _aeval.JUDGE_MODEL or judge_model
    provider, model_name = _parse_model_spec(effective_judge)

    from aeval.core.model import Model

    if provider == "openai":
        judge = Model.from_openai(model_name)
    elif provider == "openrouter":
        judge = Model.from_openrouter(model_name)
    else:
        judge = Model.from_ollama(model_name)

    results = []
    for i, (pred, task_constraints) in enumerate(zip(predictions, constraints)):
        pred_text = _extract_text(pred)

        if not task_constraints:
            results.append(
                TaskResult(
                    task_id=str(i),
                    score=1.0,
                    passed=True,
                    prediction=pred_text,
                    metadata={"constraint_results": {}, "satisfied": 0, "total": 0},
                )
            )
            continue

        constraint_results: dict[str, bool] = {}
        for constraint in task_constraints:
            prompt = _CONSTRAINT_PROMPT.format(
                constraint=constraint, prediction=pred_text
            )
            judge_responses = judge.generate(prompt, temperature=0.0)
            answer = judge_responses[0].text.strip().upper() if judge_responses else ""
            constraint_results[constraint] = answer.startswith("YES")

        satisfied = sum(1 for v in constraint_results.values() if v)
        total = len(task_constraints)
        score = satisfied / total

        results.append(
            TaskResult(
                task_id=str(i),
                score=score,
                passed=score >= 0.5,
                prediction=pred_text,
                metadata={
                    "constraint_results": constraint_results,
                    "satisfied": satisfied,
                    "total": total,
                },
            )
        )

    return results
