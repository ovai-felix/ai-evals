"""Reasoning v1 — multiple choice scoring with system prompt."""

from aeval import Eval, Dataset, Scorer


_SYSTEM_PROMPT = (
    "You are taking a multiple choice test. "
    "Read each question carefully and select the best answer. "
    "Respond with ONLY the letter of your answer (A, B, C, or D)."
)


@Eval(
    name="reasoning-v1",
    tags=["reasoning", "multiple-choice", "core", "v1"],
    threshold=0.5,
    description="25-item multiple choice reasoning evaluation.",
    category="reasoning",
    version="1.0",
)
def reasoning_v1(model):
    dataset = Dataset.from_jsonl("datasets/reasoning-v1.jsonl", answer_key="answer")
    responses = model.generate(dataset.prompts, system=_SYSTEM_PROMPT)
    return Scorer.multiple_choice(responses, dataset.answers)
