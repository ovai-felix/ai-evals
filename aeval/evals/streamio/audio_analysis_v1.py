from aeval import Eval, Dataset, Scorer


@Eval(
    name="streamio-audio-analysis-v1",
    tags=["streamio", "audio", "json", "v1"],
    threshold=0.75,
    description="StreamIO audio analysis JSON structure validation.",
)
def streamio_audio_analysis_v1(model):
    dataset = Dataset.from_jsonl("datasets/streamio-audio-v1.jsonl")

    system_prompt = (
        "You are an AI assistant that analyzes audio transcriptions and "
        "provides insights. Respond in JSON format."
    )

    responses = model.generate(
        dataset.prompts,
        system=system_prompt,
        temperature=0.3,
    )

    return Scorer.json_schema(
        responses,
        required_fields=["analysis", "insights", "actions", "confidence"],
    )
