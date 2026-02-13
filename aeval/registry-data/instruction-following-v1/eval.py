"""Instruction following v1 — LLM-judge scoring for instruction adherence."""

from aeval import Eval, Dataset, Scorer


_RUBRIC = (
    "Rate how well the response follows the given instructions on a scale of 1 to 5.\n"
    "1 = Completely ignores the instructions\n"
    "2 = Partially follows but misses key requirements\n"
    "3 = Follows most instructions with minor deviations\n"
    "4 = Follows all instructions with very minor issues\n"
    "5 = Perfectly follows every instruction\n"
    "Respond with ONLY a single number between 1 and 5."
)


@Eval(
    name="instruction-following-v1",
    tags=["instruction-following", "llm-judge", "core", "v1"],
    threshold=0.6,
    description="20-item instruction adherence eval scored by LLM judge.",
    category="instruction-following",
    version="1.0",
)
def instruction_following_v1(model):
    dataset = Dataset.from_jsonl("datasets/instruction-following-v1.jsonl")
    responses = model.generate(dataset.prompts)
    return Scorer.llm_judge(responses, dataset.references, rubric=_RUBRIC, scale=5)
