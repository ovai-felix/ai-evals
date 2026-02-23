"""Semantic similarity scorer using TF-IDF vectors and cosine similarity."""

from __future__ import annotations

import math
from collections import Counter
from typing import TYPE_CHECKING

from aeval.core.result import TaskResult

if TYPE_CHECKING:
    from aeval.core.model import GenerateResponse


def _extract_text(pred: GenerateResponse | str) -> str:
    if isinstance(pred, str):
        return pred
    return pred.text


def _extract_response(pred: GenerateResponse | str) -> tuple[str, float, int]:
    if isinstance(pred, str):
        return pred, 0.0, 0
    return pred.text, pred.latency_ms, pred.tokens_used


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercased tokenization."""
    return text.lower().split()


def _build_tfidf_vectors(
    doc_a: str, doc_b: str
) -> tuple[list[float], list[float]]:
    """Build TF-IDF vectors for two documents against each other as corpus."""
    tokens_a = _tokenize(doc_a)
    tokens_b = _tokenize(doc_b)

    if not tokens_a or not tokens_b:
        return [], []

    # Build vocabulary from both documents
    vocab = sorted(set(tokens_a) | set(tokens_b))
    vocab_index = {term: i for i, term in enumerate(vocab)}

    # Term frequency per document
    tf_a = Counter(tokens_a)
    tf_b = Counter(tokens_b)

    # Smoothed IDF: log((N + 1) / (df + 1)) + 1 to avoid zero vectors
    n_docs = 2
    idf = {}
    for term in vocab:
        df = (1 if term in tf_a else 0) + (1 if term in tf_b else 0)
        idf[term] = math.log((n_docs + 1) / (df + 1)) + 1.0

    # TF-IDF vectors
    vec_a = [0.0] * len(vocab)
    vec_b = [0.0] * len(vocab)

    for term, idx in vocab_index.items():
        vec_a[idx] = (tf_a[term] / len(tokens_a)) * idf[term] if tokens_a else 0.0
        vec_b[idx] = (tf_b[term] / len(tokens_b)) * idf[term] if tokens_b else 0.0

    return vec_a, vec_b


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec_a or not vec_b:
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def score_semantic_similarity(
    predictions: list[GenerateResponse | str],
    references: list[str],
    *,
    threshold: float = 0.6,
) -> list[TaskResult]:
    """Score predictions by semantic similarity to references using TF-IDF cosine similarity.

    Args:
        predictions: Model outputs.
        references: Reference answers.
        threshold: Minimum similarity to pass (default 0.6).

    Returns:
        List of TaskResult with cosine similarity scores (0.0–1.0).
    """
    if len(predictions) != len(references):
        raise ValueError(
            f"Length mismatch: {len(predictions)} predictions vs {len(references)} references"
        )

    results = []
    for i, (pred, ref) in enumerate(zip(predictions, references)):
        pred_text, latency_ms, tokens_used = _extract_response(pred)
        vec_a, vec_b = _build_tfidf_vectors(pred_text, ref)
        similarity = _cosine_similarity(vec_a, vec_b)

        results.append(
            TaskResult(
                task_id=str(i),
                score=similarity,
                passed=similarity >= threshold,
                prediction=pred_text,
                reference=ref,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                metadata={
                    "similarity": similarity,
                    "method": "tfidf_cosine",
                },
            )
        )

    return results
