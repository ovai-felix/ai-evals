from aeval import Eval, Dataset, Scorer


SCREEN_ANALYSIS_SYSTEM_PROMPT = """\
You are an expert visual AI assistant. You will be provided with an image (such as a screenshot or photo) and, optionally, a user question or prompt.

Your tasks:
- Carefully analyze the image you receive and provide a detailed description of what you see in relation to the user's question.
- Describe in detail what you see.
- If the user asks a specific question, answer it using only the information visible in the image.
- If relevant, provide suggestions, insights, or next steps based on the image content.
- If the image is unclear or missing, politely inform the user.

Always base your response on the actual image provided. Respond directly to the user's specific question while providing relevant context and insights about the screen content."""


@Eval(
    name="streamio-screen-analysis-v1",
    tags=["streamio", "vision", "screen-analysis", "v1"],
    threshold=0.60,
    description="StreamIO screen analysis quality with vision.",
)
def streamio_screen_analysis_v1(model):
    dataset = Dataset.from_jsonl("datasets/streamio-screen-v1.jsonl")

    responses = model.generate(
        dataset.prompts,
        system=SCREEN_ANALYSIS_SYSTEM_PROMPT,
        images=dataset.images,
        temperature=0.7,
    )

    return Scorer.llm_judge(
        responses,
        dataset.references,
        rubric=(
            "Rate the response on visual analysis accuracy, level of detail, "
            "and actionability. A good response should correctly identify and "
            "describe elements visible in the image, provide sufficient detail "
            "to be useful, and offer actionable insights or suggestions based "
            "on what is observed."
        ),
        scale=5,
    )
