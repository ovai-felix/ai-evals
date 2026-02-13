"""Suite definitions — named groups of evals to run together."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SuiteDefinition:
    """A named collection of evals."""

    name: str
    description: str = ""
    evals: list[str] = field(default_factory=list)
    timeout: str = "30m"


def load_suites(path: str | Path | None = None) -> dict[str, SuiteDefinition]:
    """Load all suites from a YAML file.

    Search order:
        1. Provided path
        2. evals/suites.yaml in current directory
        3. AEVAL_SUITES_FILE environment variable
    """
    resolved = _find_suites_file(path)
    if resolved is None or not resolved.exists():
        return {}

    with open(resolved) as f:
        data = yaml.safe_load(f) or {}

    raw_suites = data.get("suites", {})
    suites: dict[str, SuiteDefinition] = {}

    for name, value in raw_suites.items():
        if isinstance(value, list):
            suites[name] = SuiteDefinition(name=name, evals=value)
        elif isinstance(value, dict):
            suites[name] = SuiteDefinition(
                name=name,
                description=value.get("description", ""),
                evals=value.get("evals", []),
                timeout=value.get("timeout", "30m"),
            )
    return suites


def get_suite(name: str, path: str | Path | None = None) -> SuiteDefinition | None:
    """Get a single suite by name."""
    return load_suites(path).get(name)


def list_suites(path: str | Path | None = None) -> list[SuiteDefinition]:
    """List all available suites."""
    return list(load_suites(path).values())


def _find_suites_file(path: str | Path | None = None) -> Path | None:
    """Resolve the suites YAML file location."""
    if path is not None:
        return Path(path)

    # Check evals/suites.yaml in cwd
    cwd_path = Path.cwd() / "evals" / "suites.yaml"
    if cwd_path.exists():
        return cwd_path

    # Check environment variable
    env_path = os.environ.get("AEVAL_SUITES_FILE")
    if env_path:
        return Path(env_path)

    return None
