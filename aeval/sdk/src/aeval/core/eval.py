"""@Eval decorator for registering eval functions."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from aeval.core.model import Model
from aeval.core.result import EvalResult, TaskResult
from aeval.stats.significance import confidence_interval


# Global registry of eval definitions
_EVAL_REGISTRY: dict[str, EvalDefinition] = {}


@dataclass
class EvalDefinition:
    """A registered eval definition."""

    name: str
    func: Callable
    tags: list[str] = field(default_factory=list)
    threshold: float | None = None
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def run(self, model: Model, **kwargs) -> EvalResult:
        """Execute this eval against a model."""
        start = time.time()
        raw_result = self.func(model, **kwargs)
        elapsed = time.time() - start

        # The eval function can return different types:
        # 1. EvalResult - fully formed result
        # 2. list[TaskResult] - list of per-task results
        # 3. list[float] - list of scores
        # 4. float - single aggregate score
        if isinstance(raw_result, EvalResult):
            result = raw_result
            result.eval_name = result.eval_name or self.name
            result.model_name = result.model_name or model.name
        elif isinstance(raw_result, list) and raw_result and isinstance(raw_result[0], TaskResult):
            scores = [t.score for t in raw_result]
            mean_score = sum(scores) / len(scores) if scores else 0.0
            ci = confidence_interval(scores) if len(scores) >= 2 else None
            result = EvalResult(
                eval_name=self.name,
                model_name=model.name,
                score=mean_score,
                ci=ci,
                num_tasks=len(raw_result),
                task_results=raw_result,
            )
        elif isinstance(raw_result, list):
            scores = [float(s) for s in raw_result]
            mean_score = sum(scores) / len(scores) if scores else 0.0
            ci = confidence_interval(scores) if len(scores) >= 2 else None
            task_results = [
                TaskResult(task_id=str(i), score=s) for i, s in enumerate(scores)
            ]
            result = EvalResult(
                eval_name=self.name,
                model_name=model.name,
                score=mean_score,
                ci=ci,
                num_tasks=len(scores),
                task_results=task_results,
            )
        elif isinstance(raw_result, (int, float)):
            result = EvalResult(
                eval_name=self.name,
                model_name=model.name,
                score=float(raw_result),
                num_tasks=1,
            )
        else:
            raise TypeError(
                f"Eval function must return EvalResult, list[TaskResult], list[float], or float. "
                f"Got {type(raw_result).__name__}"
            )

        # Apply threshold
        if self.threshold is not None and result.passed is None:
            result.passed = result.score >= self.threshold
            result.threshold = self.threshold

        result.metadata["elapsed_seconds"] = elapsed
        return result


class Eval:
    """Decorator to register a function as an eval.

    Usage:
        @Eval(name="my-eval", tags=["factuality"])
        def my_eval(model):
            dataset = Dataset.load("my-data.jsonl")
            results = model.generate(dataset.prompts)
            return Scorer.exact_match(results, dataset.references)
    """

    def __init__(
        self,
        name: str,
        *,
        tags: list[str] | None = None,
        threshold: float | None = None,
        description: str = "",
        **metadata: Any,
    ):
        self.name = name
        self.tags = tags or []
        self.threshold = threshold
        self.description = description
        self.metadata = metadata

    def __call__(self, func: Callable) -> EvalDefinition:
        definition = EvalDefinition(
            name=self.name,
            func=func,
            tags=self.tags,
            threshold=self.threshold,
            description=self.description,
            metadata=self.metadata,
        )
        _EVAL_REGISTRY[self.name] = definition
        return definition


def get_eval(name: str) -> EvalDefinition | None:
    """Get a registered eval by name."""
    return _EVAL_REGISTRY.get(name)


def list_evals() -> list[EvalDefinition]:
    """List all registered evals."""
    return list(_EVAL_REGISTRY.values())


def load_eval_file(path: str) -> list[EvalDefinition]:
    """Load eval definitions from a Python file by executing it."""
    import importlib.util
    import sys

    # Use a unique module name per file to avoid collisions when loading
    # multiple eval files in the same worker process.
    module_name = f"_aeval_eval_{hash(path)}"
    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load eval file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    # Snapshot registry values (not just keys) so we detect both new
    # registrations AND re-registrations of existing names.
    before = dict(_EVAL_REGISTRY)
    spec.loader.exec_module(module)

    new_or_updated = [
        defn for name, defn in _EVAL_REGISTRY.items()
        if name not in before or before[name] is not defn
    ]
    return new_or_updated
