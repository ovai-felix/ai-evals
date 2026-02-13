# Eval Authoring Guide

How to write custom evaluations for aeval.

## The Basics

An eval is a Python function decorated with `@Eval` that takes a `model` argument and returns scored results.

```python
from aeval.core.eval import Eval
from aeval.core.dataset import Dataset
from aeval.core.scorer import Scorer
from aeval.core.result import TaskResult, EvalResult

@Eval(name="my-eval", threshold=0.7, tags=["custom"], description="My custom evaluation")
def my_eval(model):
    # 1. Load your data
    # 2. Get model predictions
    # 3. Score them
    # 4. Return results
    ...
```

## Return Types

Evals can return results in four formats. The SDK normalizes all of them.

### Option 1: List of TaskResults (recommended)

```python
@Eval(name="qa-eval", threshold=0.8)
def qa_eval(model):
    dataset = Dataset.from_jsonl("datasets/qa.jsonl")
    responses = model.generate(dataset.prompts)

    return [
        TaskResult(
            task_id=f"task-{i}",
            score=1.0 if pred.text.strip().lower() == ref.lower() else 0.0,
            passed=pred.text.strip().lower() == ref.lower(),
            prediction=pred.text,
            reference=ref,
            latency_ms=pred.latency_ms,
            tokens_used=pred.tokens_used,
        )
        for i, (pred, ref) in enumerate(zip(responses, dataset.references))
    ]
```

### Option 2: Use a built-in scorer

```python
@Eval(name="factuality-eval", threshold=0.7)
def factuality_eval(model):
    dataset = Dataset.from_jsonl("datasets/facts.jsonl")
    responses = model.generate(dataset.prompts)
    predictions = [r.text for r in responses]

    # Returns list[TaskResult] automatically
    return Scorer.exact_match(predictions, dataset.references)
```

### Option 3: List of scores (floats)

```python
@Eval(name="simple-eval")
def simple_eval(model):
    prompts = ["What is 1+1?", "What is 2+2?", "What is 3+3?"]
    expected = ["2", "4", "6"]
    responses = model.generate(prompts)

    return [
        1.0 if r.text.strip() == e else 0.0
        for r, e in zip(responses, expected)
    ]
```

### Option 4: Single score

```python
@Eval(name="overall-quality")
def overall_quality(model):
    responses = model.generate(["Write a haiku about programming."])
    # Return a single aggregate score
    return 0.85
```

### Option 5: Full EvalResult

```python
@Eval(name="detailed-eval")
def detailed_eval(model):
    # Full control over the result
    return EvalResult(
        eval_name="detailed-eval",
        model_name=model.name,
        score=0.85,
        num_tasks=10,
        task_results=[...],
        metadata={"version": "2.0"},
    )
```

## Dataset Loading

The `Dataset` class loads data from JSONL, JSON, or CSV files.

### JSONL (recommended)

```jsonl
{"prompt": "What is the capital of France?", "reference": "Paris"}
{"prompt": "What is 2+2?", "reference": "4"}
```

```python
dataset = Dataset.from_jsonl("datasets/my-data.jsonl")
print(dataset.prompts)     # ["What is the capital of France?", "What is 2+2?"]
print(dataset.references)  # ["Paris", "4"]
```

### JSON array

```json
[
  {"prompt": "Question 1", "reference": "Answer 1"},
  {"prompt": "Question 2", "reference": "Answer 2"}
]
```

```python
dataset = Dataset.from_json("datasets/my-data.json")
```

### CSV

```csv
prompt,reference
"What is the capital of France?","Paris"
"What is 2+2?","4"
```

```python
dataset = Dataset.from_csv("datasets/my-data.csv")
```

### Custom keys

```python
dataset = Dataset.from_jsonl(
    "data.jsonl",
    prompt_key="question",
    reference_key="answer",
)
```

### In-memory

```python
dataset = Dataset.from_list([
    {"prompt": "Q1", "reference": "A1"},
    {"prompt": "Q2", "reference": "A2"},
])
```

## Scorers

### Exact Match

Normalized string comparison. Strips whitespace, lowercases, removes punctuation.

```python
results = Scorer.exact_match(predictions, references, normalize=True)
```

### Multiple Choice

Extracts A/B/C/D from model output and compares to correct answer.

```python
results = Scorer.multiple_choice(predictions, answers)
# predictions: ["The answer is B", "I think it's (C)"]
# answers: ["B", "C"]
```

### LLM Judge

Uses another Ollama model to rate quality on a rubric.

```python
results = Scorer.llm_judge(
    predictions,
    references,
    judge_model="ollama:gpt-oss:20b",
    rubric="Rate accuracy and completeness from 1-5.",
    scale=5,
)
```

### Safety Refusal

Checks if the model correctly refused unsafe prompts.

```python
results = Scorer.safety_refusal(
    predictions,
    expected_refusals=[True, True, False, True],
)
```

## Model Interface

The `model` argument passed to your eval function has these methods:

```python
# Chat completion (recommended)
responses = model.generate(
    prompts=["Hello, world!"],
    system="You are a helpful assistant.",
    temperature=0.0,
    max_tokens=256,
)

# Raw completion
responses = model.complete(
    prompts=["Once upon a time"],
    temperature=0.7,
)

# Each response has:
response.text        # Generated text
response.tokens_used # Token count
response.latency_ms  # Inference time
response.model       # Model name
response.metadata    # Extra info
```

## Publishing to the Registry

Package your eval as a directory in `registry-data/`:

```
registry-data/my-eval/
├── meta.yaml       # Metadata
├── dataset.jsonl   # Evaluation data
└── eval.py         # Eval definition
```

**meta.yaml:**
```yaml
name: my-eval
version: 1.0.0
description: My custom evaluation
category: reasoning
tags: [custom, reasoning]
threshold: 0.7
dataset: dataset.jsonl
```

Then it's automatically discoverable:
```bash
aeval registry search "my-eval"
```

## Running Evals

```bash
# Single eval
aeval run my-eval -m ollama:llama3

# From file path
aeval run ./evals/my_eval.py -m ollama:gemma3:4b

# Suite
aeval run --suite smoke -m ollama:llama3

# Local-only (skip orchestrator)
aeval run my-eval -m ollama:llama3 --local

# JSON output
aeval run my-eval -m ollama:llama3 --output json
```

## Tips

1. **Start with exact_match** for factual Q&A. It's fast and deterministic.
2. **Use llm_judge** when exact matching is too strict (open-ended generation, summaries).
3. **Include 20+ tasks** per eval for meaningful confidence intervals.
4. **Set thresholds** based on baseline model performance, not aspirational targets.
5. **Tag your evals** for organization: `tags=["safety", "v2", "adversarial"]`.
6. **Use JSONL** for datasets — easy to version, diff, and extend.
