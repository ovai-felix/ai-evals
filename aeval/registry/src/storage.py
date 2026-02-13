"""File-based storage layer — reads from registry-data/ and evals/suites.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml


def _registry_data_dir() -> Path:
    """Locate the registry-data directory."""
    # Inside Docker, mounted at /app/registry-data
    docker_path = Path("/app/registry-data")
    if docker_path.exists():
        return docker_path

    # Local development fallback
    local_path = Path.cwd() / "registry-data"
    if local_path.exists():
        return local_path

    return docker_path  # Return docker path even if missing


def _suites_file() -> Path:
    """Locate the suites.yaml file."""
    docker_path = Path("/app/evals/suites.yaml")
    if docker_path.exists():
        return docker_path

    local_path = Path.cwd() / "evals" / "suites.yaml"
    if local_path.exists():
        return local_path

    return docker_path


def list_evals() -> list[dict]:
    """List all evals from registry-data/."""
    data_dir = _registry_data_dir()
    if not data_dir.exists():
        return []

    evals = []
    for meta_file in sorted(data_dir.rglob("meta.yaml")):
        try:
            with open(meta_file) as f:
                meta = yaml.safe_load(f) or {}
            # Count dataset lines
            dataset_file = meta_file.parent / "dataset.jsonl"
            dataset_size = 0
            if dataset_file.exists():
                with open(dataset_file) as f:
                    dataset_size = sum(1 for line in f if line.strip())
            meta["dataset_size"] = dataset_size
            meta["dataset"] = str(dataset_file) if dataset_file.exists() else ""

            # Read code preview
            eval_file = meta_file.parent / "eval.py"
            code_preview = ""
            if eval_file.exists():
                code_preview = eval_file.read_text()[:500]
            meta["code_preview"] = code_preview

            evals.append(meta)
        except Exception:
            continue
    return evals


def get_eval(name: str) -> dict | None:
    """Get a single eval by name."""
    for e in list_evals():
        if e.get("name") == name:
            return e
    return None


def search_evals(query: str) -> list[dict]:
    """Search evals by name, tag, category, or description."""
    query_lower = query.lower()
    results = []
    for e in list_evals():
        name = e.get("name", "").lower()
        desc = e.get("description", "").lower()
        tags = [t.lower() for t in e.get("tags", [])]
        category = e.get("category", "").lower()

        if (
            query_lower in name
            or query_lower in desc
            or query_lower in category
            or any(query_lower in t for t in tags)
        ):
            results.append(e)
    return results


def list_suites() -> list[dict]:
    """Load suites from suites.yaml."""
    suites_path = _suites_file()
    if not suites_path.exists():
        return []

    try:
        with open(suites_path) as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return []

    raw = data.get("suites", {})
    suites = []
    for name, value in raw.items():
        if isinstance(value, list):
            suites.append({"name": name, "evals": value, "description": "", "timeout": "30m"})
        elif isinstance(value, dict):
            suites.append({
                "name": name,
                "description": value.get("description", ""),
                "evals": value.get("evals", []),
                "timeout": value.get("timeout", "30m"),
            })
    return suites
