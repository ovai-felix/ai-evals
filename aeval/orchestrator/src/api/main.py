"""FastAPI application for the aeval orchestrator."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.api.routes import router
from orchestrator.api.health_routes import health_router
from orchestrator.db.connection import close_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and clean up resources."""
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="aeval orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(health_router)
