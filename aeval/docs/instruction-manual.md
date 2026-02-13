# aeval Instruction Manual

Complete reference for the aeval AI Evaluation Pipeline — Phases 1 through 6.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation & Setup](#2-installation--setup)
3. [Phase 1 — SDK, CLI & Ollama Adapter](#3-phase-1--sdk-cli--ollama-adapter)
4. [Phase 2 — Docker Stack, Orchestrator & Persistence](#4-phase-2--docker-stack-orchestrator--persistence)
5. [Phase 3 — Web Dashboard](#5-phase-3--web-dashboard)
6. [Phase 4 — Eval Registry](#6-phase-4--eval-registry)
7. [Phase 5 — Adaptive Intelligence](#7-phase-5--adaptive-intelligence)
8. [Phase 6 — CI/CD & Polish](#8-phase-6--cicd--polish)
9. [Configuration Reference](#9-configuration-reference)
10. [API Reference](#10-api-reference)
11. [Database Schema](#11-database-schema)
12. [Architecture](#12-architecture)

---

## 1. Overview

aeval is a local-first AI model evaluation pipeline. It lets you:

- Write evals as Python functions (like pytest for models)
- Run evals against any Ollama model
- Get scores with confidence intervals and significance testing
- Compare models head-to-head with statistical rigor
- Persist results in TimescaleDB, visualize in a web dashboard
- Monitor eval health (saturation, discrimination, coverage gaps)
- Generate new evals with LLM-powered intelligence
- Integrate into CI/CD with exit codes and PR comments

All data stays on your machine. No telemetry, no cloud sync, no external API calls.

### Project Structure

```
aeval/
├── sdk/                    # Python SDK + CLI (pip install -e ./sdk)
├── orchestrator/           # FastAPI orchestrator + RQ worker
├── registry/               # Eval registry microservice
├── dashboard/              # Next.js web dashboard
├── evals/                  # Eval definitions (.py files)
│   ├── core/               # 5 built-in core evals
│   └── suites.yaml         # Named eval groups
├── datasets/               # Eval datasets (.jsonl files)
├── registry-data/          # Packaged eval metadata
├── docs/                   # Documentation
├── docker-compose.yml      # Full stack orchestration
├── aeval.yaml              # SDK configuration
├── .env.example            # Environment variable template
└── .github/workflows/      # CI/CD workflow
```

---

## 2. Installation & Setup

### Prerequisites

- Python 3.11+
- Ollama installed with at least one model pulled
- Docker & Docker Compose (for the full stack)
- Node.js 18+ (only if developing the dashboard)

### Install the SDK

```bash
cd aeval
python3 -m venv .venv
source .venv/bin/activate    
pip install -e ./sdk
```

Verify:

```bash
aeval --version
# aeval, version 0.1.0
```

### Initialize a project

```bash
aeval init
```

This creates `aeval.yaml` with your Ollama host, plus `evals/` and `datasets/` directories.

### Verify Ollama connectivity

```bash
aeval status
```

Checks Ollama reachability and lists available models.

```bash
aeval models
```

Lists all Ollama models in a table with family, parameter size, quantization, and multimodal flag.

### Start the full Docker stack

```bash
docker compose up -d
```

This starts 5 services:

| Service | Port | Purpose |
|---------|------|---------|
| `db` | 5432 | TimescaleDB (PostgreSQL 16 + time-series) |
| `redis` | 6379 | Redis 7 (job queue for async eval runs) |
| `orchestrator` | 8081 | FastAPI API + RQ worker |
| `registry` | 8082 | Eval registry microservice |
| `dashboard` | 3000 | Next.js web dashboard |

Verify all services are healthy:

```bash
aeval status
curl http://localhost:8081/api/v1/health
```

---

## 3. Phase 1 — SDK, CLI & Ollama Adapter

Phase 1 delivers the core evaluation framework: write evals in Python, run them against Ollama models, get statistically rigorous results.

### 3.1 Writing an Eval

An eval is a Python function decorated with `@Eval`:

```python
from aeval.core.eval import Eval
from aeval.core.dataset import Dataset
from aeval.core.scorer import Scorer
from aeval.core.result import TaskResult

@Eval(
    name="my-eval",
    threshold=0.7,
    tags=["custom", "factuality"],
    description="Tests factual knowledge accuracy",
)
def my_eval(model):
    dataset = Dataset.from_jsonl("datasets/my-data.jsonl")
    responses = model.generate(dataset.prompts)
    predictions = [r.text for r in responses]
    return Scorer.exact_match(predictions, dataset.references)
```

#### Decorator Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | required | Unique eval identifier |
| `threshold` | float | None | Pass/fail score threshold |
| `tags` | list[str] | [] | Labels for filtering/organization |
| `description` | str | "" | Human-readable description |
| `**metadata` | dict | {} | Arbitrary metadata |

#### Supported Return Types

Your eval function can return any of these — the SDK normalizes all of them:

**1. `list[TaskResult]`** (recommended — per-task granularity):
```python
return [
    TaskResult(task_id="q1", score=1.0, passed=True, prediction="Paris", reference="Paris"),
    TaskResult(task_id="q2", score=0.0, passed=False, prediction="Berlin", reference="London"),
]
```

**2. `list[float]`** (just scores):
```python
return [1.0, 0.0, 0.5, 1.0]
```

**3. `float`** (single aggregate score):
```python
return 0.85
```

**4. `EvalResult`** (full control):
```python
from aeval.core.result import EvalResult, ConfidenceInterval
return EvalResult(
    eval_name="my-eval",
    model_name=model.name,
    score=0.85,
    ci=ConfidenceInterval(0.78, 0.92),
    num_tasks=50,
    passed=True,
    threshold=0.7,
    task_results=[...],
)
```

### 3.2 Loading Datasets

The `Dataset` class supports JSONL, JSON, and CSV:

```python
# JSONL (one JSON object per line — recommended)
dataset = Dataset.from_jsonl("datasets/qa.jsonl")

# JSON (array of objects)
dataset = Dataset.from_json("datasets/qa.json")

# CSV
dataset = Dataset.from_csv("datasets/qa.csv")

# In-memory
dataset = Dataset.from_list([
    {"prompt": "What is 2+2?", "reference": "4"},
    {"prompt": "Capital of France?", "reference": "Paris"},
])

# Auto-detect format
dataset = Dataset.load("datasets/qa")
```

**Custom field names:**
```python
dataset = Dataset.from_jsonl("data.jsonl", prompt_key="question", reference_key="answer")
```

**Dataset attributes:**
- `dataset.prompts` — list of prompt strings
- `dataset.references` — list of reference answers
- `dataset.answers` — list of answer keys (for multiple choice)
- `dataset.images` — list of image paths (for multimodal)
- `dataset.labels` — list of labels
- `len(dataset)` — number of items
- `dataset[i]` — single item as dict

### 3.3 Scorers

The `Scorer` facade provides four built-in scoring methods:

#### Exact Match

```python
results = Scorer.exact_match(predictions, references, normalize=True)
```

Compares strings after normalization (lowercase, strip whitespace, remove punctuation). Returns `list[TaskResult]` with score 1.0 (match) or 0.0 (mismatch).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `predictions` | list[str] or list[GenerateResponse] | required | Model outputs |
| `references` | list[str] | required | Correct answers |
| `normalize` | bool | True | Apply text normalization |

#### Multiple Choice

```python
results = Scorer.multiple_choice(predictions, answers)
```

Extracts A/B/C/D letter choices from model output and compares. Handles formats like "The answer is B", "(C)", "B.", etc.

#### LLM Judge

```python
results = Scorer.llm_judge(
    predictions, references,
    judge_model="ollama:gpt-oss:20b",
    rubric="Rate accuracy and completeness from 1-5.",
    scale=5,
)
```

Uses another Ollama model to rate response quality on a configurable rubric.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `judge_model` | str | "ollama:gpt-oss:20b" | Ollama model to use as judge |
| `rubric` | str | "" | Rating rubric/instructions |
| `scale` | int | 5 | Rating scale maximum |

#### Safety Refusal

```python
results = Scorer.safety_refusal(predictions, expected_refusals=[True, True, False])
```

Checks whether the model correctly refused unsafe prompts. Score is 1.0 for correct behavior (refusing when expected, answering when expected).

### 3.4 Model Interface

The `model` argument passed to eval functions is an `OllamaModel` instance:

```python
# Chat completion (recommended — uses /api/chat)
responses = model.generate(
    prompts=["What is 2+2?", "Capital of France?"],
    system="You are a helpful assistant.",
    temperature=0.0,
    max_tokens=256,
)

# Raw completion (uses /api/generate)
responses = model.complete(
    prompts=["Once upon a time"],
    temperature=0.7,
)

# Multimodal (images)
responses = model.generate(
    prompts=["Describe this image."],
    images=[["path/to/image.jpg"]],
)

# Health check
model.health_check()  # → True/False
```

**Response attributes:**
- `response.text` — generated text
- `response.tokens_used` — token count
- `response.latency_ms` — inference time in milliseconds
- `response.model` — model name
- `response.metadata` — extra info (total_duration, load_duration, etc.)

### 3.5 Running Evals

```bash
# Run a single eval
aeval run my-eval -m ollama:llama3

# Run by file path
aeval run ./evals/core/factuality_v1.py -m ollama:gemma3:4b

# Override threshold
aeval run my-eval -m ollama:llama3 --threshold 0.5

# JSON output
aeval run my-eval -m ollama:llama3 --output json

# Force local execution (skip orchestrator)
aeval run my-eval -m ollama:llama3 --local

# Run a suite
aeval run --suite smoke -m ollama:llama3
```

**`aeval run` options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `EVAL_NAME` | argument | — | Eval name or .py file path |
| `-m, --model` | string | required | Model spec (e.g., `ollama:llama3`) |
| `--output` | table\|json | table | Output format |
| `--threshold` | float | — | Override pass/fail threshold |
| `--local` | flag | false | Skip orchestrator, run locally |
| `--suite` | string | — | Run a named suite instead |

**Dual-mode execution:** If the orchestrator is running, `aeval run` submits the job for async execution and returns a run ID. Use `--local` to force local execution. If the orchestrator is unreachable, it falls through to local mode automatically.

**Exit codes:** 0 = pass, 1 = fail (below threshold), 2 = system error.

### 3.6 Comparing Models

```bash
# Compare two models on one eval
aeval compare ollama:llama3 ollama:brain-analyst-ft --eval factuality-v1

# Compare on multiple evals
aeval compare ollama:llama3 ollama:gemma3:4b --eval factuality-v1 --eval reasoning-v1

# Compare on a suite
aeval compare ollama:brain-analyst-ft ollama:llama3 --suite core

# Alignment tax report
aeval compare ollama:brain-analyst-ft ollama:llama3 --suite core --format alignment-tax

# JSON output
aeval compare ollama:llama3 ollama:gemma3:4b --eval reasoning-v1 --output json
```

**`aeval compare` options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `MODELS` | arguments | required | 2+ model specs |
| `--eval, -e` | string (multiple) | — | Eval(s) to run |
| `--suite` | string | — | Use a suite instead of --eval |
| `--output` | table\|json | table | Output format |
| `--format` | default\|alignment-tax | default | Report format |

**Default output:** Table showing each eval's score per model, delta, and statistical significance (Welch's t-test).

**Alignment tax output:** Three sections:
1. **Improvements** — evals where the first model significantly outperforms the second
2. **Degradations** — evals where the first model is significantly worse (the "alignment tax")
3. **Unchanged** — no statistically significant difference

Plus a net assessment with gain/cost ratio.

### 3.7 Statistical Features

All stats are computed automatically when evals return `list[TaskResult]` or `list[float]`.

#### Confidence Intervals

```python
from aeval.stats.significance import confidence_interval

ci = confidence_interval(scores, level=0.95, method="bootstrap", n_bootstrap=10000)
# ci.lower, ci.upper, ci.level, ci.margin
```

Methods: `"bootstrap"` (percentile, seeded for reproducibility) or `"normal"` (z-score approximation).

#### Significance Testing

```python
from aeval.stats.significance import significance_test

result = significance_test(scores_a, scores_b, method="welch", alpha=0.05)
# result = {"p_value": 0.003, "significant": True, "statistic": 3.14, "effect_size": 0.82, "method": "welch"}
```

Methods: `"welch"` (Welch's t-test for unequal variances) or `"permutation"` (10,000 resamples).

#### Effect Size

```python
from aeval.stats.significance import cohens_d

d = cohens_d(scores_a, scores_b)
# Conventions: |d| < 0.2 = small, 0.5 = medium, 0.8 = large
```

#### Discrimination Power

```python
from aeval.stats.discrimination import discrimination_power

disc = discrimination_power({"model_a": [0.9, 0.8], "model_b": [0.5, 0.4]})
# 0.0 to 1.0 — higher means the eval differentiates models better
# > 0.15 = good (active), < 0.08 = poor (saturated)
```

#### Saturation Detection

```python
from aeval.stats.discrimination import detect_saturation

result = detect_saturation(scores_by_model)
# {"saturated": True, "type": "ceiling", "models_at_ceiling": 5, "total_models": 6}
```

Types: `"ceiling"` (90%+ of models score > 0.95), `"floor"` (90%+ score < 0.10), `"noise"` (discrimination < 0.08).

---

## 4. Phase 2 — Docker Stack, Orchestrator & Persistence

Phase 2 adds the Docker infrastructure: a FastAPI orchestrator, Redis job queue, TimescaleDB persistence, and async eval execution.

### 4.1 Starting the Stack

```bash
docker compose up -d
```

The stack includes:
- **TimescaleDB** — PostgreSQL 16 with time-series hypertables for eval results
- **Redis 7** — Job queue backend for RQ (Redis Queue)
- **Orchestrator** — FastAPI app + RQ worker in one container
- **Registry** — Eval registry microservice
- **Dashboard** — Next.js web UI

All containers use `host.docker.internal` to reach Ollama on the host machine.

### 4.2 Submitting Runs

When the orchestrator is running, `aeval run` automatically submits jobs to it:

```bash
aeval run factuality-v1 -m ollama:gemma3:4b
# → "Run submitted to orchestrator"
# → "Run ID: 550e8400-..."
# → "Track with: aeval results --run-id 550e8400-..."
```

The orchestrator:
1. Resolves the eval file path
2. Fetches model info from Ollama
3. Creates a pending run in the database
4. Enqueues an RQ job (30-minute timeout)
5. Returns immediately (HTTP 202)

The RQ worker:
1. Picks up the job
2. Sets status to "running"
3. Dynamically imports the eval .py file
4. Creates an OllamaModel instance
5. Runs the eval
6. Stores per-task results in TimescaleDB
7. Updates the run with final score, CI, and pass/fail status
8. Retries up to 3 times with exponential backoff on failure

### 4.3 Querying Results

```bash
# Most recent completed run
aeval results --last

# Specific run by ID
aeval results --run-id 550e8400-...

# Filter by eval and model
aeval results --eval factuality-v1 --model gemma3:4b

# JSON output
aeval results --eval factuality-v1 --output json

# Set limit
aeval results --limit 100
```

**`aeval results` options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--run-id` | string | — | Show specific run |
| `--eval` | string | — | Filter by eval name |
| `--model` | string | — | Filter by model name |
| `--last` | flag | false | Show most recent run |
| `--output` | table\|json | table | Output format |
| `--limit` | int | 20 | Max results |

### 4.4 Health Checking

```bash
aeval status
```

Shows connectivity status for:
- Ollama (reachable, model count)
- Orchestrator (reachable, DB/Redis/Ollama sub-checks)

---

## 5. Phase 3 — Web Dashboard

The dashboard runs at `http://localhost:3000` and provides visual access to all eval data.

### 5.1 Pages

| Page | URL | Description |
|------|-----|-------------|
| Home | `/` | System health panel + recent runs table |
| Runs | `/runs` | All runs with filters (eval, model, status) |
| Run Detail | `/runs/{id}` | Single run: score, CI, pass/fail, per-task results |
| Models | `/models` | Ollama model catalog (cards with family, size, quant) |
| Compare | `/compare` | Multi-model comparison with radar chart |
| Scorecard | `/scorecard` | Release readiness matrix (evals × models, pass/fail) |
| Taxonomy | `/taxonomy` | Coverage heat map + taxonomy tree (Phase 5) |

### 5.2 Key Components

- **Health Panel** — Green/red indicators for DB, Redis, Ollama connectivity
- **Runs Table** — Sortable table with status badges, score badges, timestamps
- **Run Filters** — Filter by eval name, model, status (pending/running/completed/failed)
- **Task Results Table** — Per-task breakdown with prediction, reference, score, latency
- **Radar Chart** — Spider plot comparing multiple models across eval dimensions
- **Comparison Table** — Side-by-side scores with significance indicators
- **Scorecard Grid** — Binary pass/fail matrix; model is "READY" if it passes all tested evals
- **Coverage Heatmap** — Taxonomy leaf nodes color-coded by health (green=active, yellow=watch, red=gap/saturated)
- **Taxonomy Tree** — Collapsible tree with discrimination scores and lifecycle labels

### 5.3 Navigation

The sidebar includes: Home, Runs, Models, Compare, Scorecard, Taxonomy.

---

## 6. Phase 4 — Eval Registry

The registry is a microservice that indexes eval packages from `registry-data/` on disk.

### 6.1 Eval Packages

Each eval is a directory in `registry-data/`:

```
registry-data/factuality-v1/
├── meta.yaml       # Metadata
├── eval.py         # @Eval definition
└── dataset.jsonl   # Evaluation data
```

**meta.yaml format:**
```yaml
name: factuality-v1
version: 1.0.0
description: Factual knowledge evaluation with 25 Q&A tasks
category: factuality
tags: [factuality, core, v1]
threshold: 0.6
dataset: dataset.jsonl
```

### 6.2 CLI Commands

```bash
# Search evals
aeval registry search "reasoning"

# List all evals
aeval registry list

# Get eval details
aeval registry info factuality-v1

# List suites
aeval registry suites
```

### 6.3 Built-in Suites

Defined in `evals/suites.yaml`:

| Suite | Evals | Timeout | Purpose |
|-------|-------|---------|---------|
| `smoke` | factuality-v1, reasoning-v1 | 10m | Quick validation |
| `standard` | factuality-v1, reasoning-v1, instruction-following-v1 | 20m | Standard gate |
| `safety` | safety-v1 | 15m | Safety testing |
| `pre-release` | factuality-v1, reasoning-v1, safety-v1, instruction-following-v1 | 30m | Pre-release gate |
| `full` | all 5 core evals | 45m | Comprehensive |

### 6.4 Core Evals

| Eval | Scorer | Tasks | Threshold | Description |
|------|--------|-------|-----------|-------------|
| `factuality-v1` | exact_match + llm_judge fallback | 25 | 0.6 | Factual Q&A |
| `reasoning-v1` | multiple_choice | 25 | 0.5 | Multi-step reasoning (A/B/C/D) |
| `safety-v1` | safety_refusal | 20 | 0.85 | Adversarial prompt refusal |
| `instruction-following-v1` | llm_judge (5-point rubric) | 20 | 0.6 | Instruction adherence |
| `code-gen-v1` | llm_judge | — | 0.7 | Code generation |

---

## 7. Phase 5 — Adaptive Intelligence

Phase 5 adds self-monitoring capabilities: a taxonomy of model capabilities, health metrics per eval, coverage analysis, and LLM-powered eval generation.

### 7.1 Capability Taxonomy

A hierarchical tree of 7 categories and ~30 leaf capabilities stored in the database:

| Category | Leaf Capabilities |
|----------|-------------------|
| **Reasoning** | Logical Deduction, Mathematical Reasoning, Causal Reasoning, Analogical Reasoning, Multi-Step Planning, Counterfactual Reasoning |
| **Knowledge & Factuality** | World Knowledge, Temporal Reasoning, Source Attribution, Uncertainty Calibration |
| **Language & Communication** | Instruction Following, Long-Form Generation, Summarization, Translation, Tone & Style Adaptation |
| **Code & Tool Use** | Code Generation, Code Debugging, API / Tool Calling, Agentic Task Completion |
| **Multimodal** | Image Understanding, Audio Understanding, Cross-Modal Reasoning |
| **Safety & Alignment** | Harmful Content Refusal, Bias & Fairness, Privacy Protection, Jailbreak Resistance |
| **Meta-Cognitive** | Self-Correction, Uncertainty Expression, Asking Clarifying Questions, Knowing Limitations |

Core evals are mapped to taxonomy nodes (e.g., factuality-v1 → World Knowledge, safety-v1 → Harmful Content Refusal).

### 7.2 Eval Health Monitoring

Each eval has a health record tracking:

| Field | Description |
|-------|-------------|
| `discrimination_power` | Between-model variance / total variance (0.0–1.0) |
| `saturation_type` | ceiling, floor, noise, or null |
| `lifecycle_state` | active, watch, saturated, or archived |
| `scores_by_model` | Average score per model (JSONB) |
| `last_checked` | When health was last computed |

#### Lifecycle State Machine

```
Active (disc > 0.15) → Watch (0.08 ≤ disc < 0.15) → Saturated (disc < 0.08 after 90 days) → Archived (manual)
```

- **Active** — eval differentiates models well
- **Watch** — discrimination declining, monitor closely
- **Saturated** — eval no longer useful (all models score similarly)
- **Archived** — manually retired

### 7.3 Health CLI

```bash
# Full health report
aeval health

# Refresh metrics first (triggers monitor worker)
aeval health --refresh

# JSON output
aeval health --json-output
```

**Output sections:**
1. **Suite Health Overview** — total evals, active/watch/saturated/archived counts, avg discrimination
2. **Taxonomy Coverage Table** — per-category capabilities with eval count, avg discrimination, status (Active/Watch/Saturated/GAP)
3. **Watch List** — evals approaching saturation
4. **Saturated List** — evals below discrimination threshold

### 7.4 Coverage Analysis

The taxonomy analyzer computes:
- **Coverage**: percentage of leaf nodes with at least one active eval
- **Gaps**: leaf nodes with zero evals or only saturated evals
- **Saturation rate**: fraction of evals in saturated state

```bash
curl http://localhost:8081/api/v1/health/coverage
```

Returns: `total_categories`, `total_nodes`, `covered_nodes`, `gap_count`, `coverage_pct`, `saturation_rate`, `avg_discrimination`, and per-lifecycle-state counts.

### 7.5 Eval Generation

The intelligence layer can generate new eval tasks using an Ollama model:

```bash
# Generate capability probe tasks
curl -X POST http://localhost:8081/api/v1/intelligence/generate \
  -H 'Content-Type: application/json' \
  -d '{"taxonomy_node": "Code Debugging", "method": "capability_probe", "count": 5}'
```

**Generation methods:**

| Method | Description |
|--------|-------------|
| `capability_probe` | General tasks testing a capability (varying difficulty) |
| `adversarial` | Edge cases and failure modes for a capability |
| `difficulty_escalation` | Harder versions of existing tasks (for saturated evals) |

**Quality gates** (applied automatically):
1. **Reference check** — task must have both a prompt and a non-empty reference answer
2. **Clarity check** — LLM rates task clarity 1–5; requires score ≥ 4

Generated evals are stored in `registry-data/` with `generated: true` metadata, a dataset.jsonl, and a template eval.py using the llm_judge scorer.

### 7.6 Dashboard: Taxonomy Page

The `/taxonomy` page shows:
- **Stats cards** — leaf nodes, covered count, gaps, avg discrimination
- **Coverage heatmap** — color-coded leaf nodes grouped by category
- **Taxonomy tree** — collapsible tree with eval counts and lifecycle badges

Color scheme: green = active + good discrimination, yellow = watch, red = gap or saturated.

---

## 8. Phase 6 — CI/CD & Polish

Phase 6 makes the system production-ready with CI/CD integration, contamination detection, alignment tax reporting, and documentation.

### 8.1 CI/CD Command

```bash
aeval ci \
  --suite pre-merge \
  --model ollama:brain-analyst-ft \
  --baseline-model ollama:llama3 \
  --fail-on regression \
  --report console
```

**`aeval ci` options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--suite` | string | required | Eval suite to run |
| `-m, --model` | string | required | Model to evaluate |
| `--fail-on` | regression\|threshold\|any | any | Failure trigger |
| `--baseline-model` | string | — | Model for regression comparison |
| `--report` | console\|github-pr-comment\|json | console | Output format |
| `--threshold` | float | — | Override threshold for all evals |
| `--local` | flag | false | Force local execution |

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | All evals pass, no regressions |
| 1 | Regression detected or threshold failure |
| 2 | System error (service unreachable, eval not found) |

**Regression detection:**

When `--baseline-model` is provided, the CI command:
1. Runs every eval in the suite against both models
2. Computes per-eval score delta
3. Runs Welch's t-test on per-task scores
4. A **regression** = statistically significant decrease (p < 0.05)

**`--fail-on` modes:**
- `regression` — only fail if a statistically significant regression is detected
- `threshold` — only fail if any eval falls below its threshold
- `any` — fail on either regression or threshold failure

#### Report Formats

**Console** — Rich panels and tables:
```
╭──── aeval CI ────╮
│ Suite: pre-merge  Model: brain-analyst-ft  Result: PASS │
╰──────────────────╯
┌──────────────────────┬───────┬───────────┬──────┬──────────┬───────┬────────────┐
│ Eval                 │ Score │ Threshold │ Pass │ Baseline │ Delta │ Regression │
├──────────────────────┼───────┼───────────┼──────┼──────────┼───────┼────────────┤
│ factuality-v1        │ 0.840 │ 0.60      │ PASS │ 0.760    │ +0.080│ no         │
│ reasoning-v1         │ 0.680 │ 0.50      │ PASS │ 0.640    │ +0.040│ no         │
└──────────────────────┴───────┴───────────┴──────┴──────────┴───────┴────────────┘
```

**JSON** — machine-readable for downstream tools:
```json
{
  "suite": "pre-merge",
  "model": "ollama:brain-analyst-ft",
  "passed": true,
  "exit_code": 0,
  "any_regression": false,
  "evals": [...]
}
```

**GitHub PR Comment** — markdown table with icons for posting to PRs:
```markdown
## :white_check_mark: Model Evaluation — PASS

**Suite:** `pre-merge` | **Model:** `brain-analyst-ft` | **Baseline:** `llama3`

| Eval | Score | Threshold | Pass | Baseline | Delta | Regression |
|------|------:|----------:|:----:|--------:|------:|:----------:|
| factuality-v1 | 0.840 | 0.60 | :white_check_mark: | 0.760 | +0.080 | :white_check_mark: |
```

### 8.2 GitHub Actions Workflow

A complete workflow is provided at `.github/workflows/model-eval.yml`:

**Triggers:** push/PR on `models/**`, `training/**`, `evals/**` paths, plus manual dispatch.

**Two jobs:**

1. **eval** — full suite with regression detection
   - Starts Docker stack, waits for health
   - Runs `aeval ci --suite <suite> --fail-on regression --report json`
   - Posts PR comment with results table
   - Uploads results as artifact

2. **safety-gate** — safety-specific suite
   - Runs `aeval ci --suite safety --fail-on threshold`
   - Blocks merge if safety evals fail

**Usage:**
```yaml
# Manual dispatch
gh workflow run model-eval.yml \
  -f model=ollama:brain-analyst-ft \
  -f suite=pre-merge
```

### 8.3 Contamination Detection

```bash
aeval contamination-check --training-manifest ./manifest.json
```

Compares SHA-256 hashes of eval prompts against a training data manifest to detect data leakage.

**`aeval contamination-check` options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--training-manifest` | path | required | JSON file with training data hashes |
| `--datasets-dir` | path | registry-data/ | Directory to scan for eval datasets |
| `--threshold` | float | 0.05 | Contamination rate to flag (5%) |
| `--output` | table\|json | table | Output format |

**Manifest formats** (JSON):
```json
// Format 1: Files with hashes
{"files": [{"path": "train.jsonl", "hash": "abc123..."}, ...]}

// Format 2: Hash list
{"hashes": ["abc123...", "def456...", ...]}

// Format 3: Flat array
["abc123...", "def456...", ...]
```

**How it works:**
1. Loads all hashes from the training manifest
2. For each eval dataset, computes SHA-256 of each prompt (normalized: stripped, lowercased)
3. Also hashes prompt+reference combinations
4. Reports contamination rate per eval
5. Flags evals above the threshold (default 5%)

**Output:**
```
Contamination Check
Manifest: ./manifest.json (15,000 entries)

┌──────────────────┬──────────────┬───────┬──────────────┬──────┬─────────┐
│ Eval             │ Dataset      │ Items │ Contaminated │ Rate │ Status  │
├──────────────────┼──────────────┼───────┼──────────────┼──────┼─────────┤
│ factuality-v1    │ dataset.jsonl│ 25    │ 0            │ 0.0% │ clean   │
│ reasoning-v1     │ dataset.jsonl│ 25    │ 2            │ 8.0% │ FLAGGED │
└──────────────────┴──────────────┴───────┴──────────────┴──────┴─────────┘
```

**Exit code:** 1 if any eval is flagged, 0 if all clean.

### 8.4 Alignment Tax Report

```bash
aeval compare ollama:brain-analyst-ft ollama:llama3 --suite core --format alignment-tax
```

Shows the cost of fine-tuning: what improved, what degraded, and the net tradeoff.

**Output sections:**

1. **Improvements** — evals where the fine-tuned model significantly outperforms the baseline, sorted by delta, with effect size
2. **Degradations (Alignment Tax)** — evals where the fine-tuned model is significantly worse, sorted by delta
3. **Unchanged** — no statistically significant difference
4. **Net Assessment** — improved/degraded/unchanged counts, net average delta, total alignment tax, gain/cost ratio with interpretation

**Gain/cost interpretation:**
- ≥ 2.0x — strong net improvement despite alignment tax
- ≥ 1.0x — marginal improvement, review degradations
- < 1.0x — alignment tax exceeds improvements

---

## 9. Configuration Reference

### aeval.yaml

```yaml
ollama:
  host: http://localhost:11434       # Ollama API URL
  timeout: 300                        # Request timeout (seconds)
  keep_alive: 5m                      # Model keep-alive duration

judge_model: ollama:gpt-oss:20b      # Default LLM judge model
datasets_dir: ./datasets              # Dataset file search path
evals_dir: ./evals                    # Eval file search path
orchestrator_url: http://localhost:8081   # Orchestrator API URL
registry_url: http://localhost:8082       # Registry API URL

intelligence:
  generator_model: ollama:gpt-oss:20b     # Model for eval generation
  calibration_model: ollama:gemma3        # Model for calibration tasks
  schedule_saturation_check: weekly       # Saturation check frequency
  schedule_coverage_check: weekly         # Coverage check frequency
```

**Config search order:**
1. `AEVAL_CONFIG` environment variable
2. `aeval.yaml` in current directory, then parent directories

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AEVAL_CONFIG` | — | Path to aeval.yaml |
| `AEVAL_SUITES_FILE` | — | Path to suites.yaml |
| `DATABASE_URL` | postgresql://aeval:aeval_dev@localhost:5432/aeval | TimescaleDB connection |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection |
| `OLLAMA_HOST` | http://host.docker.internal:11434 | Ollama API (Docker) |
| `ORCHESTRATOR_PORT` | 8081 | Orchestrator listen port |
| `REGISTRY_PORT` | 8082 | Registry listen port |
| `DASHBOARD_PORT` | 3000 | Dashboard listen port |
| `NEXT_PUBLIC_API_URL` | http://localhost:8081 | Dashboard → Orchestrator (browser) |
| `INTELLIGENCE_GENERATOR_MODEL` | gemma3 | LLM for eval generation |
| `INTELLIGENCE_CALIBRATION_MODEL` | gemma3 | LLM for calibration |

---

## 10. API Reference

### Orchestrator API (port 8081)

All endpoints are prefixed with `/api/v1`.

#### Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/runs` | Submit eval run (202 Accepted) |
| GET | `/runs` | List runs (filter: eval_name, model, status, limit, offset) |
| GET | `/runs/{run_id}` | Get run detail with per-task results |
| GET | `/results` | Query completed runs only |

**POST /runs request:**
```json
{
  "eval_name": "factuality-v1",
  "model": "ollama:gemma3:4b",
  "threshold": 0.7,
  "metadata": {}
}
```

**POST /runs response (202):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Run submitted successfully"
}
```

#### Models

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/models` | List Ollama models (proxies to Ollama /api/tags) |

#### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check (DB, Redis, Ollama) |

#### Taxonomy (Phase 5)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/taxonomy` | Full taxonomy tree with coverage stats |
| GET | `/taxonomy/{node_id}` | Node detail with mapped evals |

#### Eval Health (Phase 5)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/evals` | Eval health list (filter: lifecycle_state) |
| GET | `/health/coverage` | Coverage summary |
| POST | `/health/refresh` | Trigger health check on all evals |

#### Intelligence (Phase 5)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/intelligence/generate` | Generate eval tasks via LLM |

**POST /intelligence/generate request:**
```json
{
  "taxonomy_node": "Code Debugging",
  "method": "capability_probe",
  "count": 5
}
```

### Registry API (port 8082)

All endpoints are prefixed with `/api/v1`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/evals` | List all registry evals |
| GET | `/evals/{name}` | Get eval detail (code preview, dataset size) |
| GET | `/search?q=...` | Search evals by name, tag, description |
| GET | `/suites` | List all suites |
| GET | `/health` | Registry health check |

---

## 11. Database Schema

### Tables (001_initial.sql)

**models**
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Auto-increment ID |
| name | TEXT UNIQUE | Model name (e.g., "gemma3:4b") |
| family | TEXT | Model family (e.g., "gemma3") |
| param_size | TEXT | Parameter count (e.g., "4.3B") |
| quant | TEXT | Quantization (e.g., "Q4_K_M") |
| multimodal | BOOLEAN | Supports images |
| digest | TEXT | Model digest hash |
| first_seen | TIMESTAMPTZ | First registration |
| last_seen | TIMESTAMPTZ | Last activity |

**eval_definitions**
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Auto-increment ID |
| name | TEXT UNIQUE | Eval name (e.g., "factuality-v1") |
| file_path | TEXT | Path to .py file |
| tags | TEXT[] | Array of tags |
| threshold | DOUBLE PRECISION | Pass/fail threshold |
| description | TEXT | Human-readable description |
| metadata | JSONB | Arbitrary metadata |

**eval_runs**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | Run identifier |
| eval_id | INTEGER FK | → eval_definitions |
| model_id | INTEGER FK | → models |
| status | TEXT | pending, running, completed, failed |
| score | DOUBLE PRECISION | Aggregate score |
| ci_lower, ci_upper, ci_level | DOUBLE PRECISION | Confidence interval |
| num_tasks | INTEGER | Task count |
| passed | BOOLEAN | Pass/fail result |
| threshold | DOUBLE PRECISION | Threshold used |
| tier | TEXT | Execution tier |
| error | TEXT | Error message (if failed) |
| metadata | JSONB | Run metadata |
| submitted_at | TIMESTAMPTZ | Submission time |
| started_at | TIMESTAMPTZ | Execution start |
| completed_at | TIMESTAMPTZ | Execution end |

**eval_results** (TimescaleDB hypertable)
| Column | Type | Description |
|--------|------|-------------|
| time | TIMESTAMPTZ | Result timestamp (partition key) |
| run_id | UUID FK | → eval_runs |
| task_id | TEXT | Task identifier |
| score | DOUBLE PRECISION | Task score |
| passed | BOOLEAN | Task pass/fail |
| prediction | TEXT | Model output |
| reference | TEXT | Expected answer |
| latency_ms | DOUBLE PRECISION | Inference time |
| tokens_used | INTEGER | Token count |
| metadata | JSONB | Task metadata |

### Tables (002_taxonomy_health.sql)

**taxonomy_nodes**
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Node ID |
| parent_id | INTEGER FK | → taxonomy_nodes (null for root) |
| name | TEXT | Capability name |
| description | TEXT | Description |
| level | INTEGER | Tree depth (0 = root) |

**taxonomy_eval_map** (many-to-many)
| Column | Type | Description |
|--------|------|-------------|
| taxonomy_id | INTEGER FK PK | → taxonomy_nodes |
| eval_id | INTEGER FK PK | → eval_definitions |

**eval_health**
| Column | Type | Description |
|--------|------|-------------|
| eval_id | INTEGER PK FK | → eval_definitions |
| discrimination_power | DOUBLE PRECISION | 0.0–1.0 |
| saturation_type | TEXT | ceiling, floor, noise, null |
| lifecycle_state | TEXT | active, watch, saturated, archived |
| scores_by_model | JSONB | Per-model average scores |
| last_checked | TIMESTAMPTZ | Last health check |
| state_changed_at | TIMESTAMPTZ | Last lifecycle transition |
| watch_entered_at | TIMESTAMPTZ | When watch state began |

---

## 12. Architecture

### System Diagram

```
┌──────────────────────────────────────────────────┐
│  Developer Machine                                │
│                                                    │
│  ┌──────────────────┐   ┌─────────────────────┐  │
│  │  aeval CLI / SDK  │──▶│  Ollama (host)      │  │
│  │  (Python)         │   │  :11434             │  │
│  └────────┬─────────┘   │  13 models          │  │
│           │              └─────────▲───────────┘  │
│           │ HTTP                   │               │
│  ┌────────▼─────────────────────── │ ──────────┐  │
│  │  Docker Compose                 │           │  │
│  │                                 │           │  │
│  │  ┌───────────────┐  ┌────────── │ ───────┐  │  │
│  │  │  TimescaleDB   │  │  Orchestrator      │  │  │
│  │  │  :5432         │◀─│  :8081             │──┘  │
│  │  └───────────────┘  │  FastAPI + RQ Worker│     │
│  │                      └────────────────────┘     │
│  │  ┌───────────────┐  ┌────────────────────┐     │
│  │  │  Redis         │  │  Registry          │     │
│  │  │  :6379         │◀─│  :8082             │     │
│  │  └───────────────┘  └────────────────────┘     │
│  │                      ┌────────────────────┐     │
│  │                      │  Dashboard         │     │
│  │                      │  :3000             │     │
│  │                      └────────────────────┘     │
│  └─────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Data Flow

1. **User** runs `aeval run factuality-v1 -m ollama:gemma3:4b`
2. **SDK** checks if orchestrator is reachable
3. If yes: **POST /api/v1/runs** → orchestrator creates pending run, enqueues RQ job
4. **RQ Worker** picks up job, loads eval .py, creates OllamaModel, calls eval function
5. Eval function calls **model.generate()** → HTTP to **Ollama** on host
6. Scorer computes per-task results
7. Worker stores results in **TimescaleDB**, updates run status
8. **Dashboard** queries API, renders results
9. **CLI** queries results via `aeval results --last`

### Dual-Mode Execution

The SDK works in two modes:

| Mode | When | Description |
|------|------|-------------|
| **Orchestrator** | Docker stack is running | Submits async jobs, results persisted in DB |
| **Local** | `--local` flag or orchestrator unreachable | Runs eval directly, prints results to console |

### Technology Stack

| Component | Technology |
|-----------|-----------|
| SDK / CLI | Python 3.11+, Click, httpx, Pydantic, Rich, NumPy, SciPy |
| Orchestrator | Python, FastAPI, RQ (Redis Queue) |
| Database | TimescaleDB (PostgreSQL 16 + hypertables) |
| Queue | Redis 7 |
| Dashboard | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Registry | Python, FastAPI, file-backed storage |
| Model Backend | Ollama (HTTP API on host, GPU-native) |
