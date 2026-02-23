"""Predefined rubric presets for the LLM judge scorer."""


class Rubrics:
    """Predefined rubric strings for use with Scorer.llm_judge(rubric=...)."""

    COMPLETENESS = (
        "Rate the response on completeness on a scale of 1 to {scale}.\n"
        "1 = The response addresses none of the parts of the question.\n"
        "2 = The response addresses only a small portion of the question.\n"
        "3 = The response addresses roughly half of the question's parts.\n"
        "4 = The response addresses most parts but misses minor elements.\n"
        "5 = The response fully addresses every part of the question.\n"
        "Respond with ONLY a single number between 1 and {scale}."
    )

    FAITHFULNESS = (
        "Rate the response on faithfulness on a scale of 1 to {scale}.\n"
        "1 = The response contains multiple unsupported or fabricated claims.\n"
        "2 = The response has several claims not grounded in the provided context.\n"
        "3 = Some claims are supported, but important ones lack evidence.\n"
        "4 = Most claims are supported by the context with minor gaps.\n"
        "5 = Every claim in the response is directly supported by the provided context.\n"
        "Respond with ONLY a single number between 1 and {scale}."
    )

    COT_COHERENCE = (
        "Rate the chain-of-thought reasoning on coherence on a scale of 1 to {scale}.\n"
        "1 = Reasoning steps are contradictory or logically invalid.\n"
        "2 = Multiple logical gaps or non-sequiturs in the reasoning chain.\n"
        "3 = Reasoning is partially coherent but has some unclear leaps.\n"
        "4 = Reasoning is mostly sound with only minor logical weaknesses.\n"
        "5 = Every reasoning step follows logically and consistently from the previous.\n"
        "Respond with ONLY a single number between 1 and {scale}."
    )

    GROUNDEDNESS = (
        "Rate the response on groundedness on a scale of 1 to {scale}.\n"
        "1 = No assertions can be traced back to any source or evidence.\n"
        "2 = Few assertions are traceable to sources.\n"
        "3 = About half of the assertions are traceable to sources.\n"
        "4 = Most assertions are traceable, with minor unsourced claims.\n"
        "5 = Every assertion in the response is traceable to a cited source.\n"
        "Respond with ONLY a single number between 1 and {scale}."
    )
