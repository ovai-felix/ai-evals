"""Job queue management for eval runs."""

from __future__ import annotations

import os
from typing import Any

import redis
from rq import Queue

from orchestrator.db.evals_repo import get_or_create_eval
from orchestrator.db.models_repo import get_or_create_model
from orchestrator.db.runs_repo import create_run
from orchestrator.engine.executor import execute_eval_run


def get_redis_conn() -> redis.Redis:
    """Get a Redis connection from the environment."""
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url)


def get_queue() -> Queue:
    """Get the rq job queue."""
    return Queue("aeval", connection=get_redis_conn())


def enqueue_run(
    eval_name: str,
    eval_file: str,
    model_name: str,
    threshold: float | None = None,
    eval_tags: list[str] | None = None,
    eval_description: str = "",
    model_family: str = "",
    model_param_size: str = "",
    model_quant: str = "",
    model_multimodal: bool = False,
    model_digest: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create DB records and enqueue an eval run job.

    Returns the created run record (with UUID id).
    """
    # Upsert eval definition
    eval_def = get_or_create_eval(
        name=eval_name,
        file_path=eval_file,
        tags=eval_tags,
        threshold=threshold,
        description=eval_description,
    )

    # Upsert model
    model = get_or_create_model(
        name=model_name,
        family=model_family,
        param_size=model_param_size,
        quant=model_quant,
        multimodal=model_multimodal,
        digest=model_digest,
    )

    # Create run record
    run = create_run(
        eval_id=eval_def["id"],
        model_id=model["id"],
        threshold=threshold,
        metadata=metadata,
    )

    # Enqueue the job
    q = get_queue()
    q.enqueue(
        execute_eval_run,
        str(run["id"]),
        job_id=str(run["id"]),
        job_timeout="30m",
    )

    return run
