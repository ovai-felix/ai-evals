"""Repository for the models table."""

from __future__ import annotations

from typing import Any

from orchestrator.db.connection import get_cursor


def get_or_create_model(
    name: str,
    family: str = "",
    param_size: str = "",
    quant: str = "",
    multimodal: bool = False,
    digest: str = "",
) -> dict[str, Any]:
    """Insert a model if it doesn't exist, or update last_seen if it does."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO models (name, family, param_size, quant, multimodal, digest)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE
                SET family = EXCLUDED.family,
                    param_size = EXCLUDED.param_size,
                    quant = EXCLUDED.quant,
                    multimodal = EXCLUDED.multimodal,
                    digest = EXCLUDED.digest,
                    last_seen = NOW()
            RETURNING *
            """,
            (name, family, param_size, quant, multimodal, digest),
        )
        return dict(cur.fetchone())


def list_models() -> list[dict[str, Any]]:
    """List all known models."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM models ORDER BY last_seen DESC")
        return [dict(row) for row in cur.fetchall()]
