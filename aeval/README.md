# aeval — AI Evaluation Pipeline

Local-first AI model evaluation with statistical rigor. Write evals like pytest, run them against any Ollama model, get scores with confidence intervals, compare models, and ship with confidence.

## Quickstart (10 minutes)

### 1. Install

```bash
# Install the SDK (requires Python 3.11+)
pip install -e ./sdk

# Verify Ollama is running
aeval status
```

### 2. Write your first eval

Create `evals/hello_eval.py`:

```python
from aeval.core.eval import Eval
from aeval.core.dataset import Dataset
from aeval.core.scorer import Scorer

@Eval(name="hello-eval", threshold=0.6)
def hello_eval(model):
    dataset = Dataset.from_list([
        {"prompt": "What is the capital of France?", "reference": "Paris"},
        {"prompt": "What is 2 + 2?", "reference": "4"},
        {"prompt": "Who wrote Romeo and Juliet?", "reference": "Shakespeare"},
    ])

    responses = model.generate(dataset.prompts)
    predictions = [r.text for r in responses]
    return Scorer.exact_match(predictions, dataset.references)
```

### 3. Run it

```bash
# Run against a model
aeval run hello-eval -m ollama:gemma3:4b

# Compare two models
aeval compare ollama:gemma3:4b ollama:llama3 --eval hello-eval

# Run a pre-defined suite
aeval run --suite smoke -m ollama:llama3
```

### 4. Start the full stack (optional)

```bash
# Start all services (DB, Redis, orchestrator, dashboard)
docker compose up -d

# Open dashboard
open http://localhost:3000

# Runs are now persisted and visible in the dashboard
aeval run --suite full -m ollama:brain-analyst-ft
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  CLI / SDK (aeval)         Python package   │
│  Write evals, run locally or via orchestrator│
└──────────────┬──────────────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────────────┐
│  Orchestrator (FastAPI)     :8081           │
│  Job queue (Redis), persistence (TimescaleDB)│
├─────────────────────────────────────────────┤
│  Registry (FastAPI)         :8082           │
│  Eval definitions, suites, search           │
├─────────────────────────────────────────────┤
│  Dashboard (Next.js)        :3000           │
│  Runs, comparison, scorecard, taxonomy      │
└──────────────┬──────────────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────────────┐
│  Ollama (host)              :11434          │
│  13 models: llama3, gemma3, brain-analyst...│
└─────────────────────────────────────────────┘
```

**Dual-mode execution:** The SDK works standalone (direct Ollama calls) or with the full Docker stack. Use `--local` to force standalone mode.

## CLI Reference

| Command | Description |
|---------|-------------|
| `aeval init` | Initialize project config (`aeval.yaml`) |
| `aeval models` | List available Ollama models |
| `aeval run <eval> -m <model>` | Run a single eval |
| `aeval run --suite <name> -m <model>` | Run an eval suite |
| `aeval compare <model-a> <model-b> --eval <eval>` | Compare models with significance testing |
| `aeval compare <a> <b> --suite core --format alignment-tax` | Alignment tax report |
| `aeval results --last` | Show last completed run |
| `aeval status` | Check Ollama + orchestrator connectivity |
| `aeval health` | Eval suite health (coverage, saturation) |
| `aeval health --refresh` | Refresh health metrics, then report |
| `aeval ci --suite <name> --model <model>` | CI/CD mode with exit codes |
| `aeval contamination-check --training-manifest <path>` | Check for data contamination |
| `aeval registry search <query>` | Search the eval registry |

## CI/CD Integration

```bash
# Run pre-merge eval suite with regression detection
aeval ci \
  --suite pre-merge \
  --model ollama:brain-analyst-ft \
  --baseline-model ollama:llama3 \
  --fail-on regression \
  --report github-pr-comment

# Exit codes: 0 = pass, 1 = regression/failure, 2 = system error
```

See `.github/workflows/model-eval.yml` for a complete GitHub Actions example.

## Eval Suites

Pre-defined suites in `evals/suites.yaml`:

| Suite | Evals | Purpose |
|-------|-------|---------|
| `smoke` | factuality, reasoning | Quick validation (2 evals) |
| `standard` | factuality, reasoning, instruction-following | Standard gate (3 evals) |
| `safety` | safety | Safety-focused (1 eval) |
| `pre-release` | factuality, reasoning, safety, instruction-following | Pre-release gate (4 evals) |
| `full` | all 5 core evals | Comprehensive (5 evals) |

## Built-in Scorers

| Scorer | Method | Description |
|--------|--------|-------------|
| `Scorer.exact_match` | String comparison | Normalized string matching |
| `Scorer.multiple_choice` | A/B/C/D extraction | Multiple choice answer extraction |
| `Scorer.llm_judge` | LLM-as-judge | Ollama model rates quality on a rubric |
| `Scorer.safety_refusal` | Refusal detection | Checks if model refused unsafe prompts |

## Statistical Features

- **Confidence intervals**: Bootstrap (default) or normal approximation
- **Significance testing**: Welch's t-test or permutation test
- **Effect size**: Cohen's d
- **Discrimination power**: Between-model variance / total variance
- **Saturation detection**: Ceiling, floor, and noise saturation

## Configuration

Create `aeval.yaml` in your project root:

```yaml
ollama:
  host: http://localhost:11434
  timeout: 300
  keep_alive: 5m

judge_model: ollama:gpt-oss:20b
datasets_dir: ./datasets
evals_dir: ./evals

intelligence:
  generator_model: ollama:gpt-oss:20b
  calibration_model: ollama:gemma3
  schedule_saturation_check: weekly
  schedule_coverage_check: weekly
```

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `db` | 5432 | TimescaleDB (PostgreSQL 16) |
| `redis` | 6379 | Redis 7 (job queue) |
| `orchestrator` | 8081 | FastAPI eval orchestrator |
| `registry` | 8082 | Eval registry service |
| `dashboard` | 3000 | Next.js web dashboard |

All data stays local. No telemetry, no cloud sync, no external API calls.

## Project Structure

```
aeval/
├── sdk/                    # Python SDK + CLI
├── orchestrator/           # FastAPI orchestrator + worker
├── registry/               # Eval registry service
├── dashboard/              # Next.js dashboard
├── evals/                  # Eval definitions
├── datasets/               # Eval datasets
├── registry-data/          # Packaged eval metadata
├── docker-compose.yml      # Full stack
└── aeval.yaml              # SDK config
```
