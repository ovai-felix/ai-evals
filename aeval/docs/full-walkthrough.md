# aeval Full Walkthrough — All Functionality

A complete, runnable walkthrough of every feature across all 6 phases.

---

## Phase 1: Setup & Core SDK

```bash
# ─── Install ───
cd /Users/omatsone/Desktop/ai-eval/aeval
python3 -m venv .venv
source .venv/bin/activate
pip install -e ./sdk

# Verify install
aeval --version

# Initialize project config (creates aeval.yaml, evals/, datasets/)
aeval init

# Check Ollama connectivity
aeval status

# List available Ollama models (family, size, quant, multimodal)
aeval models
```

## Phase 1: Run a Single Eval

```bash
# Run a built-in eval against a model
aeval run factuality-v1 -m ollama:gemma3:4b

# Run by file path
aeval run ./evals/core/factuality_v1.py -m ollama:gemma3:4b

# Override the pass/fail threshold
aeval run factuality-v1 -m ollama:gemma3:4b --threshold 0.5

# JSON output (machine-readable)
aeval run factuality-v1 -m ollama:gemma3:4b --output json

# Force local execution (skip orchestrator even if it's running)
aeval run factuality-v1 -m ollama:gemma3:4b --local
```

## Phase 1: Run Suites

```bash
# Quick validation (factuality + reasoning)
aeval run --suite smoke -m ollama:gemma3:4b

# Standard gate (factuality + reasoning + instruction-following)
aeval run --suite standard -m ollama:llama3

# Safety only
aeval run --suite safety -m ollama:llama3

# Pre-release gate (4 evals)
aeval run --suite pre-release -m ollama:llama3

# Full suite (all 5 core evals)
aeval run --suite full -m ollama:llama3
```

## Phase 1: Compare Models

```bash
# Compare two models on a single eval
aeval compare ollama:gemma3:4b ollama:llama3 --eval factuality-v1

# Compare on multiple evals
aeval compare ollama:gemma3:4b ollama:llama3 \
  --eval factuality-v1 \
  --eval reasoning-v1

# Compare on an entire suite
aeval compare ollama:gemma3:4b ollama:llama3 --suite core

# JSON comparison output
aeval compare ollama:gemma3:4b ollama:llama3 --eval reasoning-v1 --output json
```

## Phase 2: Docker Stack & Persistence

```bash
# Start all 5 services (DB, Redis, Orchestrator, Registry, Dashboard)
docker compose up -d

# Verify all services are healthy
aeval status
curl http://localhost:8081/api/v1/health

# Now `aeval run` submits to orchestrator (async, persisted)
aeval run factuality-v1 -m ollama:gemma3:4b
# → "Run ID: 550e8400-..."

# Query the most recent completed run
aeval results --last

# Query a specific run by ID
aeval results --run-id 550e8400-e29b-41d4-a716-446655440000

# Filter results by eval and model
aeval results --eval factuality-v1 --model gemma3:4b

# JSON results
aeval results --eval factuality-v1 --output json

# Limit number of results
aeval results --limit 100
```

## Phase 2: Orchestrator API (direct)

```bash
# Submit a run via API
curl -X POST http://localhost:8081/api/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{"eval_name": "factuality-v1", "model": "ollama:gemma3:4b"}'

# List all runs
curl http://localhost:8081/api/v1/runs

# Filter runs
curl "http://localhost:8081/api/v1/runs?eval_name=factuality-v1&status=completed&limit=5"

# Get a specific run with per-task results
curl http://localhost:8081/api/v1/runs/550e8400-e29b-41d4-a716-446655440000

# List models
curl http://localhost:8081/api/v1/models
```

## Phase 3: Dashboard

```bash
# Open the web dashboard
open http://localhost:3000

# Pages to visit:
#   http://localhost:3000           — Home (health + recent runs)
#   http://localhost:3000/runs      — All runs with filters
#   http://localhost:3000/runs/{id} — Single run detail + task breakdown
#   http://localhost:3000/models    — Ollama model catalog
#   http://localhost:3000/compare   — Multi-model radar chart
#   http://localhost:3000/scorecard — Release readiness matrix
#   http://localhost:3000/taxonomy  — Coverage heat map (Phase 5)
```

## Phase 4: Eval Registry

```bash
# Search evals by keyword
aeval registry search "reasoning"
aeval registry search "safety"

# List all registered evals
aeval registry list

# Get detailed info for a specific eval
aeval registry info factuality-v1
aeval registry info code-gen-v1

# List all suites
aeval registry suites

# Registry API directly
curl http://localhost:8082/api/v1/evals
curl http://localhost:8082/api/v1/evals/factuality-v1
curl "http://localhost:8082/api/v1/search?q=reasoning"
curl http://localhost:8082/api/v1/suites
curl http://localhost:8082/api/v1/health
```

## Phase 5: Adaptive Intelligence

```bash
# Full eval health report (coverage, saturation, discrimination)
aeval health

# Refresh health metrics first (triggers monitor worker), then show report
aeval health --refresh

# JSON output
aeval health --json-output

# Taxonomy API
curl http://localhost:8081/api/v1/taxonomy
curl http://localhost:8081/api/v1/taxonomy/1

# Eval health API
curl http://localhost:8081/api/v1/health/evals
curl "http://localhost:8081/api/v1/health/evals?lifecycle_state=active"
curl "http://localhost:8081/api/v1/health/evals?lifecycle_state=watch"
curl "http://localhost:8081/api/v1/health/evals?lifecycle_state=saturated"

# Coverage summary
curl http://localhost:8081/api/v1/health/coverage

# Trigger health refresh via API
curl -X POST http://localhost:8081/api/v1/health/refresh

# Generate new eval tasks with LLM
curl -X POST http://localhost:8081/api/v1/intelligence/generate \
  -H 'Content-Type: application/json' \
  -d '{"taxonomy_node": "Code Debugging", "method": "capability_probe", "count": 5}'

curl -X POST http://localhost:8081/api/v1/intelligence/generate \
  -H 'Content-Type: application/json' \
  -d '{"taxonomy_node": "Causal Reasoning", "method": "adversarial", "count": 3}'

curl -X POST http://localhost:8081/api/v1/intelligence/generate \
  -H 'Content-Type: application/json' \
  -d '{"taxonomy_node": "World Knowledge", "method": "difficulty_escalation", "count": 5}'

# View coverage heat map in dashboard
open http://localhost:3000/taxonomy
```

## Phase 6: CI/CD Integration

```bash
# Basic CI run — fail on any issue
aeval ci --suite smoke --model ollama:gemma3:4b --fail-on any --report console

# CI with regression detection against a baseline
aeval ci \
  --suite pre-release \
  --model ollama:brain-analyst-ft \
  --baseline-model ollama:llama3 \
  --fail-on regression \
  --report console

# CI with threshold-only checking
aeval ci --suite safety --model ollama:llama3 --fail-on threshold --report console

# JSON output for automation pipelines
aeval ci \
  --suite pre-release \
  --model ollama:brain-analyst-ft \
  --baseline-model ollama:llama3 \
  --fail-on regression \
  --report json

# GitHub PR comment format (markdown table with emoji badges)
aeval ci \
  --suite pre-release \
  --model ollama:brain-analyst-ft \
  --baseline-model ollama:llama3 \
  --fail-on regression \
  --report github-pr-comment

# Override threshold for all evals
aeval ci --suite smoke --model ollama:gemma3:4b --threshold 0.5 --report console

# Force local execution
aeval ci --suite smoke --model ollama:gemma3:4b --local --report console

# Exit codes: 0 = pass, 1 = regression/failure, 2 = system error
echo $?
```

## Phase 6: Alignment Tax Report

```bash
# Full alignment tax analysis (fine-tuned vs baseline)
aeval compare ollama:brain-analyst-ft ollama:llama3 \
  --suite core \
  --format alignment-tax

# Shows: Improvements, Degradations (the "tax"), Unchanged, Net Assessment
# Includes: effect size, gain/cost ratio, actionable interpretation
```

## Phase 6: Contamination Detection

```bash
# Check eval datasets for training data leakage
aeval contamination-check --training-manifest ./manifest.json

# Custom datasets directory
aeval contamination-check \
  --training-manifest ./manifest.json \
  --datasets-dir ./datasets

# Custom contamination threshold (flag at 10% instead of 5%)
aeval contamination-check \
  --training-manifest ./manifest.json \
  --threshold 0.10

# JSON output
aeval contamination-check \
  --training-manifest ./manifest.json \
  --output json

# Exit code: 0 = all clean, 1 = contamination flagged
echo $?
```

## Phase 6: GitHub Actions (manual trigger)

```bash
# Trigger the CI workflow manually
gh workflow run model-eval.yml \
  -f model=ollama:brain-analyst-ft \
  -f suite=pre-release

# Watch the run
gh run watch
```

## Teardown

```bash
# Stop the Docker stack
docker compose down

# Stop and remove volumes (wipes DB)
docker compose down -v
```
