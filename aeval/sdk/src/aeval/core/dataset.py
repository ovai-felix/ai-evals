"""Dataset loading for aeval."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Dataset:
    """A collection of eval tasks with prompts and optional references."""

    prompts: list[str]
    references: list[str] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    metadata: list[dict[str, Any]] = field(default_factory=list)
    name: str = ""

    def __len__(self) -> int:
        return len(self.prompts)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        item: dict[str, Any] = {"prompt": self.prompts[idx]}
        if self.references:
            item["reference"] = self.references[idx]
        if self.answers:
            item["answer"] = self.answers[idx]
        if self.images:
            item["image"] = self.images[idx]
        if self.labels:
            item["label"] = self.labels[idx]
        if self.metadata:
            item["metadata"] = self.metadata[idx]
        return item

    @classmethod
    def from_list(
        cls,
        data: list[dict[str, Any]],
        *,
        prompt_key: str = "prompt",
        reference_key: str = "reference",
        answer_key: str = "answer",
        image_key: str = "image",
        label_key: str = "label",
        name: str = "",
    ) -> Dataset:
        """Create a Dataset from a list of dicts."""
        prompts = [item[prompt_key] for item in data]
        references = [item[reference_key] for item in data if reference_key in item]
        answers = [item[answer_key] for item in data if answer_key in item]
        images = [item[image_key] for item in data if image_key in item]
        labels = [item[label_key] for item in data if label_key in item]
        return cls(
            prompts=prompts,
            references=references if len(references) == len(prompts) else [],
            answers=answers if len(answers) == len(prompts) else [],
            images=images if len(images) == len(prompts) else [],
            labels=labels if len(labels) == len(prompts) else [],
            name=name,
        )

    @classmethod
    def from_jsonl(cls, path: str | Path, **kwargs) -> Dataset:
        """Load dataset from a JSONL file (one JSON object per line)."""
        path = Path(path)
        data = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
        return cls.from_list(data, name=kwargs.pop("name", path.stem), **kwargs)

    @classmethod
    def from_json(cls, path: str | Path, **kwargs) -> Dataset:
        """Load dataset from a JSON file (array of objects)."""
        path = Path(path)
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array, got {type(data).__name__}")
        return cls.from_list(data, name=kwargs.pop("name", path.stem), **kwargs)

    @classmethod
    def from_csv(cls, path: str | Path, **kwargs) -> Dataset:
        """Load dataset from a CSV file."""
        path = Path(path)
        data = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))
        return cls.from_list(data, name=kwargs.pop("name", path.stem), **kwargs)

    @classmethod
    def load(cls, name_or_path: str, **kwargs) -> Dataset:
        """Load a dataset by name or file path.

        Tries to resolve as a file path first (supports .jsonl, .json, .csv).
        """
        path = Path(name_or_path)
        if path.exists():
            return cls._load_by_extension(path, **kwargs)

        # Try common extensions
        for ext in (".jsonl", ".json", ".csv"):
            candidate = path.with_suffix(ext)
            if candidate.exists():
                return cls._load_by_extension(candidate, **kwargs)

        raise FileNotFoundError(
            f"Dataset not found: {name_or_path}. "
            f"Provide a path to a .jsonl, .json, or .csv file."
        )

    @classmethod
    def _load_by_extension(cls, path: Path, **kwargs) -> Dataset:
        ext = path.suffix.lower()
        if ext == ".jsonl":
            return cls.from_jsonl(path, **kwargs)
        elif ext == ".json":
            return cls.from_json(path, **kwargs)
        elif ext == ".csv":
            return cls.from_csv(path, **kwargs)
        else:
            raise ValueError(f"Unsupported dataset format: {ext}")
