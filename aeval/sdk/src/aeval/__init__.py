"""aeval — AI Evaluation Pipeline SDK."""

from aeval.core.eval import Eval
from aeval.core.dataset import Dataset
from aeval.core.model import Model
from aeval.core.result import EvalResult, TaskResult
from aeval.core.scorer import Scorer
from aeval.core.suite import SuiteDefinition

__all__ = [
    "Eval",
    "Dataset",
    "Model",
    "Scorer",
    "EvalResult",
    "TaskResult",
    "SuiteDefinition",
]
__version__ = "0.1.0"
