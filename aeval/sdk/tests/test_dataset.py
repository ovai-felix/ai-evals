"""Tests for Dataset loading."""

import json
import tempfile
from pathlib import Path

import pytest

from aeval.core.dataset import Dataset


def test_from_list():
    data = [
        {"prompt": "What is 2+2?", "reference": "4"},
        {"prompt": "Capital of France?", "reference": "Paris"},
    ]
    ds = Dataset.from_list(data)
    assert len(ds) == 2
    assert ds.prompts == ["What is 2+2?", "Capital of France?"]
    assert ds.references == ["4", "Paris"]


def test_from_list_missing_references():
    data = [{"prompt": "Hello"}, {"prompt": "World"}]
    ds = Dataset.from_list(data)
    assert len(ds) == 2
    assert ds.references == []


def test_from_jsonl(tmp_path):
    path = tmp_path / "test.jsonl"
    lines = [
        json.dumps({"prompt": "Q1", "reference": "A1"}),
        json.dumps({"prompt": "Q2", "reference": "A2"}),
    ]
    path.write_text("\n".join(lines))

    ds = Dataset.from_jsonl(path)
    assert len(ds) == 2
    assert ds.prompts == ["Q1", "Q2"]
    assert ds.references == ["A1", "A2"]
    assert ds.name == "test"


def test_from_json(tmp_path):
    path = tmp_path / "test.json"
    data = [
        {"prompt": "Q1", "reference": "A1"},
        {"prompt": "Q2", "reference": "A2"},
    ]
    path.write_text(json.dumps(data))

    ds = Dataset.from_json(path)
    assert len(ds) == 2
    assert ds.prompts == ["Q1", "Q2"]


def test_from_json_invalid_format(tmp_path):
    path = tmp_path / "test.json"
    path.write_text(json.dumps({"not": "a list"}))

    with pytest.raises(ValueError, match="Expected JSON array"):
        Dataset.from_json(path)


def test_from_csv(tmp_path):
    path = tmp_path / "test.csv"
    path.write_text("prompt,reference\nQ1,A1\nQ2,A2\n")

    ds = Dataset.from_csv(path)
    assert len(ds) == 2
    assert ds.prompts == ["Q1", "Q2"]
    assert ds.references == ["A1", "A2"]


def test_load_jsonl(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "my_data.jsonl"
    path.write_text(json.dumps({"prompt": "Q", "reference": "A"}) + "\n")

    ds = Dataset.load(str(path))
    assert len(ds) == 1


def test_load_not_found():
    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        Dataset.load("nonexistent_dataset_xyz")


def test_getitem():
    ds = Dataset(prompts=["Q1", "Q2"], references=["A1", "A2"])
    item = ds[0]
    assert item == {"prompt": "Q1", "reference": "A1"}
