"""FastAPI application for the eval registry service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from registry.src.routes import router

app = FastAPI(
    title="aeval registry",
    version="0.1.0",
    description="Eval registry — browse, search, and manage shared evals.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
