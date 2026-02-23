"""aeval — AI Evaluation Pipeline SDK."""

from aeval.core.eval import Eval
from aeval.core.dataset import Dataset
from aeval.core.model import Model
from aeval.core.result import EvalResult, TaskResult
from aeval.core.scorer import Scorer
from aeval.core.suite import SuiteDefinition
from aeval.scorers.rubrics import Rubrics

__all__ = [
    "Eval",
    "Dataset",
    "Model",
    "Scorer",
    "EvalResult",
    "TaskResult",
    "SuiteDefinition",
    "Rubrics",
]
__version__ = "0.1.0"

# Module-level verbose flag — set by CLI --verbose to enable real-time progress
VERBOSE = False

# Module-level judge model override — set by CLI to use same provider as eval model
# When None, falls back to the default in each scorer (ollama:gpt-oss:20b)
JUDGE_MODEL: str | None = None
