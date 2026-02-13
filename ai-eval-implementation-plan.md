# Implementation Plan: aeval — AI Evaluation Pipeline

## Context

The product design for `aeval` is complete in `ai-eval-pipeline-consolidated.md`. It describes a three-layer, Docker-containerized evaluation system for pre-training and post-training AI models, with Ollama as the primary model backend. No code exists yet — this plan covers the full build from zero to working system.

**Reference doc:** `ai-eval-pipeline-consolidated.md` (same directory)

---

## Project Structure

```
aeval/
├── docker-compose.yml                  # Full stack definition
├── .env.example                        # Default config (ports, Ollama host)
├── aeval.yaml.example                  # SDK/CLI config template
├── README.md
│
├── sdk/                                # Python SDK + CLI (Layer 2)
│   ├── pyproject.toml                  # Package: aeval
│   ├── src/
│   │   └── aeval/
│   │       ├── __init__.py
│   │       ├── cli.py                  # CLI entrypoint (click-based)
│   │       ├── commands/
│   │       │   ├── run.py              # aeval run
│   │       │   ├── compare.py          # aeval compare
│   │       │   ├── models.py           # aeval models (Ollama discovery)
│   │       │   ├── status.py           # aeval status
│   │       │   ├── health.py           # aeval health
│   │       │   ├── init.py             # aeval init
│   │       │   └── registry.py         # aeval registry search/publish
│   │       ├── core/
│   │       │   ├── eval.py             # @Eval decorator
│   │       │   ├── dataset.py          # Dataset loader (JSONL, JSON, CSV)
│   │       │   ├── scorer.py           # Built-in scorers
│   │       │   ├── model.py            # Model adapter interface
│   │       │   ├── result.py           # Result + confidence interval dataclass
│   │       │   └── suite.py            # Eval suite (named collection of evals)
│   │       ├── adapters/
│   │       │   ├── ollama.py           # Ollama model adapter (primary)
│   │       │   ├── openai_compat.py    # OpenAI-compatible API adapter
│   │       │   └── huggingface.py      # HuggingFace local model adapter
│   │       ├── scorers/
│   │       │   ├── exact_match.py
│   │       │   ├── llm_judge.py        # LLM-as-judge (via Ollama)
│   │       │   ├── embedding_sim.py
│   │       │   ├── safety_refusal.py
│   │       │   ├── multiple_choice.py
│   │       │   └── code_execution.py
│   │       ├── stats/
│   │       │   ├── significance.py     # p-values, confidence intervals
│   │       │   └── discrimination.py   # Eval discrimination power
│   │       └── client.py              # HTTP client to orchestrator API
│   └── tests/
│       ├── test_ollama_adapter.py
│       ├── test_scorers.py
│       ├── test_eval_decorator.py
│       ├── test_dataset.py
│       └── test_cli.py
│
├── orchestrator/                       # Eval Orchestrator service (Layer 1)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py                     # FastAPI app entrypoint
│       ├── api/
│       │   ├── runs.py                 # POST/GET /runs
│       │   ├── results.py              # GET /results
│       │   ├── models.py               # GET /models (proxy to Ollama)
│       │   └── health.py               # GET /health
│       ├── engine/
│       │   ├── scheduler.py            # Job scheduling + queue management
│       │   ├── runner.py               # Eval execution engine
│       │   └── ollama_client.py        # Ollama HTTP client (host.docker.internal)
│       ├── db/
│       │   ├── connection.py           # TimescaleDB connection pool
│       │   ├── models.py               # SQLAlchemy/raw SQL models
│       │   └── migrations/             # Schema migrations (alembic or raw SQL)
│       │       └── 001_initial.sql
│       └── config.py                   # Settings from env vars
│
├── dashboard/                          # Web Dashboard (Layer 1)
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── page.tsx                # Home — recent runs, system health
│       │   ├── runs/
│       │   │   └── [id]/page.tsx       # Run detail — per-task scores
│       │   ├── compare/page.tsx        # Model comparison matrix
│       │   ├── models/page.tsx         # Ollama model catalog
│       │   ├── health/page.tsx         # Eval suite health + coverage
│       │   └── scorecard/page.tsx      # Release readiness scorecard
│       └── components/
│           ├── RadarChart.tsx           # Capability radar
│           ├── ComparisonTable.tsx      # Side-by-side scores with significance
│           ├── TimelineChart.tsx        # Checkpoint timeline
│           └── CoverageHeatMap.tsx      # Taxonomy coverage
│
├── registry/                           # Eval Registry service (Layer 2)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py                     # FastAPI app
│       ├── api/
│       │   ├── evals.py                # CRUD for eval definitions
│       │   └── suites.py               # CRUD for eval suites
│       └── storage.py                  # File-backed eval storage
│
├── intelligence/                       # Adaptive Intelligence (Layer 3)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py                     # Background worker entrypoint
│       ├── taxonomy.py                 # Capability taxonomy engine
│       ├── saturation.py               # Saturation + discrimination monitor
│       ├── generator.py                # Eval generator (adversarial, probing, escalation)
│       └── ollama_client.py            # Ollama client for generation tasks
│
├── evals/                              # Default eval definitions
│   ├── core/
│   │   ├── factuality_v1.py
│   │   ├── reasoning_v1.py
│   │   ├── safety_v1.py
│   │   ├── instruction_following_v1.py
│   │   └── code_gen_v1.py
│   └── suites.yaml                     # Suite definitions (smoke, standard, full)
│
├── datasets/                           # Eval datasets (versioned)
│   └── .gitkeep
│
└── registry-data/                      # Shared eval registry storage
    └── .gitkeep
```

---

## Implementation Phases

### Phase 1: SDK + CLI + Ollama Adapter (Weeks 1-3)
> Goal: `pip install aeval && aeval run my-eval --model ollama:llama3` works end-to-end without Docker services.

**1.1 — Project scaffold**
- Create `aeval/` directory structure
- `pyproject.toml` with Click, httpx, pydantic, rich (for CLI tables), scipy (for stats)
- `aeval.yaml.example` with Ollama host config

**1.2 — Ollama adapter** (`sdk/src/aeval/adapters/ollama.py`)
- `OllamaModel` class implementing `Model` interface
- `GET /api/tags` for model discovery (`aeval models`)
- `POST /api/chat` for chat completions (`model.generate()`)
- `POST /api/generate` for raw completions (`model.complete()`)
- Image input support for multimodal models (llava, FintellectAI_images)
- Configurable timeout, keep_alive
- Connection health check

**1.3 — Core eval framework** (`sdk/src/aeval/core/`)
- `@Eval` decorator that registers eval functions
- `Dataset` class — load from JSONL, JSON, CSV, or Python list
- `Model` abstract base class with `generate()` and `complete()`
- `Result` dataclass with score, confidence interval, baseline delta

**1.4 — Scorers** (`sdk/src/aeval/scorers/`)
- `exact_match` — string comparison with normalization
- `multiple_choice` — A/B/C/D extraction + match
- `llm_judge` — send to Ollama judge model with rubric, parse rating
- `safety_refusal` — check if model refused unsafe prompts

**1.5 — Statistical rigor** (`sdk/src/aeval/stats/`)
- Confidence intervals (bootstrap or normal approximation)
- Significance testing (two-sample t-test or permutation test)
- Effect size (Cohen's d)

**1.6 — CLI** (`sdk/src/aeval/cli.py`)
- `aeval init` — create aeval.yaml, detect Ollama
- `aeval models` — list Ollama models (table format via rich)
- `aeval run <eval> --model ollama:<name>` — run single eval, print results
- `aeval compare <model-a> <model-b> --eval <eval>` — side-by-side with significance
- JSON output mode (`--output json`) for CI integration

**1.7 — Tests**
- Unit tests for Ollama adapter (mock HTTP responses)
- Unit tests for each scorer
- Unit tests for statistical functions
- Integration test: run a real eval against a live Ollama model

**Phase 1 exit criteria:** Can write a 10-line eval in Python, run it against any Ollama model, get scores with confidence intervals, and compare two models from the CLI.

---

### Phase 2: Docker Stack + Orchestrator + Persistence (Weeks 4-6)
> Goal: `docker compose up -d` deploys the platform. Eval results persist and are queryable.

**2.1 — Docker Compose**
- `docker-compose.yml` with all services
- `host.docker.internal` networking for Ollama access
- TimescaleDB (postgres:16 + timescaledb extension)
- Redis 7 for job queue
- Orchestrator container (Python/FastAPI)
- `.env.example` with all configurable values

**2.2 — Database schema** (`orchestrator/src/db/migrations/001_initial.sql`)
- `models` table — model registry (auto-populated from Ollama)
- `eval_definitions` table — eval metadata, code hash, dataset hash
- `eval_runs` table — run metadata (model, suite, tier, trigger, timestamps)
- `eval_results` hypertable — task-level scores, CI, baseline delta, p-value (time-series partitioned)
- Indexes on model_id, eval_id, created_at

**2.3 — Orchestrator API** (`orchestrator/src/api/`)
- `POST /api/v1/runs` — submit eval run (model, eval/suite, tier)
- `GET /api/v1/runs` — list runs with filters
- `GET /api/v1/runs/{id}` — run detail with per-task results
- `GET /api/v1/results` — query results across runs (for comparison)
- `GET /api/v1/models` — proxy to Ollama `/api/tags`
- `GET /api/v1/health` — stack health check

**2.4 — Eval execution engine** (`orchestrator/src/engine/`)
- Redis-backed job queue (rq or celery with Redis broker)
- Job: load eval definition → call Ollama → score → store results
- Sequential model execution (one model at a time via Ollama)
- Retry logic (3x with backoff) for Ollama timeouts
- Tiered execution: smoke (subset of evals), standard (full), comprehensive (full + LLM-judge)

**2.5 — SDK ↔ Orchestrator integration**
- Update SDK `client.py` to submit runs via orchestrator API
- `aeval run` checks for orchestrator; if available, delegates; if not, runs locally (standalone mode)
- `aeval status` queries orchestrator health + Ollama health + queue depth
- `aeval results <eval> --last` fetches from orchestrator DB

**Phase 2 exit criteria:** `docker compose up` starts the stack. `aeval run` submits a job, orchestrator dispatches to Ollama, results are stored in TimescaleDB, and `aeval results` retrieves them.

---

### Phase 3: Dashboard (Weeks 7-9)
> Goal: `localhost:8080` shows eval runs, model comparisons, and a release scorecard.

**3.1 — Dashboard scaffold**
- Next.js 14 app with Tailwind CSS
- Dockerfile (multi-stage: build + nginx serve)
- API client to orchestrator (`/api/v1/*`)

**3.2 — Core views**
- **Home** — recent eval runs (table), system health indicators, Ollama model count
- **Run Detail** — per-task score table with pass/fail, confidence intervals, baseline delta
- **Compare** — select 2+ models, select eval suite, render comparison matrix with color-coded significance
- **Models** — Ollama model catalog (family, params, quant, multimodal flag)

**3.3 — Charts**
- Capability radar chart (recharts or chart.js) — spider plot of model scores by category
- Timeline chart — scores over time for a given model + eval
- Comparison table component — reusable across views

**3.4 — Release readiness scorecard**
- Configurable pass/fail thresholds per eval (stored in DB or `suites.yaml`)
- Binary checklist: all evals pass, no regressions, safety gates met
- Green/red status per criterion

**Phase 3 exit criteria:** Dashboard renders at `localhost:8080`, shows real eval data from TimescaleDB, supports model comparison with visual charts, and displays a release readiness scorecard.

---

### Phase 4: Eval Registry (Weeks 10-11)
> Goal: Shared eval library with versioning, search, and suites.

**4.1 — Registry service**
- FastAPI app serving eval definitions from `registry-data/` on disk
- CRUD API: list, get, publish, search (by name, tag, category)
- Eval metadata: `meta.yaml` per eval (description, category, runtime estimate, dataset pointer)

**4.2 — Suites**
- Named collections of evals: `smoke`, `standard`, `pre-release`, `safety`, `full`
- Defined in `suites.yaml` or via API
- `aeval run --suite smoke --model ollama:llama3` runs all evals in the suite

**4.3 — Built-in core evals** (`evals/core/`)
- `factuality_v1.py` — fact-based Q&A with exact match + LLM-judge
- `reasoning_v1.py` — multi-step reasoning with multiple choice
- `safety_v1.py` — refusal detection on adversarial prompts
- `instruction_following_v1.py` — instruction adherence with LLM-judge
- `code_gen_v1.py` — code generation with execution-based scoring

**4.4 — CLI integration**
- `aeval registry search "reasoning"` — search registry
- `aeval registry publish ./my-eval/` — publish to local registry

**Phase 4 exit criteria:** 5+ core evals in the registry. `aeval run --suite smoke` runs all smoke evals. Registry is searchable from CLI.

---

### Phase 5: Adaptive Intelligence (Weeks 12-15)
> Goal: The eval suite monitors its own health and generates new evals to fill gaps.

**5.1 — Capability taxonomy**
- Taxonomy tree stored in DB (id, parent_id, name, description)
- Seed with initial taxonomy from the consolidated design doc (7 top-level categories, ~30 leaf nodes)
- Dashboard: coverage heat map view (eval count + discrimination per node)

**5.2 — Saturation & discrimination monitor**
- Background worker (runs on schedule or triggered)
- Discrimination power: score variance across models / total variance
- Saturation detection: ceiling (>90% of models >95%), floor, noise
- Lifecycle state machine: Active → Watch → Saturated → Archived
- `aeval health` reports saturation rate, coverage gaps, watch list

**5.3 — Eval generator**
- Uses Ollama model (configurable, default: largest available) to generate eval tasks
- Methods: adversarial generation, capability probing, difficulty escalation
- Quality gates: clarity check (LLM-verified), discrimination test (run against 3+ models), contamination scan
- Generated evals stored in registry with `generated: true` metadata

**5.4 — Configuration** (`aeval.yaml`)
- `intelligence.generator_model: ollama:gpt-oss:20b`
- `intelligence.calibration_model: ollama:gemma3`
- `intelligence.schedule.saturation_check: weekly`
- `intelligence.schedule.coverage_check: weekly`

**Phase 5 exit criteria:** Taxonomy seeded. `aeval health` reports coverage and saturation. Intelligence worker can generate candidate eval tasks via Ollama and store them in registry.

---

### Phase 6: CI/CD + Polish (Weeks 16-18)
> Goal: Production-ready for daily use with CI integration.

**6.1 — CI/CD integration**
- `aeval ci --suite pre-merge --fail-on regression --model ollama:brain-analyst-ft`
- Exit codes: 0 = pass, 1 = regression, 2 = system error
- GitHub Actions workflow example (`.github/workflows/model-eval.yml`)
- PR comment formatter (markdown table with pass/fail badges)

**6.2 — Contamination detection**
- `aeval contamination-check --training-manifest ./manifest.json`
- Compare eval dataset hashes against training data file manifest
- Flag results where contamination risk is detected

**6.3 — Post-training regression radar**
- `aeval compare ollama:brain-analyst-ft ollama:llama3 --suite core --format alignment-tax`
- Alignment tax report: what improved, what degraded, net assessment

**6.4 — Documentation**
- README.md with quickstart (10-minute path)
- SDK API reference (auto-generated from docstrings)
- Eval authoring guide (how to write a custom eval)

**Phase 6 exit criteria:** Full CI pipeline works. Documentation complete. System is daily-driver ready.

---

## Technology Choices

| Component | Technology | Rationale |
|---|---|---|
| SDK / CLI | Python 3.11+, Click, httpx, pydantic, rich, scipy | Python-native for ML workflows. Click for CLI. httpx for async Ollama calls. rich for terminal UI. |
| Orchestrator | Python, FastAPI, rq (Redis Queue) | FastAPI for async API. rq for simple Redis-backed job queue (lighter than Celery). |
| Database | TimescaleDB (Postgres 16 + extension) | Time-series hypertables for eval results. Standard Postgres for metadata. Single DB engine. |
| Queue | Redis 7 | Job queue (rq), pub/sub for dashboard live updates, result caching. |
| Dashboard | Next.js 14, Tailwind CSS, Recharts | Modern React framework. Tailwind for fast styling. Recharts for radar/timeline charts. |
| Registry | Python, FastAPI | Lightweight service. File-backed storage for eval definitions. |
| Intelligence | Python, background worker | Scheduled tasks using rq-scheduler or APScheduler. Uses Ollama for generation. |
| Model Backend | Ollama (host-side) | Already installed with 13 models. HTTP API at localhost:11434. No GPU driver needed in containers. |

---

## Key Design Decisions

1. **Ollama on host, not in Docker.** Ollama manages GPU/VRAM natively. Containers reach it via `host.docker.internal:11434`. Simpler than passing GPU devices to containers.

2. **SDK works standalone OR with Docker stack.** Phase 1 delivers a fully functional CLI that talks directly to Ollama — no Docker required. Phase 2 adds orchestrator integration as an enhancement, not a dependency.

3. **TimescaleDB, not separate Postgres + InfluxDB.** One database engine handles both relational metadata and time-series eval results. Reduces operational complexity.

4. **rq over Celery.** Simpler, lighter job queue for a local-first system. Celery's distributed features aren't needed when everything runs on one machine.

5. **LLM-as-judge via local Ollama.** `gpt-oss:20b` (the largest local model) serves as the default judge. No external API calls needed. Fully air-gapped.

---

## Verification & Testing

| Phase | How to verify |
|---|---|
| Phase 1 | `pip install -e ./sdk && aeval models` lists Ollama models. Write a 10-line eval, `aeval run` returns scores with confidence intervals. `aeval compare ollama:brain-analyst-ft ollama:llama3` shows significance table. |
| Phase 2 | `docker compose up -d && aeval status` shows all services healthy. `aeval run` stores results in DB. `aeval results --last` retrieves them. Restart containers — data persists. |
| Phase 3 | Open `localhost:8080` — see recent runs. Click a run — see per-task scores. Compare two models — see radar chart + significance table. |
| Phase 4 | `aeval run --suite smoke --model ollama:gemma3` runs 5+ core evals. `aeval registry search "safety"` finds safety evals. |
| Phase 5 | `aeval health` reports coverage % and saturation rate. Intelligence worker generates candidate evals. Dashboard shows coverage heat map. |
| Phase 6 | `aeval ci --fail-on regression` exits with code 0/1. GitHub Actions workflow runs successfully on self-hosted runner. |

---

## Available Ollama Models (Current)

These models are installed and available for evaluation on this machine:

| Model | Family | Params | Quant | Multimodal | Role in aeval |
|---|---|---|---|---|---|
| `gpt-oss:20b` | gptoss | 20.9B | MXFP4 | No | Default LLM-judge, eval generator |
| `brain-analyst-ft` | llama | 8.0B | Q4_K_M | No | Primary fine-tune eval target |
| `brain-analyst` | llama | 8.0B | Q4_0 | No | Fine-tune baseline |
| `llama3` | llama | 8.0B | Q4_0 | No | Foundation baseline |
| `llama3.2` | llama | 3.2B | Q4_K_M | No | Small model, quantization comparison |
| `llama3.2:3b-instruct-fp16` | llama | 3.2B | F16 | No | F16 quantization reference |
| `gemma3` / `gemma3:4b` | gemma3 | 4.3B | Q4_K_M | No | Cross-architecture comparison, fast calibrator |
| `FintellectAI_gemma` | gemma3 | 4.3B | Q4_K_M | No | Finance fine-tune on Gemma |
| `FintellectAI` | llama | 3.2B | Q4_K_M | No | Finance fine-tune on Llama |
| `llava` / `llava:7b` | llama+clip | 7.0B | Q4_0 | Yes | Multimodal evals |
| `FintellectAI_images` | llama+clip | 7.2B | Q4_0 | Yes | Multimodal fine-tune evals |
