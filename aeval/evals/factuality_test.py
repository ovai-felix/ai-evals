"""Simple factuality eval — capital cities with exact match."""

from aeval import Eval, Dataset, Scorer


@Eval(name="factuality-test", tags=["factuality", "test"], threshold=0.7)
def factuality_eval(model):
    dataset = Dataset.from_jsonl("datasets/factuality-test.jsonl")
    results = model.generate(dataset.prompts)
    return Scorer.exact_match(results, dataset.references)
