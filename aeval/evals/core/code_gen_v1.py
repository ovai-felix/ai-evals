"""Code generation v1 — subprocess execution with test assertions and LLM-judge fallback."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from aeval import Eval, Scorer
from aeval.core.result import TaskResult


_SYSTEM_PROMPT = (
    "You are an expert Python programmer. "
    "Write clean, correct Python code that solves the given task. "
    "Return ONLY the Python code, wrapped in a ```python code block. "
    "Do not include explanations outside the code block."
)


def _extract_python(text: str) -> str:
    """Extract Python code from markdown code blocks."""
    # Try ```python ... ``` first
    match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try ``` ... ``` (generic code block)
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: return the whole text (might be raw code)
    return text.strip()


def _run_code_with_tests(code: str, test_code: str, timeout: int = 10) -> tuple[bool, str]:
    """Execute code + tests in a subprocess. Returns (passed, output)."""
    full_code = f"{code}\n\n{test_code}\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(full_code)
        f.flush()
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Execution timed out"
    except Exception as e:
        return False, str(e)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@Eval(
    name="code-gen-v1",
    tags=["code-generation", "execution", "core", "v1"],
    threshold=0.5,
    description="15-item code generation eval with subprocess execution and LLM-judge fallback.",
    category="code-generation",
    version="1.0",
)
def code_gen_v1(model):
    # Load raw JSON since we need the test_code field
    dataset_path = Path("datasets/code-gen-v1.jsonl")
    items = []
    with open(dataset_path) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    prompts = [item["prompt"] for item in items]
    responses = model.generate(prompts, system=_SYSTEM_PROMPT)

    results = []
    failed_indices = []

    for i, (resp, item) in enumerate(zip(responses, items)):
        pred_text = resp.text if hasattr(resp, "text") else str(resp)
        code = _extract_python(pred_text)
        test_code = item.get("test_code", "")

        if test_code:
            passed, output = _run_code_with_tests(code, test_code)
            results.append(
                TaskResult(
                    task_id=str(i),
                    score=1.0 if passed else 0.0,
                    passed=passed,
                    prediction=pred_text,
                    reference=item.get("reference", ""),
                    metadata={
                        "extracted_code": code,
                        "test_output": output[:500],
                        "scorer": "execution",
                    },
                )
            )
            if not passed:
                failed_indices.append(i)
        else:
            results.append(
                TaskResult(
                    task_id=str(i),
                    score=0.0,
                    passed=False,
                    prediction=pred_text,
                    reference=item.get("reference", ""),
                    metadata={"scorer": "no_tests"},
                )
            )
            failed_indices.append(i)

    # LLM-judge fallback for failed items
    if failed_indices:
        failed_preds = [responses[i] for i in failed_indices]
        failed_refs = [items[i].get("reference", "") for i in failed_indices]
        try:
            judge_results = Scorer.llm_judge(
                failed_preds,
                failed_refs,
                rubric=(
                    "Rate the code quality and correctness on a scale of 1 to 5.\n"
                    "Consider: Does it solve the stated problem? Is the logic correct?\n"
                    "Respond with ONLY a single number between 1 and 5."
                ),
                scale=5,
            )
            for idx, jr in zip(failed_indices, judge_results):
                if jr.score >= 0.6:
                    results[idx] = TaskResult(
                        task_id=str(idx),
                        score=jr.score,
                        passed=jr.score >= 0.6,
                        prediction=results[idx].prediction,
                        reference=results[idx].reference,
                        metadata={
                            **results[idx].metadata,
                            "scorer": "llm_judge_fallback",
                            **jr.metadata,
                        },
                    )
        except Exception:
            pass  # Keep execution scores on judge failure

    return results
