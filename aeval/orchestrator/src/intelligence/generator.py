"""LLM-powered eval generation with quality gates."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx
import yaml

logger = logging.getLogger(__name__)

# Default Ollama host for the orchestrator container
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
GENERATOR_MODEL = os.environ.get("INTELLIGENCE_GENERATOR_MODEL", "gemma3")


def generate_capability_probe(
    node_name: str,
    node_description: str,
    *,
    count: int = 5,
    model: str | None = None,
) -> list[dict[str, str]]:
    """Generate eval tasks probing a specific capability.

    Prompts an LLM to create evaluation tasks that test the given
    taxonomy capability. Each task has a prompt and reference answer.
    """
    model = model or GENERATOR_MODEL
    prompt = f"""You are an AI evaluation expert. Generate exactly {count} evaluation tasks
that test the following capability:

Capability: {node_name}
Description: {node_description}

Requirements for each task:
1. The prompt should be a clear, specific question or instruction
2. The reference answer should be a correct, concise answer
3. Tasks should vary in difficulty (easy, medium, hard)
4. Tasks should be unambiguous — a human expert would agree on the reference answer

Return your response as a JSON array of objects with "prompt" and "reference" keys.
Return ONLY the JSON array, no other text."""

    raw = _call_ollama(prompt, model)
    tasks = _parse_json_array(raw)
    return _apply_quality_gates(tasks, model)


def generate_adversarial(
    node_name: str,
    existing_tasks: list[dict[str, str]],
    *,
    count: int = 5,
    model: str | None = None,
) -> list[dict[str, str]]:
    """Generate adversarial edge-case tasks targeting model weaknesses."""
    model = model or GENERATOR_MODEL
    examples = json.dumps(existing_tasks[:3], indent=2) if existing_tasks else "[]"

    prompt = f"""You are an AI evaluation expert specializing in adversarial testing.
Generate exactly {count} challenging edge-case evaluation tasks for:

Capability: {node_name}

Here are some existing tasks for context:
{examples}

Requirements:
1. Tasks should target common failure modes and edge cases
2. Tasks should be tricky but fair — a capable model should be able to answer correctly
3. Include diverse failure modes (ambiguity, misdirection, boundary conditions)
4. Each task must have a clear correct reference answer

Return your response as a JSON array of objects with "prompt" and "reference" keys.
Return ONLY the JSON array, no other text."""

    raw = _call_ollama(prompt, model)
    tasks = _parse_json_array(raw)
    return _apply_quality_gates(tasks, model)


def generate_difficulty_escalation(
    eval_name: str,
    existing_tasks: list[dict[str, str]],
    *,
    count: int = 5,
    model: str | None = None,
) -> list[dict[str, str]]:
    """Generate harder versions of existing eval tasks for saturated evals."""
    model = model or GENERATOR_MODEL
    examples = json.dumps(existing_tasks[:5], indent=2) if existing_tasks else "[]"

    prompt = f"""You are an AI evaluation expert. The eval "{eval_name}" is becoming saturated —
most models score very high on it. Generate {count} significantly harder tasks.

Current example tasks:
{examples}

Requirements:
1. Each new task should be notably harder than the examples
2. Add complexity: multi-step reasoning, subtle distinctions, longer context
3. Maintain the same general capability domain
4. Each task must have a clear correct reference answer

Return your response as a JSON array of objects with "prompt" and "reference" keys.
Return ONLY the JSON array, no other text."""

    raw = _call_ollama(prompt, model)
    tasks = _parse_json_array(raw)
    return _apply_quality_gates(tasks, model)


def store_generated_eval(
    tasks: list[dict[str, str]],
    eval_name: str,
    *,
    generation_method: str,
    taxonomy_node: str | None = None,
) -> str:
    """Write generated tasks to registry-data as a new eval package.

    Creates:
    - registry-data/{eval_name}/meta.yaml
    - registry-data/{eval_name}/dataset.jsonl
    - registry-data/{eval_name}/eval.py
    """
    base = Path("/app/registry-data")
    if not base.exists():
        base = Path("registry-data")
    base.mkdir(parents=True, exist_ok=True)

    eval_dir = base / eval_name
    eval_dir.mkdir(parents=True, exist_ok=True)

    # meta.yaml
    meta = {
        "name": eval_name,
        "version": "0.1.0",
        "description": f"Auto-generated eval for {taxonomy_node or eval_name}",
        "category": taxonomy_node or "generated",
        "tags": ["generated", generation_method],
        "threshold": 0.7,
        "dataset": "dataset.jsonl",
        "generated": True,
        "generation_method": generation_method,
        "taxonomy_node": taxonomy_node,
    }
    with open(eval_dir / "meta.yaml", "w") as f:
        yaml.dump(meta, f, default_flow_style=False, sort_keys=False)

    # dataset.jsonl
    with open(eval_dir / "dataset.jsonl", "w") as f:
        for task in tasks:
            f.write(json.dumps(task) + "\n")

    # eval.py — template using llm_judge scorer
    eval_code = f'''"""Auto-generated eval: {eval_name}."""

from aeval.core.eval import Eval
from aeval.core.dataset import Dataset
from aeval.core.scorer import Scorer
from aeval.core.result import TaskResult


@Eval(
    name="{eval_name}",
    tags=["generated", "{generation_method}"],
    threshold=0.7,
    description="Auto-generated eval for {taxonomy_node or eval_name}",
)
def {eval_name.replace("-", "_")}(model):
    dataset = Dataset.from_jsonl("{eval_dir}/dataset.jsonl")
    responses = model.generate(dataset.prompts)
    predictions = [r.text for r in responses]

    scores = Scorer.llm_judge(
        predictions=predictions,
        references=dataset.references,
        judge_model=model.name,
        rubric="Rate the accuracy and completeness of the answer on a scale of 0-1.",
        scale=(0, 1),
    )

    return [
        TaskResult(
            task_id=f"task-{{i}}",
            score=s,
            passed=s >= 0.7,
            prediction=p,
            reference=r,
        )
        for i, (s, p, r) in enumerate(zip(scores, predictions, dataset.references))
    ]
'''
    with open(eval_dir / "eval.py", "w") as f:
        f.write(eval_code)

    return eval_name


# ---- Internal helpers ----


def _call_ollama(prompt: str, model: str) -> str:
    """Call Ollama's generate API and return the response text."""
    with httpx.Client(base_url=OLLAMA_HOST, timeout=120) as client:
        resp = client.post(
            "/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7},
            },
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


def _parse_json_array(text: str) -> list[dict[str, str]]:
    """Extract a JSON array from LLM response text."""
    # Try direct parse first
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find JSON array in the text
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse JSON array from LLM response")
    return []


def _apply_quality_gates(
    tasks: list[dict[str, str]], model: str
) -> list[dict[str, str]]:
    """Filter tasks through quality gates."""
    passed = []
    for task in tasks:
        if not _has_reference(task):
            continue
        if _clarity_check(task, model):
            passed.append(task)
    return passed


def _has_reference(task: dict[str, str]) -> bool:
    """Check that a task has both a prompt and a non-empty reference answer."""
    return bool(task.get("prompt")) and bool(task.get("reference"))


def _clarity_check(task: dict[str, str], model: str) -> bool:
    """Ask the LLM to rate task clarity. Requires score >= 4/5."""
    prompt = f"""Rate the clarity of this evaluation task on a scale of 1-5.
1 = very unclear/ambiguous, 5 = perfectly clear and unambiguous.

Task prompt: {task['prompt']}
Reference answer: {task['reference']}

Return ONLY a single integer (1-5)."""

    try:
        response = _call_ollama(prompt, model)
        # Extract first digit from response
        digits = re.findall(r"\d", response)
        if digits:
            score = int(digits[0])
            return score >= 4
    except Exception:
        logger.warning("Clarity check failed, accepting task")

    # Default to accepting if check fails
    return True
