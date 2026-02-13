"""Contamination detection — compare eval datasets against training data manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ContaminationResult:
    """Result of a contamination check for one eval dataset."""

    eval_name: str
    dataset_path: str
    total_items: int = 0
    contaminated_items: int = 0
    contamination_rate: float = 0.0
    flagged: bool = False
    matched_hashes: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.flagged


@dataclass
class ContaminationReport:
    """Aggregate contamination report across all eval datasets."""

    results: list[ContaminationResult] = field(default_factory=list)
    manifest_path: str = ""
    manifest_entries: int = 0

    @property
    def any_contaminated(self) -> bool:
        return any(r.flagged for r in self.results)

    @property
    def clean_count(self) -> int:
        return sum(1 for r in self.results if r.clean)

    @property
    def contaminated_count(self) -> int:
        return sum(1 for r in self.results if r.flagged)


def load_training_manifest(manifest_path: str | Path) -> set[str]:
    """Load a training data manifest file.

    Manifest is a JSON file containing a list of entries, each with
    a "hash" or "content_hash" key, or a flat list of hash strings.

    Supported formats:
      - {"files": [{"path": "...", "hash": "abc123"}, ...]}
      - {"hashes": ["abc123", ...]}
      - ["abc123", ...]
    """
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Training manifest not found: {manifest_path}")

    with open(path) as f:
        data = json.load(f)

    hashes: set[str] = set()

    if isinstance(data, list):
        # Flat list of hashes
        for item in data:
            if isinstance(item, str):
                hashes.add(item)
            elif isinstance(item, dict):
                h = item.get("hash") or item.get("content_hash") or item.get("sha256")
                if h:
                    hashes.add(h)
    elif isinstance(data, dict):
        # Object with files/hashes key
        for key in ("files", "entries", "data"):
            if key in data:
                for item in data[key]:
                    if isinstance(item, str):
                        hashes.add(item)
                    elif isinstance(item, dict):
                        h = item.get("hash") or item.get("content_hash") or item.get("sha256")
                        if h:
                            hashes.add(h)
        if "hashes" in data:
            for h in data["hashes"]:
                if isinstance(h, str):
                    hashes.add(h)

    return hashes


def hash_text(text: str) -> str:
    """Compute a SHA-256 hash of normalized text."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def check_dataset_contamination(
    dataset_path: str | Path,
    training_hashes: set[str],
    eval_name: str = "",
    threshold: float = 0.05,
) -> ContaminationResult:
    """Check a single eval dataset for contamination against training hashes.

    Args:
        dataset_path: Path to a JSONL dataset file.
        training_hashes: Set of content hashes from training data.
        eval_name: Name of the eval for reporting.
        threshold: Contamination rate above which the eval is flagged.

    Returns:
        ContaminationResult with per-item and aggregate contamination info.
    """
    path = Path(dataset_path)
    if not path.exists():
        return ContaminationResult(
            eval_name=eval_name or path.stem,
            dataset_path=str(path),
        )

    items: list[dict[str, Any]] = []

    if path.suffix == ".jsonl":
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
    elif path.suffix == ".json":
        with open(path) as f:
            data = json.load(f)
            if isinstance(data, list):
                items = data

    if not items:
        return ContaminationResult(
            eval_name=eval_name or path.stem,
            dataset_path=str(path),
        )

    matched: list[str] = []
    for item in items:
        # Hash the prompt (primary check)
        prompt = item.get("prompt", "")
        if prompt:
            h = hash_text(prompt)
            if h in training_hashes:
                matched.append(h)
                continue

        # Hash prompt + reference combination
        reference = item.get("reference", "")
        if prompt and reference:
            combined = f"{prompt}|||{reference}"
            h = hash_text(combined)
            if h in training_hashes:
                matched.append(h)

    total = len(items)
    contaminated = len(matched)
    rate = contaminated / total if total > 0 else 0.0

    return ContaminationResult(
        eval_name=eval_name or path.stem,
        dataset_path=str(path),
        total_items=total,
        contaminated_items=contaminated,
        contamination_rate=rate,
        flagged=rate > threshold,
        matched_hashes=matched,
    )


def check_all_datasets(
    manifest_path: str | Path,
    dataset_paths: list[str | Path],
    eval_names: list[str] | None = None,
    threshold: float = 0.05,
) -> ContaminationReport:
    """Check all eval datasets against a training manifest.

    Args:
        manifest_path: Path to the training data manifest.
        dataset_paths: List of eval dataset file paths.
        eval_names: Optional eval names corresponding to each dataset.
        threshold: Contamination rate threshold for flagging.

    Returns:
        ContaminationReport with per-dataset results.
    """
    training_hashes = load_training_manifest(manifest_path)

    results = []
    for i, ds_path in enumerate(dataset_paths):
        name = eval_names[i] if eval_names and i < len(eval_names) else ""
        result = check_dataset_contamination(
            dataset_path=ds_path,
            training_hashes=training_hashes,
            eval_name=name,
            threshold=threshold,
        )
        results.append(result)

    return ContaminationReport(
        results=results,
        manifest_path=str(manifest_path),
        manifest_entries=len(training_hashes),
    )
