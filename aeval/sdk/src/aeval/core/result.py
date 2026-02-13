"""Result dataclasses for aeval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfidenceInterval:
    """Confidence interval for a score."""

    lower: float
    upper: float
    level: float = 0.95

    @property
    def margin(self) -> float:
        return (self.upper - self.lower) / 2

    def __str__(self) -> str:
        return f"[{self.lower:.3f}, {self.upper:.3f}] ({self.level:.0%} CI)"


@dataclass
class TaskResult:
    """Result for a single eval task (one prompt)."""

    task_id: str
    score: float
    passed: bool | None = None
    prediction: str = ""
    reference: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Aggregated result for an entire eval run."""

    eval_name: str
    model_name: str
    score: float
    ci: ConfidenceInterval | None = None
    baseline_delta: float | None = None
    p_value: float | None = None
    significant: bool | None = None
    effect_size: float | None = None
    num_tasks: int = 0
    passed: bool | None = None
    threshold: float | None = None
    task_results: list[TaskResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float | None:
        """Fraction of tasks that passed, if pass/fail is defined."""
        passed_tasks = [t for t in self.task_results if t.passed is not None]
        if not passed_tasks:
            return None
        return sum(1 for t in passed_tasks if t.passed) / len(passed_tasks)

    def summary(self) -> str:
        parts = [f"{self.eval_name} on {self.model_name}: {self.score:.3f}"]
        if self.ci:
            parts.append(f"(±{self.ci.margin:.3f}, {self.ci.level:.0%} CI)")
        if self.baseline_delta is not None:
            sign = "+" if self.baseline_delta >= 0 else ""
            parts.append(f"vs. baseline: {sign}{self.baseline_delta:.3f}")
        if self.p_value is not None:
            sig = "significant" if self.significant else "not significant"
            parts.append(f"(p={self.p_value:.3f}, {sig})")
        if self.passed is not None:
            parts.append("PASS" if self.passed else "FAIL")
        return " ".join(parts)
