from aeval import Eval, Dataset, Scorer


@Eval(
    name="streamio-summary-v1",
    tags=["streamio", "summary", "v1"],
    threshold=0.65,
    description="StreamIO conversation summary quality.",
)
def streamio_summary_v1(model):
    dataset = Dataset.from_jsonl("datasets/streamio-summary-v1.jsonl")

    system_prompt = (
        "You are an expert at summarizing conversations and extracting key insights."
    )

    responses = model.generate(
        dataset.prompts,
        system=system_prompt,
        temperature=0.3,
    )

    return Scorer.llm_judge(
        responses,
        dataset.references,
        rubric=(
            "Rate the response on summary completeness, key point extraction, "
            "and conciseness. A good response should capture all important "
            "points from the conversation, correctly identify and extract key "
            "insights and decisions, and present the summary in a concise and "
            "well-organized manner without unnecessary verbosity."
        ),
        scale=5,
    )
