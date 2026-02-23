from aeval import Eval, Dataset, Scorer

from .screen_analysis_v1 import SCREEN_ANALYSIS_SYSTEM_PROMPT


@Eval(
    name="streamio-live-frame-v1",
    tags=["streamio", "vision", "live-frame", "v1"],
    threshold=0.60,
    description="StreamIO live frame analysis quality with vision.",
)
def streamio_live_frame_v1(model):
    dataset = Dataset.from_jsonl("datasets/streamio-live-frame-v1.jsonl")

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
            "Rate the response on real-time visual analysis quality. A good "
            "response should accurately identify and describe what is happening "
            "in the live frame, provide timely and relevant observations, and "
            "offer useful context or suggestions based on the current screen state."
        ),
        scale=5,
    )
