"""Eval execution — the rq job function."""

from __future__ import annotations

import logging
import os
import time

from orchestrator.db.runs_repo import get_run, store_results, update_run_status

logger = logging.getLogger(__name__)


def execute_eval_run(run_id: str) -> None:
    """Execute an eval run. Called as an rq job.

    Loads the eval file, creates an OllamaModel with the orchestrator's
    OLLAMA_HOST, runs the eval, and stores results in the database.

    Retries up to 3 times with exponential backoff on transient failures.
    """
    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            _do_execute(run_id)
            return
        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(
                    "Attempt %d/%d failed for run %s: %s. Retrying in %ds...",
                    attempt + 1, max_retries + 1, run_id, e, wait,
                )
                time.sleep(wait)
            else:
                logger.error("All retries exhausted for run %s: %s", run_id, e)
                update_run_status(run_id, "failed", error=str(e))
                raise


def _do_execute(run_id: str) -> None:
    """Inner execution logic."""
    from aeval.adapters.ollama import OllamaModel
    from aeval.core.eval import load_eval_file

    run = get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    update_run_status(run_id, "running")

    # chdir to /app so relative paths like "datasets/factuality-test.jsonl" resolve
    # against the mounted volumes. Safe because rq workers are single-threaded.
    os.chdir("/app")

    ollama_host = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")

    # Load eval file by looking up the eval definition's file_path
    from orchestrator.db.connection import get_cursor
    with get_cursor() as cur:
        cur.execute(
            "SELECT file_path, name, threshold FROM eval_definitions WHERE id = %s",
            (run["eval_id"],),
        )
        eval_def_row = cur.fetchone()

    if not eval_def_row:
        raise ValueError(f"Eval definition {run['eval_id']} not found")

    eval_file = eval_def_row["file_path"]

    # Load the eval definitions from the file
    definitions = load_eval_file(eval_file)
    target_name = eval_def_row["name"]
    definition = None
    for d in definitions:
        if d.name == target_name:
            definition = d
            break

    if definition is None:
        raise ValueError(
            f"Eval '{target_name}' not found in file {eval_file}"
        )

    # Override threshold from run if set
    if run["threshold"] is not None:
        definition.threshold = run["threshold"]

    # Create model with explicit host
    model = OllamaModel(
        model_name=run["model_name"],
        host=ollama_host,
    )

    # Run the eval
    result = definition.run(model)

    # Store per-task results
    task_dicts = [
        {
            "task_id": tr.task_id,
            "score": tr.score,
            "passed": tr.passed,
            "prediction": tr.prediction,
            "reference": tr.reference,
            "latency_ms": tr.latency_ms,
            "tokens_used": tr.tokens_used,
            "metadata": tr.metadata,
        }
        for tr in result.task_results
    ]
    store_results(run_id, task_dicts)

    # Update run with final results
    update_run_status(
        run_id,
        "completed",
        score=result.score,
        ci_lower=result.ci.lower if result.ci else None,
        ci_upper=result.ci.upper if result.ci else None,
        ci_level=result.ci.level if result.ci else None,
        num_tasks=result.num_tasks,
        passed=result.passed,
        metadata=result.metadata,
    )

    logger.info(
        "Run %s completed: score=%.3f, tasks=%d, passed=%s",
        run_id, result.score, result.num_tasks, result.passed,
    )
