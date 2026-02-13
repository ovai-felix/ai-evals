"""Configuration loading for aeval."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    host: str = "http://localhost:11434"
    timeout: int = 120
    keep_alive: str = "5m"


class IntelligenceConfig(BaseModel):
    generator_model: str = "ollama:gpt-oss:20b"
    calibration_model: str = "ollama:gemma3"
    schedule_saturation_check: str = "weekly"
    schedule_coverage_check: str = "weekly"


class AevalConfig(BaseModel):
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    judge_model: str = "ollama:gpt-oss:20b"
    datasets_dir: str = "./datasets"
    evals_dir: str = "./evals"
    orchestrator_url: str = "http://localhost:8081"
    registry_url: str = "http://localhost:8082"
    intelligence: IntelligenceConfig = Field(default_factory=IntelligenceConfig)

    @classmethod
    def load(cls, path: Path | None = None) -> AevalConfig:
        """Load config from aeval.yaml, falling back to defaults."""
        if path is None:
            path = _find_config()
        if path and path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return cls.model_validate(data)
        return cls()


def _find_config() -> Path | None:
    """Search for aeval.yaml in cwd and parent directories."""
    # Check environment variable first
    env_path = os.environ.get("AEVAL_CONFIG")
    if env_path:
        return Path(env_path)

    cwd = Path.cwd()
    for directory in [cwd, *cwd.parents]:
        candidate = directory / "aeval.yaml"
        if candidate.exists():
            return candidate
    return None
