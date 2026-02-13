"""Factuality v1 — exact match with LLM-judge fallback for failed items."""

import logging

from aeval import Eval, Dataset, Scorer
from aeval.core.result import TaskResult

logger = logging.getLogger(__name__)


@Eval(
    name="factuality-v1",
    tags=["factuality", "core", "v1"],
    threshold=0.6,
    description="25-item factual Q&A with exact match and LLM-judge fallback.",
    category="factuality",
    version="1.0",
)
def factuality_v1(model):
    dataset = Dataset.from_jsonl("datasets/factuality-v1.jsonl")
    responses = model.generate(dataset.prompts)

    # Primary scoring: exact match (includes contains-match fallback)
    results = Scorer.exact_match(responses, dataset.references)

    # Fallback: re-score failed items with LLM judge
    failed_indices = [i for i, r in enumerate(results) if r.score < 1.0]
    if failed_indices:
        failed_preds = [responses[i] for i in failed_indices]
        failed_refs = [dataset.references[i] for i in failed_indices]
        try:
            judge_results = Scorer.llm_judge(failed_preds, failed_refs, scale=5)
            for idx, jr in zip(failed_indices, judge_results):
                if jr.score >= 0.8:
                    results[idx] = TaskResult(
                        task_id=str(idx),
                        score=jr.score,
                        passed=True,
                        prediction=results[idx].prediction,
                        reference=results[idx].reference,
                        metadata={"scorer": "llm_judge_fallback", **jr.metadata},
                    )
        except Exception as e:
            logger.warning(
                "LLM judge fallback failed (%s), keeping exact-match scores: %s",
                type(e).__name__, e,
            )

    return results
