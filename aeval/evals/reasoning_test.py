"""Reasoning eval — math and logic with exact match."""

from aeval import Eval, Dataset, Scorer


@Eval(name="reasoning-test", tags=["reasoning", "math", "test"], threshold=0.7)
def reasoning_eval(model):
    dataset = Dataset.from_jsonl("datasets/reasoning-test.jsonl")
    results = model.generate(dataset.prompts)
    return Scorer.exact_match(results, dataset.references)
