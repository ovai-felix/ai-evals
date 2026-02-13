"""Database connection pool management."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor


_pool: pool.SimpleConnectionPool | None = None


def get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://aeval:aeval_dev@localhost:5432/aeval"
    )


def init_pool(minconn: int = 2, maxconn: int = 10) -> None:
    """Initialize the connection pool."""
    global _pool
    if _pool is not None:
        return
    _pool = pool.SimpleConnectionPool(minconn, maxconn, dsn=get_database_url())


def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def get_conn() -> Generator:
    """Get a connection from the pool with automatic return."""
    if _pool is None:
        init_pool()
    conn = _pool.getconn()  # type: ignore[union-attr]
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)  # type: ignore[union-attr]


@contextmanager
def get_cursor() -> Generator:
    """Get a dict cursor from the pool with automatic cleanup."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
