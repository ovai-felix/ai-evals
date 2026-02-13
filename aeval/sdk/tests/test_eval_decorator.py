"""Tests for @Eval decorator and eval execution."""

from unittest.mock import MagicMock

import pytest

from aeval.core.eval import Eval, EvalDefinition, get_eval, list_evals, _EVAL_REGISTRY
from aeval.core.result import EvalResult, TaskResult


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear eval registry before each test."""
    _EVAL_REGISTRY.clear()
    yield
    _EVAL_REGISTRY.clear()


def _make_mock_model(name="test-model"):
    model = MagicMock()
    model.name = name
    return model


def test_eval_decorator_registers():
    @Eval(name="test-eval", tags=["test"])
    def my_eval(model):
        return 0.85

    assert isinstance(my_eval, EvalDefinition)
    assert get_eval("test-eval") is my_eval
    assert my_eval.name == "test-eval"
    assert my_eval.tags == ["test"]


def test_eval_decorator_with_threshold():
    @Eval(name="threshold-eval", threshold=0.8)
    def my_eval(model):
        return 0.85

    model = _make_mock_model()
    result = my_eval.run(model)
    assert result.score == 0.85
    assert result.passed is True
    assert result.threshold == 0.8


def test_eval_returns_float():
    @Eval(name="float-eval")
    def my_eval(model):
        return 0.75

    model = _make_mock_model()
    result = my_eval.run(model)
    assert result.score == 0.75
    assert result.eval_name == "float-eval"
    assert result.model_name == "test-model"


def test_eval_returns_list_of_floats():
    @Eval(name="list-eval")
    def my_eval(model):
        return [0.8, 0.9, 0.7, 1.0]

    model = _make_mock_model()
    result = my_eval.run(model)
    assert result.score == pytest.approx(0.85)
    assert result.num_tasks == 4
    assert result.ci is not None
    assert len(result.task_results) == 4


def test_eval_returns_task_results():
    @Eval(name="task-eval")
    def my_eval(model):
        return [
            TaskResult(task_id="0", score=1.0, passed=True),
            TaskResult(task_id="1", score=0.0, passed=False),
        ]

    model = _make_mock_model()
    result = my_eval.run(model)
    assert result.score == 0.5
    assert result.num_tasks == 2


def test_eval_returns_eval_result():
    @Eval(name="result-eval")
    def my_eval(model):
        return EvalResult(
            eval_name="custom", model_name="custom-model", score=0.92, num_tasks=10
        )

    model = _make_mock_model()
    result = my_eval.run(model)
    assert result.score == 0.92


def test_eval_returns_invalid_type():
    @Eval(name="bad-eval")
    def my_eval(model):
        return "not a valid return type"

    model = _make_mock_model()
    with pytest.raises(TypeError, match="Eval function must return"):
        my_eval.run(model)


def test_list_evals():
    @Eval(name="eval-a")
    def eval_a(model):
        return 0.5

    @Eval(name="eval-b")
    def eval_b(model):
        return 0.6

    evals = list_evals()
    names = [e.name for e in evals]
    assert "eval-a" in names
    assert "eval-b" in names


def test_eval_threshold_fail():
    @Eval(name="fail-eval", threshold=0.9)
    def my_eval(model):
        return 0.5

    model = _make_mock_model()
    result = my_eval.run(model)
    assert result.passed is False


def test_eval_elapsed_time():
    @Eval(name="timed-eval")
    def my_eval(model):
        return 0.5

    model = _make_mock_model()
    result = my_eval.run(model)
    assert "elapsed_seconds" in result.metadata
    assert result.metadata["elapsed_seconds"] >= 0
