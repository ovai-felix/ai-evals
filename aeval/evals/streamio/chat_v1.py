from aeval import Eval, Dataset, Scorer, Rubrics
from aeval.core.result import TaskResult


@Eval(
    name="streamio-chat-v1",
    tags=["streamio", "chat", "v1"],
    threshold=0.65,
    description="StreamIO chat assistant quality evaluation — multi-dimensional scoring.",
)
def streamio_chat_v1(model):
    dataset = Dataset.from_jsonl("datasets/streamio-chat-v1.jsonl")

    system_prompt = (
        "You are a helpful AI assistant for screen recording and analysis. "
        "Provide clear, actionable insights and suggestions."
    )

    responses = model.generate(
        dataset.prompts,
        system=system_prompt,
        temperature=0.7,
    )

    # Score on 3 dimensions using LLM judge with different rubrics
    helpfulness_results = Scorer.llm_judge(
        responses,
        dataset.references,
        rubric=(
            "Rate the response on helpfulness, clarity, and actionability. "
            "A good response should directly address the user's question, "
            "provide clear and well-structured information, and offer "
            "actionable suggestions or next steps where appropriate."
        ),
        scale=5,
    )

    completeness_results = Scorer.llm_judge(
        responses,
        dataset.references,
        rubric=Rubrics.COMPLETENESS.format(scale=5),
        scale=5,
    )

    faithfulness_results = Scorer.llm_judge(
        responses,
        dataset.references,
        rubric=Rubrics.FAITHFULNESS.format(scale=5),
        scale=5,
    )

    # Combine with weights: helpfulness 50%, completeness 30%, faithfulness 20%
    combined_results = []
    for i, (h, c, f) in enumerate(
        zip(helpfulness_results, completeness_results, faithfulness_results)
    ):
        weighted_score = 0.5 * h.score + 0.3 * c.score + 0.2 * f.score

        combined_results.append(
            TaskResult(
                task_id=str(i),
                score=weighted_score,
                passed=weighted_score >= 0.6,
                prediction=h.prediction,
                reference=h.reference,
                latency_ms=h.latency_ms,
                tokens_used=h.tokens_used,
                metadata={
                    "helpfulness_score": h.score,
                    "completeness_score": c.score,
                    "faithfulness_score": f.score,
                    "weights": {"helpfulness": 0.5, "completeness": 0.3, "faithfulness": 0.2},
                },
            )
        )

    return combined_results
