"""Repository for the eval_definitions table."""

from __future__ import annotations

import json
from typing import Any

from orchestrator.db.connection import get_cursor


def get_or_create_eval(
    name: str,
    file_path: str = "",
    tags: list[str] | None = None,
    threshold: float | None = None,
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert an eval definition if it doesn't exist, or return existing."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO eval_definitions (name, file_path, tags, threshold, description, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE
                SET file_path = EXCLUDED.file_path,
                    tags = EXCLUDED.tags,
                    threshold = EXCLUDED.threshold,
                    description = EXCLUDED.description,
                    metadata = EXCLUDED.metadata
            RETURNING *
            """,
            (
                name,
                file_path,
                tags or [],
                threshold,
                description,
                json.dumps(metadata or {}),
            ),
        )
        return dict(cur.fetchone())
