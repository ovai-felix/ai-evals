"""Auto-generated eval: gen-code-debugging-capability_probe."""

from aeval.core.eval import Eval
from aeval.core.dataset import Dataset
from aeval.core.scorer import Scorer
from aeval.core.result import TaskResult


@Eval(
    name="gen-code-debugging-capability_probe",
    tags=["generated", "capability_probe"],
    threshold=0.7,
    description="Auto-generated eval for Code Debugging",
)
def gen_code_debugging_capability_probe(model):
    dataset = Dataset.from_jsonl("/app/registry-data/gen-code-debugging-capability_probe/dataset.jsonl")
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
            task_id=f"task-{i}",
            score=s,
            passed=s >= 0.7,
            prediction=p,
            reference=r,
        )
        for i, (s, p, r) in enumerate(zip(scores, predictions, dataset.references))
    ]
