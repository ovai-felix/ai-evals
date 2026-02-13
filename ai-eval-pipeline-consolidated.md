# AI Evaluation Pipeline — Consolidated Product Design
## A Containerized, Local-First Evaluation System for Pre-Training and Post-Training AI Models

**Product Name:** `aeval`

**Design Philosophy:** Three layers, one product. A locally-deployable evaluation platform that runs entirely in Docker containers — no cloud dependency, no SaaS vendor lock-in. Engineers get a Python SDK and CLI for writing evals. The platform orchestrates, stores, and visualizes results. An adaptive intelligence layer keeps the eval suite fresh as models evolve. Ship it with `docker compose up`.

---

## Product Architecture — Three Layers in Containers

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HOST MACHINE                                                           │
│                                                                         │
│  ┌──────────────────────┐    ┌────────────────────────────────────────┐ │
│  │  Ollama (host-side)  │    │  Python SDK + CLI (host-side)         │ │
│  │  localhost:11434     │    │  pip install aeval                     │ │
│  │                      │    │  aeval run / compare / status          │ │
│  │  Models:             │    └──────────────┬─────────────────────────┘ │
│  │  ├ gpt-oss:20b       │                   │ HTTP API                  │
│  │  ├ brain-analyst-ft  │                   ↓                           │
│  │  ├ brain-analyst     │    ┌────────────────────────────────────────┐ │
│  │  ├ gemma3            │    │       aeval (Docker Stack)             │ │
│  │  ├ llama3 / 3.2      │    │                                        │ │
│  │  ├ llava (multimodal)│    │  ┌──────────────────────────────────┐  │ │
│  │  └ FintellectAI*     │    │  │  LAYER 3: ADAPTIVE INTELLIGENCE  │  │ │
│  │         ↑             │    │  │  Taxonomy · Generator · Monitor  │  │ │
│  └─────────┼────────────┘    │  └──────────────────────────────────┘  │ │
│            │                  │                   ↕                     │ │
│   host.docker.internal:11434 │  ┌──────────────────────────────────┐  │ │
│            │                  │  │  LAYER 2: DEVELOPER INTERFACE    │  │ │
│            ↓                  │  │  Eval Registry (localhost:8082)  │  │ │
│  ┌─────────────────────────┐ │  └──────────────────────────────────┘  │ │
│  │  aeval-orchestrator     │ │                   ↕                     │ │
│  │  Dispatches evals to    │ │  ┌──────────────────────────────────┐  │ │
│  │  Ollama models via API  │ │  │  LAYER 1: PLATFORM INFRA         │  │ │
│  │  localhost:8081         │ │  │  Orchestrator · TimescaleDB ·     │  │ │
│  └─────────────────────────┘ │  │  Redis · Dashboard (:8080)       │  │ │
│                               │  └──────────────────────────────────┘  │ │
│                               └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: DEFINE

### Define the Decision
- **Not:** "How do we build an eval pipeline?"
- **Instead:** "How do we give every ML engineer — from solo researcher to platform team — a single `docker compose up` that deploys a complete evaluation system: write evals like pytest, orchestrate them across local GPUs, track results over time, and keep the suite fresh as models evolve?"

### The Problem Space (Unified)
Today's evaluation landscape has three compounding failures:

1. **Fragmentation (Platform problem):** Eval results scattered across notebooks, spreadsheets, Slack. No single system connects pre-training checkpoints to post-training alignment to production behavior. Decision-makers assemble data from 5+ disconnected systems to answer "is this model ready?"

2. **Developer Friction (SDK problem):** Writing evals is hard — custom code for every benchmark, no standardized way to define/version/run/compare. Engineers copy-paste eval scripts, introducing bugs. Evaluation is a phase ("we'll eval later"), not a continuous practice.

3. **Eval Staleness (Intelligence problem):** Static benchmarks decay. Models saturate MMLU, HumanEval, GSM8K. Scores improve without real-world quality improvement. New capabilities (tool use, agentic behavior) emerge months before evals exist to measure them. No one catches blind spots until users complain.

**These three problems reinforce each other.** Without a platform, there's no shared infrastructure for evals. Without an SDK, nobody writes evals consistently. Without adaptive intelligence, even well-written evals go stale. Solving one without the others leaves the system broken.

### Why Local Docker + Ollama?
- **Data Sovereignty:** Model checkpoints and eval datasets never leave your infrastructure. No cloud upload of proprietary model weights.
- **Ollama as the Model Layer:** Ollama already manages model lifecycle (pull, run, serve, quantize) and exposes a standard API at `localhost:11434`. aeval doesn't reinvent model serving — it delegates to Ollama and focuses on evaluation. If it runs in Ollama, aeval can eval it.
- **GPU Access:** Ollama handles GPU scheduling and VRAM management for model inference. aeval containers access Ollama via HTTP — no direct GPU driver dependency in the eval stack.
- **Reproducibility:** `docker compose up` produces identical eval environment on any machine. Ollama model tags (e.g., `llama3.2:3b-instruct-fp16`) pin exact model versions for deterministic eval runs.
- **Offline Operation:** Run evals on air-gapped machines, on-prem clusters, or laptops. No internet dependency for core functionality. Ollama models are pre-downloaded and served locally.
- **Cost:** Zero per-run cloud charges. Eval compute cost = electricity + hardware depreciation. No API fees — every model call is local.

### Mission, Vision & North Star
- **Mission:** Make AI evaluation a continuous, automated, and self-improving discipline — deployable anywhere with a single command.
- **Vision:** Every model change is automatically validated against a comprehensive, adaptive eval suite before it reaches any user — and the entire system runs on your own hardware.
- **North Star Metric:** **Eval-Gated Model Changes** — percentage of model changes (commits, experiments, releases) that pass through automated eval verification before deployment. Target: >90%.

---

## Phase 2: INSTRUMENT

### Container Architecture

```yaml
# docker-compose.yml
services:

  # --- Layer 1: Platform Infrastructure ---

  aeval-orchestrator:
    build: ./orchestrator
    ports: ["8081:8081"]
    extra_hosts:
      - "host.docker.internal:host-gateway"   # reach Ollama on host
    environment:
      OLLAMA_HOST: http://host.docker.internal:11434
      AEVAL_MODEL_BACKEND: ollama              # default model backend
    volumes:
      - ./models:/models:ro          # mount local model checkpoints (non-Ollama)
      - ./evals:/evals               # eval definitions
      - ./datasets:/datasets:ro      # eval datasets
      - aeval-results:/results       # persistent results
    depends_on: [aeval-db, aeval-queue]

  aeval-db:
    image: timescale/timescaledb:latest-pg16
    ports: ["5432:5432"]
    volumes:
      - aeval-pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: aeval
      POSTGRES_USER: aeval
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password

  aeval-queue:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - aeval-redis:/data

  aeval-dashboard:
    build: ./dashboard
    ports: ["8080:8080"]            # main UI at localhost:8080
    depends_on: [aeval-db]

  # --- Layer 2: Developer Interface ---

  aeval-registry:
    build: ./registry
    ports: ["8082:8082"]
    volumes:
      - ./registry-data:/registry   # shared eval definitions
      - ./evals:/evals:ro
    depends_on: [aeval-db]

  # --- Layer 3: Adaptive Intelligence ---

  aeval-intelligence:
    build: ./intelligence
    extra_hosts:
      - "host.docker.internal:host-gateway"   # reach Ollama for eval generation
    environment:
      OLLAMA_HOST: http://host.docker.internal:11434
    volumes:
      - ./evals:/evals
      - ./datasets:/datasets
      - aeval-results:/results:ro
    depends_on: [aeval-db, aeval-orchestrator]

volumes:
  aeval-pgdata:
  aeval-redis:
  aeval-results:
```

> **Note: Ollama runs on the host, not in a container.** aeval containers reach Ollama via `host.docker.internal:11434`. On macOS this works out of the box. On Linux, the `extra_hosts` directive maps it to the host gateway. Ollama manages its own GPU scheduling and model loading — aeval never needs direct GPU access for inference, only for the intelligence layer's eval generation tasks.

### Container & Service Responsibilities

| Service | Runs In | Role | GPU | Port |
|---|---|---|---|---|
| **Ollama** | Host (native) | Model serving — loads, runs, and manages all models. Handles VRAM, quantization, and inference. The single source of truth for available models. | Yes (host GPU) | 11434 |
| `aeval-orchestrator` | Docker | Schedules eval runs, dispatches prompts to Ollama via API, manages job queue, retries | No (uses Ollama) | 8081 |
| `aeval-db` | Docker (TimescaleDB) | Stores all eval results, run metadata, time-series scores, taxonomy, audit logs | No | 5432 |
| `aeval-queue` | Docker (Redis) | Job queue for eval tasks, pub/sub for real-time dashboard updates, result caching | No | 6379 |
| `aeval-dashboard` | Docker (React/Next.js) | Web UI for results exploration, comparisons, trend charts, release scorecard | No | 8080 |
| `aeval-registry` | Docker (Python/FastAPI) | Shared eval definition library, versioning, search, metadata | No | 8082 |
| `aeval-intelligence` | Docker (Python) | Capability taxonomy, saturation detection, eval generation, discrimination scoring. Uses Ollama for LLM-powered generation tasks. | No (uses Ollama) | — |

### Universal Event Schema

| Event Type | Fields | Stored In |
|---|---|---|
| **Eval Run** | run_id, model_id, checkpoint, eval_suite, stage (pre/post/prod), trigger (manual/CI/scheduled), timestamp, container_id, gpu_id | Postgres |
| **Eval Task** | task_id, benchmark_name, category, num_samples, prompt_template_version, discrimination_power, saturation_score | Postgres |
| **Eval Result** | task_id, run_id, score, confidence_interval, baseline_delta, pass/fail, latency_p50/p99, tokens_used | TimescaleDB (time-series) |
| **Task Lifecycle** | task_id, created_date, generation_method, active_status, saturation_score, retirement_date | Postgres |
| **System Health** | container_id, gpu_utilization, queue_depth, job_success_rate, disk_usage | TimescaleDB |

### Volume Mounts & Data Locations

```
Host Filesystem                    Container Mount         Purpose
─────────────────────────────────────────────────────────────────────
~/.ollama/models/            →     (host-only)             Ollama model weights (GGUF)
./models/                    →     /models (read-only)     Non-Ollama checkpoints (.safetensors, HF)
./evals/                     →     /evals                  Eval definitions (Python files)
./datasets/                  →     /datasets (read-only)   Eval datasets (versioned)
./registry-data/             →     /registry               Shared eval library
aeval-pgdata (Docker vol)    →     /var/lib/postgresql      All structured data
aeval-results (Docker vol)   →     /results                Raw eval outputs, logs
```

> Ollama models live in `~/.ollama/models/` on the host and are never mounted into Docker containers. aeval accesses them exclusively through Ollama's HTTP API.

### Who Uses This Product

| Persona | Primary Need | Primary Interface |
|---|---|---|
| **ML Researcher** | "Did this checkpoint improve?" Quick, ad-hoc eval of experimental models | `aeval run` CLI, notebook integration |
| **ML Engineer** | Automated eval in training CI/CD. No model merges without passing evals | SDK in Python, CI hooks, `aeval ci` |
| **Alignment Engineer** | "Did RLHF improve helpfulness without regressing safety?" | Regression radar, alignment tax dashboard |
| **Safety Researcher** | Adversarial eval generation, red-team coverage | Intelligence layer, adversarial generator |
| **Platform Engineer** | "Are evals running reliably? Are containers healthy?" | System health dashboard, `docker compose logs` |
| **Technical Lead / PM** | "Is this model ready to ship?" | Release readiness scorecard at `localhost:8080` |

---

## Phase 3: OBSERVE

### Behavioral Dimensions

1. **Volume:** Eval runs per day. Are teams running evals on every checkpoint, or sporadically? Container utilization — are GPUs idle or saturated?
2. **Conversion:** What % of eval runs produce a ship/hold decision? If evals run but don't inform decisions, the system is noise. What % of `pip install aeval` leads to a first eval run within 24 hours?
3. **Frequency:** How often are eval suites updated? Dashboard DAU. Stale evals + stale dashboard = false confidence.
4. **Friction:** Where do evals fail? Common local-Docker issues: GPU OOM, dataset too large for disk, container crashes, slow cold starts, confusing score interpretation.
5. **Freshness:** What % of active evals maintain discrimination power >0.15? Median eval task age. Saturation rate.

### Qualitative Context
- **Researcher:** "I don't trust benchmark X because it was contaminated." → Contamination detection in intelligence layer.
- **Engineer:** "Setting up eval infrastructure takes 2 days per project." → `aeval init` scaffolding + Docker handles infra.
- **Engineer:** "I can't tell if 0.82 vs 0.81 is meaningful." → Built-in statistical significance.
- **Safety team:** "We red-team manually but can't keep up." → Automated adversarial eval generation.
- **PM:** "I assemble data from 5 systems to decide if we can ship." → Release readiness scorecard.
- **Leadership:** "How do I know our eval suite isn't missing something?" → Coverage heat map + gap analysis.

### Root Cause Diagnosis
- **Symptom:** "Teams ship models without running full eval suites."
- **Root Causes:** (1) Full suite takes too long on available GPUs. (2) Writing evals is hard. (3) Results are scattered and hard to interpret. (4) Saturated benchmarks give false confidence.
- **Levers:** (1) Tiered eval system — smoke tests in 30 min, full suite only for releases. (2) Pytest-like SDK — eval definitions in 10 lines. (3) Unified dashboard at `localhost:8080`. (4) Adaptive intelligence retires stale evals automatically.

---

## Phase 4: DEVELOP

### Layer 1: Platform Infrastructure

#### Eval Orchestrator (`aeval-orchestrator`)
The backbone — schedules, dispatches, and manages eval runs across local GPUs.

- **Tiered Eval System:**

  | Tier | Trigger | Duration | Scope | Gate |
  |---|---|---|---|---|
  | **Smoke** | `aeval run --tier smoke` or every N training steps | < 30 min | Core benchmarks (10 tasks) | Continue / pause training |
  | **Standard** | `aeval run --tier standard` or post-training experiment | 2-4 hours | Full benchmark suite (100+ tasks) | Merge / reject alignment change |
  | **Comprehensive** | `aeval run --tier full` or release candidate | 12-24 hours | Full suite + LLM-judge + adversarial + regression radar | Ship / hold release |

- **Model Inference via Ollama:**
  - All model inference is delegated to Ollama on the host. The orchestrator sends prompts via HTTP, not GPU calls.
  - Ollama manages GPU memory, model loading/unloading, and quantization. aeval never competes with Ollama for GPU resources.
  - **Sequential model evaluation:** When comparing multiple models, the orchestrator requests them one at a time. Ollama unloads the previous model and loads the next automatically.
  - **Concurrency tuning:** For parallel eval across models, configure Ollama's `OLLAMA_NUM_PARALLEL` or use `OLLAMA_MAX_LOADED_MODELS` to keep multiple models warm.
  - **Fallback adapters:** For models not in Ollama (e.g., `.safetensors` checkpoints), the orchestrator can dispatch to vLLM, TGI, or direct HuggingFace inference as configured in `aeval.yaml`.

- **Job Queue (Redis-backed):**
  - Persistent job queue survives container restarts.
  - Priority lanes: smoke (high), standard (medium), comprehensive (low), generated-eval-calibration (background).
  - Dead letter queue for failed tasks with automatic retry (3x) and alerting.
  - Real-time job status via `aeval status` CLI command.

#### Results Store (`aeval-db`)
TimescaleDB (Postgres extension) for both relational metadata and time-series eval scores.

- **Schema Design:**
  - `models` — model registry (id, name, checkpoint_path, stage, metadata)
  - `eval_definitions` — eval definitions (id, name, version, category, code_hash, dataset_hash)
  - `eval_runs` — run metadata (id, model_id, suite, tier, trigger, status, started_at, finished_at)
  - `eval_results` — individual task scores (run_id, task_id, score, ci_lower, ci_upper, baseline_delta, p_value) — TimescaleDB hypertable, partitioned by time
  - `taxonomy_nodes` — capability taxonomy tree
  - `task_lifecycle` — eval task health (discrimination_power, saturation_score, status)

- **Data Retention:** All data persists in Docker volume `aeval-pgdata`. Survives `docker compose down`. Explicit `docker volume rm` to delete.

#### Dashboard (`aeval-dashboard`)
Web UI at `localhost:8080` — the single pane of glass.

- **Views:**
  - **Home:** Recent eval runs, system health, alerts.
  - **Checkpoint Timeline:** Horizontal timeline of checkpoints with scores overlaid. Click to drill into per-task results.
  - **Capability Radar:** Spider chart of model performance across capability dimensions. Overlay two models for comparison.
  - **Comparison Matrix:** Select N models x M evals → color-coded score matrix with significance indicators.
  - **Release Readiness Scorecard:** Binary pass/fail checklist — benchmarks met, safety gates passed, no regressions, within latency SLA.
  - **Coverage Heat Map:** Taxonomy tree with eval density and discrimination power per node. Red = gap. Green = healthy.
  - **Eval Health:** Saturation alerts, discrimination trends, eval lifecycle status.
  - **System:** Container health, GPU utilization, queue depth, disk usage.

- **No Authentication Required:** Local-only deployment. Dashboard accessible only from the host machine. For team access, put behind a reverse proxy with auth.

---

### Layer 2: Developer Interface

#### Python SDK (`pip install aeval`)

The SDK runs on the host (not in a container) and communicates with the orchestrator via HTTP API.

```python
# Install: pip install aeval
# Configure: aeval init (creates aeval.yaml, connects to local Docker stack + Ollama)

from aeval import Eval, Dataset, Scorer, Model

# --- Load models from Ollama (primary interface) ---

model = Model.from_ollama("brain-analyst-ft")           # chat model
base  = Model.from_ollama("llama3")                      # base model for comparison
judge = Model.from_ollama("gpt-oss:20b")                 # use largest local model as judge

# --- Define an eval (decorator-based, pytest-style) ---

@Eval(name="factuality-v2", tags=["safety", "factuality"])
def factuality_eval(model: Model):
    dataset = Dataset.load("factuality-qa-v3")  # versioned, from local ./datasets/

    results = model.generate(dataset.prompts)

    scores = Scorer.factuality(
        predictions=results,
        references=dataset.references,
        method="llm-judge",
        judge_model="ollama:gpt-oss:20b",   # use a local Ollama model as judge
    )

    return scores

# --- Define a fine-tune regression eval ---

@Eval(name="brain-analyst-regression-v1", tags=["fine-tune", "regression"])
def finetune_regression(model: Model):
    dataset = Dataset.load("brain-analysis-qa-v1")
    results = model.generate(dataset.prompts)
    return Scorer.domain_accuracy(results, dataset.references, domain="neuroscience")

# --- Define a safety eval ---

@Eval(name="jailbreak-resistance-v1", tags=["safety", "adversarial"])
def jailbreak_eval(model: Model):
    dataset = Dataset.load("adversarial-jailbreaks-v2")
    results = model.generate(dataset.prompts)
    scores = Scorer.safety_refusal(predictions=results, expected_refusals=dataset.labels)
    return scores

# --- Define a multimodal eval (for llava / vision models) ---

@Eval(name="image-understanding-v1", tags=["multimodal", "vision"])
def vision_eval(model: Model):
    dataset = Dataset.load("visual-qa-v1")  # contains image paths + questions
    results = model.generate(
        dataset.prompts,
        images=dataset.images,              # Ollama handles image input natively
    )
    return Scorer.exact_match(results, dataset.references)

# --- Define a pre-training checkpoint probe ---

@Eval(name="reasoning-probe-v1", tags=["pre-training", "reasoning"])
def reasoning_probe(model: Model):
    dataset = Dataset.load("reasoning-probes-v1")
    results = model.complete(dataset.prompts)  # completion mode, not chat
    scores = Scorer.multiple_choice(predictions=results, answers=dataset.answers)
    return scores
```

**Key SDK Features:**
- **Ollama-Native Model Adapter:** `Model.from_ollama("model-name")` connects to any model served by Ollama. Auto-discovers available models via `GET /api/tags`. Supports chat (`model.generate`) and completion (`model.complete`) modes. Handles multimodal input (images) for vision models like `llava`.
- **Declarative Eval Definition:** `@Eval` decorator. Define what to evaluate, the orchestrator handles how.
- **Built-in Scorers:** Exact match, BLEU/ROUGE, LLM-as-judge (using local Ollama models as judges), embedding similarity, code execution, safety refusal, multiple choice. Extensible with custom scorers.
- **Local LLM-as-Judge:** Use your largest local model (e.g., `gpt-oss:20b`) as an eval judge — no external API calls needed. Specify `judge_model="ollama:model-name"` in any scorer that supports LLM judging.
- **Model Adapters:** Unified `Model` interface for Ollama models (primary), local checkpoints (`.safetensors`, `.gguf`), other inference servers (vLLM, TGI), or external API endpoints as fallback.
- **Dataset Management:** Versioned datasets in `./datasets/` with integrity hashes. Automatic contamination checking against registered training data manifests.
- **Statistical Rigor by Default:** Every score returns confidence intervals, significance tests vs. baseline, and effect size. No guessing whether 0.82 vs 0.81 matters.

#### CLI (`aeval`)

```bash
# Initialize project — auto-detects Docker stack + Ollama
$ aeval init
Created aeval.yaml.
Docker stack:  ✓ detected at localhost:8081
Ollama:        ✓ detected at localhost:11434 (13 models available)

# --- Discover available Ollama models ---
$ aeval models
┌──────────────────────────────┬──────────┬───────────┬──────────┬──────────────┐
│ Model                        │ Family   │ Params    │ Quant    │ Multimodal   │
├──────────────────────────────┼──────────┼───────────┼──────────┼──────────────┤
│ gpt-oss:20b                  │ gptoss   │ 20.9B     │ MXFP4    │ no           │
│ brain-analyst-ft             │ llama    │ 8.0B      │ Q4_K_M   │ no           │
│ brain-analyst                │ llama    │ 8.0B      │ Q4_0     │ no           │
│ FintellectAI_gemma           │ gemma3   │ 4.3B      │ Q4_K_M   │ no           │
│ gemma3                       │ gemma3   │ 4.3B      │ Q4_K_M   │ no           │
│ llava                        │ llama    │ 7.0B      │ Q4_0     │ yes (CLIP)   │
│ FintellectAI_images          │ llama    │ 7.2B      │ Q4_0     │ yes (CLIP)   │
│ FintellectAI                 │ llama    │ 3.2B      │ Q4_K_M   │ no           │
│ llama3.2                     │ llama    │ 3.2B      │ Q4_K_M   │ no           │
│ llama3.2:3b-instruct-fp16   │ llama    │ 3.2B      │ F16      │ no           │
│ llama3                       │ llama    │ 8.0B      │ Q4_0     │ no           │
│ gemma3:4b                    │ gemma3   │ 4.3B      │ Q4_K_M   │ no           │
└──────────────────────────────┴──────────┴───────────┴──────────┴──────────────┘

# --- Run a single eval against an Ollama model ---
$ aeval run factuality-v2 --model ollama:brain-analyst-ft
Running factuality-v2 on brain-analyst-ft (via Ollama)...
━━━━━━━━━━━━━━━━━━━━━ 100% ━━━━━━━━━━━━━━━━━━━━━
  factuality_score: 0.847 (±0.023, 95% CI)
  vs. baseline:     +0.031 (p=0.003, significant)
  Status:           PASS (threshold: 0.80)
  Dashboard:        http://localhost:8080/runs/run-2026-0212-001

# --- Compare fine-tune vs base model ---
$ aeval compare ollama:brain-analyst-ft ollama:brain-analyst --suite core
┌─────────────────┬───────────┬───────────┬──────────┬─────────┐
│ Eval            │ ft        │ base      │ Delta    │ Sig?    │
├─────────────────┼───────────┼───────────┼──────────┼─────────┤
│ factuality      │ 0.847     │ 0.791     │ +0.056   │ **yes** │
│ reasoning       │ 0.723     │ 0.735     │ -0.012   │ no      │
│ safety          │ 0.981     │ 0.994     │ -0.013   │ *yes*   │
│ code-gen        │ 0.681     │ 0.697     │ -0.016   │ no      │
│ instruction     │ 0.891     │ 0.842     │ +0.049   │ **yes** │
│ domain-neuro    │ 0.924     │ 0.603     │ +0.321   │ **yes** │
└─────────────────┴───────────┴───────────┴──────────┴─────────┘
Fine-tune improved domain + instruction. Minor safety regression. Investigate.

# --- Run same eval across all models in a family ---
$ aeval run reasoning-v2 --model ollama:llama3 ollama:llama3.2 ollama:brain-analyst-ft
Running reasoning-v2 across 3 models (sequential via Ollama)...

# --- Compare quantization impact ---
$ aeval compare ollama:llama3.2 ollama:llama3.2:3b-instruct-fp16 --suite core
# Same model, Q4_K_M vs F16 — does quantization degrade quality?

# --- Run multimodal eval on vision models ---
$ aeval run image-understanding-v1 --model ollama:llava
Running image-understanding-v1 on llava (multimodal via Ollama)...

# --- Run a tiered suite ---
$ aeval run --suite pre-release --tier standard --model ollama:gpt-oss:20b
Running 47 evals via Ollama (gpt-oss:20b, 20.9B params)...
━━━━━━━━━━━━━━━━━━━━━ 100% (2h 14m) ━━━━━━━━━━━━━━━━━━━━━
  PASS: 44/47 | FAIL: 2/47 | SKIP: 1/47
  Dashboard:   http://localhost:8080/runs/run-2026-0212-002

# --- CI/CD mode ---
$ aeval ci --suite pre-merge --fail-on regression --model ollama:brain-analyst-ft

# --- Check system health ---
$ aeval status
Orchestrator:  ✓ running (localhost:8081)
Ollama:        ✓ running (localhost:11434, 13 models, gpt-oss:20b loaded)
Database:      ✓ running (localhost:5432, 2.3 GB used)
Queue:         ✓ running (3 jobs pending, 1 active)
Dashboard:     ✓ running (localhost:8080)
Registry:      ✓ running (localhost:8082, 142 evals)
Intelligence:  ✓ running (using ollama:gpt-oss:20b for generation)

# --- Eval suite health ---
$ aeval health
Active evals:     142
Discriminative:   128 (90.1%) ✓
Watch list:       9 (6.3%)
Saturated:        5 (3.5%) — retirement queued
Coverage:         87.3% of taxonomy (target: 90%)
Gaps:             Counterfactual Reasoning, Video Understanding, Multi-Tool Orchestration
```

#### CI/CD Integration

```yaml
# .github/workflows/model-eval.yml
name: Model Evaluation
on:
  push:
    paths: ['models/**', 'training/**']
jobs:
  eval:
    runs-on: [self-hosted, gpu]     # runs on your GPU machine
    steps:
      - uses: actions/checkout@v4
      - name: Start eval stack
        run: docker compose up -d
      - name: Run pre-merge eval suite
        run: |
          pip install aeval
          aeval ci --suite pre-merge --fail-on regression \
                   --model ./models/${{ github.sha }} \
                   --report github-pr-comment
```

**CI Features:**
- **Pre-Merge Gate:** Regressions block merge. Configurable thresholds per eval.
- **PR Comments:** Eval results posted as GitHub/GitLab PR comments with score tables, pass/fail badges, and links to the local dashboard.
- **Exit Codes:** `0` = pass, `1` = regression detected, `2` = eval system error. Standard CI integration.

#### Eval Registry (`aeval-registry`)

Containerized shared library of eval definitions.

```
registry/
├── core/                    # Platform-maintained, mandatory
│   ├── factuality-v3/
│   │   ├── eval.py          # eval definition
│   │   ├── dataset.json     # versioned dataset (or pointer to ./datasets/)
│   │   ├── meta.yaml        # description, category, runtime, compute req
│   │   └── CHANGELOG.md
│   ├── reasoning-v2/
│   ├── safety-v4/
│   └── code-gen-v2/
├── community/               # Team contributions
│   ├── medical-qa-v1/
│   ├── legal-reasoning-v1/
│   └── multilingual-v2/
└── custom/                  # Team-private
    └── [team-specific]/
```

- **Eval Suites:** Named collections — `pre-merge` (fast, 10 core evals), `pre-release` (comprehensive, 100+ evals), `safety` (all safety evals), `full` (everything).
- **Semantic Versioning:** Breaking changes = major bump. Old versions remain runnable. `aeval run factuality-v2` vs `factuality-v3`.
- **Search:** `aeval registry search "reasoning"` — find evals by name, tag, or capability taxonomy node.
- **Publish:** `aeval registry publish ./my-eval/` — adds to local registry. Available to all users of this Docker stack.

---

### Layer 3: Adaptive Intelligence

#### Capability Taxonomy Engine

A structured, living map of what the model should be able to do. Stored in `aeval-db`, visualized on the dashboard.

```
AI Capability Taxonomy
├── Reasoning
│   ├── Logical Deduction
│   ├── Mathematical Reasoning
│   ├── Causal Reasoning
│   ├── Analogical Reasoning
│   ├── Multi-Step Planning
│   └── Counterfactual Reasoning
├── Knowledge & Factuality
│   ├── World Knowledge (by domain)
│   ├── Temporal Reasoning
│   ├── Source Attribution
│   └── Uncertainty Calibration
├── Language & Communication
│   ├── Instruction Following (simple → complex)
│   ├── Long-Form Generation
│   ├── Summarization
│   ├── Translation / Multilingual
│   └── Tone & Style Adaptation
├── Code & Tool Use
│   ├── Code Generation (by language)
│   ├── Code Debugging
│   ├── API / Tool Calling
│   ├── Multi-Tool Orchestration
│   └── Agentic Task Completion
├── Multimodal
│   ├── Image Understanding
│   ├── Image Generation
│   ├── Audio Understanding
│   ├── Video Understanding
│   └── Cross-Modal Reasoning
├── Safety & Alignment
│   ├── Harmful Content Refusal
│   ├── Bias & Fairness
│   ├── Privacy Protection
│   ├── Jailbreak Resistance
│   └── Honesty & Calibration
└── Meta-Cognitive
    ├── Self-Correction
    ├── Uncertainty Expression
    ├── Asking Clarifying Questions
    └── Knowing Limitations
```

- **Coverage Heat Map (Dashboard):** Each taxonomy node shows: number of active evals, average discrimination power, saturation risk. Red = uncovered or saturated. Green = well-evaluated and discriminative.
- **Gap Detection:** `aeval health` reports taxonomy nodes with <2 active discriminative evals. Triggers eval generation.

#### Saturation & Discrimination Monitor

Runs continuously in `aeval-intelligence` container. Monitors every active eval task.

- **Discrimination Power:** Variance in scores across different-quality models / total variance. Low discrimination = eval is too easy, too hard, or too noisy.
- **Saturation Detection:**
  - Ceiling: >90% of models score >95% → too easy.
  - Floor: >90% score <10% → too hard.
  - Noise: within-model variance > between-model variance → measuring noise.

- **Automated Lifecycle:**

  | State | Trigger | Action |
  |---|---|---|
  | **Active** | Discrimination > 0.15 | Include in standard suite |
  | **Watch** | Discrimination 0.08-0.15 | Flag, consider difficulty escalation |
  | **Saturated** | Discrimination < 0.08 for 3 months | Retire, trigger replacement generation |
  | **Archived** | Retired | Historical comparison only |

- **Saturation Forecast:** Predicts which evals will saturate in 3-6 months. Generates replacements proactively.

#### Adaptive Eval Generator

AI-powered eval task creation, running in the `aeval-intelligence` container. Uses Ollama models for all generation and quality-gate tasks — no external API needed.

| Method | Input | Ollama Model Used | Output | Use Case |
|---|---|---|---|---|
| **Adversarial Generation** | Current model + failure patterns | `gpt-oss:20b` (generator) | Hard eval cases probing weaknesses | Safety, robustness |
| **Capability Probing** | Taxonomy gap + capability description | `gpt-oss:20b` (generator) | Eval tasks for uncovered capabilities | Coverage expansion |
| **Difficulty Escalation** | Saturated eval + model performance | `gemma3` (fast calibrator) | Harder versions of existing evals | Maintaining discrimination |
| **Cross-Domain Transfer** | Eval from domain A + domain B spec | `gpt-oss:20b` (generator) | Analogous eval adapted to new domain | Rapid expansion |

- **Quality Gates (automated, via Ollama):**
  1. Clarity check — is the task unambiguous? (verified by `gemma3` — fast, cheap)
  2. Difficulty calibration — tested against 3+ Ollama models of varying capability, must discriminate
  3. Ground truth validation — verifiable correct answer or clear criteria
  4. Contamination check — scanned against registered training data manifests

- **Generation Cadence:**
  - Continuous: adversarial generation runs daily (via Ollama, background priority), 50-100 candidates
  - Triggered: coverage gap detection triggers bulk generation
  - Scheduled: quarterly full taxonomy review

#### Pre-Training Integration

- **Checkpoint Probes:** Lightweight evals for base models (no instruction tuning needed). Test raw capability emergence using completion-mode, not chat-mode.
- **Scaling Law Predictions:** Given scores at checkpoints N, 2N, 4N — predict performance at 10N. Identify plateauing capabilities before investing full training compute.
- **Early Termination Signals:** If probes show a run isn't developing expected capabilities, recommend early termination.

#### Post-Training Regression Radar

- **Alignment Tax Calculator:** Quantify the capability cost of RLHF/DPO. What improved (helpfulness, safety) and what degraded (factuality, reasoning)? Make the tradeoff explicit.
- **Silent Regression Detection:** Compare post-training vs. pre-training across full taxonomy. Flag any capability that drops >2%.
- **Reward Hacking Detection:** Reward model scores diverging from human preference and objective metrics = hacking.
- **Multi-Turn Regression:** Evaluate 5+ turn conversations. Alignment tuning often degrades multi-turn coherence — invisible to single-turn evals.

---

### Quickstart: From Zero to First Eval in 10 Minutes

**Prerequisites:** Ollama installed and running with at least one model pulled.

```bash
# 1. Clone and start the stack (2 minutes)
git clone https://github.com/aeval/aeval.git
cd aeval
docker compose up -d

# 2. Install the SDK (30 seconds)
pip install aeval
aeval init   # auto-detects Docker stack + Ollama at localhost:11434

# 3. Verify Ollama models are visible (10 seconds)
aeval models   # should list all your Ollama models

# 4. Write your first eval (3 minutes)
cat > evals/my_first_eval.py << 'EOF'
from aeval import Eval, Dataset, Scorer

@Eval(name="my-factuality-test", tags=["factuality"])
def my_eval(model):
    dataset = Dataset.from_jsonl("datasets/my-questions.jsonl")
    results = model.generate(dataset.prompts)
    return Scorer.exact_match(results, dataset.references)
EOF

# 5. Run it against any Ollama model (5 minutes)
aeval run my-factuality-test --model ollama:llama3

# 6. Compare your fine-tune against the base (10 minutes)
aeval compare ollama:brain-analyst-ft ollama:llama3 --eval my-factuality-test

# 7. View results
open http://localhost:8080   # dashboard
# or
aeval results my-factuality-test --last
```

---

### Ollama Integration — First-Class Model Backend

Ollama is the primary model backend for `aeval`. Every Ollama model is automatically available for evaluation without additional configuration.

#### How It Works

```
SDK / CLI                    Orchestrator (Docker)              Ollama (Host)
─────────                    ─────────────────────              ─────────────
aeval run                    Receives eval job                  Serves model
  --model ollama:llama3  →   Reads eval definition          →  POST /api/chat
                             Sends prompts to Ollama            Returns completions
                             Collects responses              ←  (streaming or batch)
                             Scores with Scorer
                             Stores results in TimescaleDB
                             Updates dashboard
```

- **Auto-Discovery:** `aeval models` calls `GET /api/tags` on Ollama and displays all available models with family, parameter count, quantization level, and multimodal support.
- **Model Loading:** Ollama loads models into VRAM on first request and keeps them warm. aeval respects Ollama's model management — it never loads/unloads models directly.
- **Concurrency:** Ollama handles one model at a time by default. When comparing multiple models, aeval runs them sequentially (unloading/loading between models). For parallel evals across models, configure Ollama with `OLLAMA_NUM_PARALLEL` or run multiple Ollama instances.
- **Timeouts:** Large models (20B+) generating long responses may need extended timeouts. Configurable via `aeval.yaml`:
  ```yaml
  ollama:
    host: http://localhost:11434
    timeout: 300           # seconds per request (default: 120)
    keep_alive: 5m         # how long Ollama keeps model in VRAM after last request
  ```

#### Eval Workflows for Your Models

**1. Fine-Tune Regression Testing**

Compare `brain-analyst-ft` against its base (`brain-analyst`) and the original foundation (`llama3`) to measure what fine-tuning gained and lost.

```bash
# Three-way comparison: fine-tune vs base-tuned vs foundation
$ aeval compare ollama:brain-analyst-ft ollama:brain-analyst ollama:llama3 \
    --suite core --output-format table

┌─────────────────┬──────────────┬──────────────┬──────────┬───────────────┐
│ Eval            │ brain-ft     │ brain-base   │ llama3   │ Best          │
├─────────────────┼──────────────┼──────────────┼──────────┼───────────────┤
│ domain-neuro    │ 0.924 ██████ │ 0.603 ███    │ 0.312    │ brain-ft ✓    │
│ instruction     │ 0.891 █████  │ 0.842 █████  │ 0.873    │ brain-ft ✓    │
│ factuality      │ 0.847 █████  │ 0.791 ████   │ 0.816    │ brain-ft ✓    │
│ reasoning       │ 0.723 ████   │ 0.735 ████   │ 0.748    │ llama3        │
│ safety          │ 0.981 █████  │ 0.994 █████  │ 0.996    │ llama3        │
│ code-gen        │ 0.681 ███    │ 0.697 ████   │ 0.712    │ llama3        │
└─────────────────┴──────────────┴──────────────┴──────────┴───────────────┘
Alignment Tax: brain-analyst-ft gained +0.321 domain, +0.049 instruction
               Lost -0.025 reasoning, -0.015 safety, -0.031 code-gen
```

**2. Cross-Architecture Comparison**

Evaluate which model family performs best on your specific tasks.

```bash
# Compare across families at different sizes
$ aeval compare ollama:gpt-oss:20b ollama:llama3 ollama:gemma3 \
    --suite core --judge ollama:gpt-oss:20b

# Compare your custom Gemma fine-tune against base Gemma
$ aeval compare ollama:FintellectAI_gemma ollama:gemma3 --suite finance
```

**3. Quantization Impact Analysis**

Same model, different quantizations — statistically measure quality degradation.

```bash
# llama3.2 Q4_K_M vs F16 — does 4-bit quantization degrade quality?
$ aeval compare ollama:llama3.2 ollama:llama3.2:3b-instruct-fp16 \
    --suite core --output-format detailed

# Reports: per-eval score delta, statistical significance,
# latency difference, and tokens/second comparison
```

**4. Multimodal Evaluation**

Evaluate vision capabilities of models with CLIP support.

```bash
# Eval image understanding on llava
$ aeval run image-understanding-v1 --model ollama:llava

# Compare your multimodal fine-tune against base llava
$ aeval compare ollama:FintellectAI_images ollama:llava --suite multimodal
```

```python
# SDK: multimodal eval definition
@Eval(name="visual-qa-v1", tags=["multimodal", "vision"])
def visual_qa(model: Model):
    dataset = Dataset.load("visual-qa-v1")
    results = model.generate(
        dataset.prompts,
        images=dataset.images,    # Ollama handles image encoding via CLIP
    )
    return Scorer.llm_judge(
        results, dataset.references,
        judge_model="ollama:gpt-oss:20b",  # text-only judge evaluates answer quality
    )
```

**5. Using Local Models as Eval Judges**

No external API needed — use your largest local model as the LLM-as-judge scorer.

```python
# Use gpt-oss:20b (your largest model) as the judge for all LLM-scored evals
@Eval(name="helpfulness-v1", tags=["quality"])
def helpfulness_eval(model: Model):
    dataset = Dataset.load("helpfulness-prompts-v1")
    results = model.generate(dataset.prompts)
    return Scorer.llm_judge(
        predictions=results,
        references=dataset.references,
        judge_model="ollama:gpt-oss:20b",
        rubric="Rate the response on helpfulness (1-5). Consider accuracy, "
               "completeness, and clarity.",
    )
```

```bash
# CLI shorthand: set default judge model
$ aeval config set judge_model ollama:gpt-oss:20b

# Now all LLM-judge evals use gpt-oss:20b automatically
$ aeval run helpfulness-v1 --model ollama:brain-analyst-ft
```

**6. Adaptive Intelligence with Local Models**

The intelligence layer uses Ollama models for eval generation and quality gates.

```yaml
# aeval.yaml — intelligence layer configuration
intelligence:
  generator_model: ollama:gpt-oss:20b     # generates new eval tasks
  calibration_model: ollama:gemma3         # fast model for quality gate checks
  adversarial_model: ollama:llama3         # generates adversarial prompts
  schedule:
    adversarial: daily                      # daily adversarial probe generation
    coverage_check: weekly                  # weekly taxonomy gap analysis
    saturation_check: weekly                # weekly discrimination power audit
```

#### Model Compatibility Matrix

| Model | Chat Eval | Completion Eval | Multimodal Eval | Judge Capable | Notes |
|---|---|---|---|---|---|
| `gpt-oss:20b` | Yes | Yes | No | **Best** (largest) | Recommended as default judge |
| `brain-analyst-ft` | Yes | Yes | No | Yes | Primary fine-tune eval target |
| `brain-analyst` | Yes | Yes | No | Yes | Fine-tune baseline |
| `llama3` | Yes | Yes | No | Yes | Foundation baseline for brain-analyst lineage |
| `llama3.2` | Yes | Yes | No | Yes | Smaller foundation model |
| `llama3.2:3b-instruct-fp16` | Yes | Yes | No | Yes | F16 quantization reference |
| `gemma3` / `gemma3:4b` | Yes | Yes | No | Yes | Cross-architecture comparison |
| `FintellectAI_gemma` | Yes | Yes | No | Yes | Finance fine-tune on Gemma |
| `FintellectAI` | Yes | Yes | No | Limited (3.2B) | Finance fine-tune on Llama |
| `llava` / `llava:7b` | Yes | Yes | **Yes** (CLIP) | Yes | Multimodal evals |
| `FintellectAI_images` | Yes | Yes | **Yes** (CLIP) | Yes | Multimodal fine-tune |

---

### Smallest Lever Hypotheses (Unified)

| # | Hypothesis | Layer | Impact |
|---|---|---|---|
| 1 | `docker compose up` + `aeval init` + first eval in <10 min eliminates the #1 adoption blocker (infrastructure setup) | Platform + SDK | Activation |
| 2 | Tiered eval system (smoke/standard/full) reduces "teams skip evals because they're too slow" from 60% to <10% | Platform | Coverage |
| 3 | Built-in statistical significance eliminates "false ship" decisions where score deltas aren't meaningful | SDK | Decision quality |
| 4 | Automated saturation detection + replacement increases eval suite information content by 35% | Intelligence | Signal quality |
| 5 | Release readiness scorecard reduces ship/no-ship decision time from 3 days to 15 minutes | Platform | Velocity |
| 6 | Coverage heat map + gap analysis makes blind spots visible before they become production incidents | Intelligence | Safety |

### Prioritization (RICE)

| Initiative | Reach | Impact | Confidence | Effort | Score |
|---|---|---|---|---|---|
| Docker stack + orchestrator + DB + dashboard MVP | Everyone | High — foundational | High | High (12 weeks) | **P0** |
| Core SDK (eval definition + scorers + model adapters) | All engineers | High — foundational | High | High (12 weeks) | **P0** |
| CLI (`aeval run`, `aeval compare`, `aeval status`) | All engineers | High — daily use | High | Medium (6 weeks) | **P0** |
| Tiered eval system (smoke/standard/full) | All training runs | High — coverage | High | Medium (6 weeks) | **P0** |
| Statistical significance by default | All eval runs | Medium — decisions | High | Low (3 weeks) | **P1** |
| Release readiness scorecard | Every release | High — velocity | High | Low (3 weeks) | **P1** |
| Eval registry (containerized) | Cross-team | Medium — reuse | Medium | Medium (6 weeks) | **P1** |
| Saturation detection + discrimination scoring | All active evals | High — signal | High | Medium (6 weeks) | **P1** |
| Capability taxonomy + coverage heat map | All stakeholders | High — blind spots | High | Medium (8 weeks) | **P1** |
| CI/CD integration (GitHub Actions / GitLab) | Repos with models | High — gates | High | Medium (4 weeks) | **P1** |
| Adversarial eval generator | Safety | High — critical | Medium | High (12 weeks) | **P2** |
| Alignment tax calculator / regression radar | Post-training | High — alignment | Medium | Medium (8 weeks) | **P2** |
| Eval generation (all methods) | Coverage gaps | Medium — freshness | Medium | High (12 weeks) | **P2** |
| Pre-training checkpoint probes + scaling predictions | Pre-training | Medium — early signal | Low | High (16 weeks) | **P3** |

### Tradeoffs & Compute Cost

- **Ollama GPU Contention:** Ollama uses the GPU for model inference. If you're also training a model locally, Ollama and the training process compete for VRAM. Resolution: schedule comprehensive evals during training downtime. Smoke evals use smaller models (e.g., `gemma3:4b` at 3.3GB) that fit alongside training workloads. Configure Ollama's `OLLAMA_MAX_LOADED_MODELS=1` to minimize VRAM footprint.
- **Disk vs. Memory:** Large eval datasets and model checkpoints consume significant local disk. Resolution: datasets loaded lazily, model weights memory-mapped, old results prunable via `aeval prune --older-than 90d`.
- **Speed vs. Rigor:** Smoke evals trade coverage for speed. Comprehensive evals trade speed for coverage. The tiered system resolves this by matching rigor to decision weight.
- **Freshness vs. Comparability:** Adaptive evals make historical comparison difficult. Resolution: 20% stable "anchor set" for long-term trends, 80% adaptive set for fresh signal.
- **Automated vs. Human Eval:** LLM-as-judge scales but misses nuance. Resolution: use LLM-judge for gating, flag low-confidence scores for human review.
- **Eval Compute Budget:** Target: <5% of total local GPU hours. Dashboard tracks eval compute cost. Caching, sampling, and proxy models keep cost down.

---

## Phase 5: SHIP & ITERATE

### Experiments

| Experiment | Hypothesis | Metric | Duration |
|---|---|---|---|
| 10-min quickstart vs. manual setup | Dockerized quickstart increases eval adoption from ~30% to ~70% of projects | % projects with eval suite within 1 week of starting | 6 weeks |
| Smoke eval every 1000 vs. 5000 training steps | More frequent catches regressions earlier without excessive GPU contention | Time to detect regression, GPU overhead % | 4 weeks |
| LLM-as-judge vs. human eval (by category) | LLM judge achieves >90% agreement with humans at 100x speed for factuality, reasoning | Agreement rate per category, cost per eval | 8 weeks |
| Saturated eval replacement | Fresh evals catch regressions that saturated evals miss | Regressions caught, discrimination power delta | 8 weeks |
| PR comment format: table vs. badge | Which format drives more reviewer engagement with eval results? | Click-through rate, review comment quality | 4 weeks |
| Eval caching (skip unchanged model+eval+dataset) | Caching reduces redundant compute by >40% | Cache hit rate, compute savings, iteration speed | 4 weeks |

### System Health Metrics

| Metric | Target |
|---|---|
| `docker compose up` to healthy stack | < 2 min |
| Ollama connectivity check (`aeval models`) | < 1 sec |
| `aeval init` to first eval result (with Ollama model) | < 10 min |
| Smoke eval latency (end-to-end) | < 30 min |
| Standard eval latency | < 4 hours |
| Eval run success rate | > 99% |
| Dashboard page load (p95) | < 2 sec |
| Container uptime | > 99.5% |
| Ollama availability | > 99.9% |
| Ollama inference latency (p50) | < 5 sec per prompt |
| False regression alerts | < 5% |
| Eval coverage (% taxonomy with discriminative evals) | > 90% |
| Suite discrimination power (avg) | > 0.85 |
| Saturation rate (% of active evals) | < 15% |
| Eval freshness (median age) | < 6 months |

### Roadmap

| Horizon | Focus |
|---|---|
| **0-3 months (Foundation)** | Docker stack (orchestrator, DB, queue, dashboard MVP). Core SDK (eval definition, scorers, model adapters, CLI). Tiered eval system. `aeval init` quickstart. 20 core evals in registry. Basic CI integration. Statistical significance by default. |
| **3-6 months (Intelligence)** | Capability taxonomy v1. Saturation detection + discrimination scoring. Coverage heat map on dashboard. Release readiness scorecard. Eval registry with search/versioning. Comparison matrix + trend charts. Alignment tax calculator. |
| **6-12 months (Adaptive)** | Adversarial eval generator. Difficulty escalation for saturated evals. Automated eval lifecycle management. Pre-training checkpoint probes. Regression radar. LLM-as-judge framework. Advanced CI (parallel, caching, budget). |
| **1-2 years (Self-Improving)** | Full adaptive eval generation (all 5 methods). Saturation forecasting. Self-improving generator (learns from eval quality outcomes). Multi-node Docker Swarm / Kubernetes deployment for larger GPU clusters. Eval marketplace for cross-organization sharing. |

---

## Phase 6: SAFEGUARD

### Eval Integrity
- **Contamination Prevention:** Automated scanning of training data manifests against eval datasets. Contamination flag on every eval result. `aeval contamination-check --training-manifest ./manifest.json`.
- **Anti-Gaming:** 30% of active evals are held-out — results visible, tasks are not. Rotating eval subsets prevent overfitting. Goodhart's Law monitoring: track correlation between eval scores and downstream quality.
- **Anchor Set:** 20% of evals are permanently stable for long-term trend comparison. Never rotated, never retired. Clearly labeled in dashboard.

### Data Security (Local Docker)
- **No Data Leaves the Machine:** All model weights (in Ollama's `~/.ollama/models/`), eval datasets, and results stay on local disk / Docker volumes. No telemetry, no cloud sync, no external API calls. LLM-as-judge uses local Ollama models by default — fully air-gap compatible.
- **Volume Encryption:** Recommend encrypted Docker volumes or host-level disk encryption for sensitive model weights and eval data.
- **Access Control:** Dashboard at `localhost:8080` is local-only by default. For team access, user configures a reverse proxy with their own auth (nginx + OIDC, Tailscale, etc.).
- **Secrets Management:** Database passwords and API keys (for external judge models) stored via Docker secrets, not environment variables.

### Generated Eval Safety
- **Adversarial Content Sandboxing:** Generated adversarial evals may contain harmful content. Stored in restricted Docker volume. Dashboard marks adversarial eval content with warning labels.
- **Bias Auditing:** Regular automated audit of generated evals for demographic, cultural, and linguistic bias. Coverage report by taxonomy node ensures diverse representation.

### Responsible AI
- **Alignment Tax Transparency:** Every post-training eval run reports what improved and what degraded. No hiding the cost of alignment behind aggregate scores.
- **Safety Regression Blocking:** Safety score regressions automatically block the release scorecard. No override without explicit `--force-unsafe` flag (logged and auditable).
- **Eval Provenance:** Every eval task has a full audit trail: generation method, quality gate results, calibration history, version. Stored in `aeval-db`, exportable as JSON.

### Metrics / KPIs

| Category | Metrics |
|---|---|
| **Adoption** | Projects with eval suites, eval runs/week, CLI DAU, CI integration rate |
| **Decision Quality** | Regressions caught pre-merge, false ship rate, decision time |
| **Model Quality Signal** | Capability scores, safety pass rate, regression rate, user satisfaction correlation |
| **Eval Health** | Discrimination power, coverage completeness, saturation rate, freshness |
| **System** | Container uptime, GPU utilization, queue depth, DB size, eval latency |
| **Integrity** | Contamination detection rate, gaming indicators, anchor set stability |

### Insights → Repeat
- **The eval system is a product.** Apply the same rigor — instrumentation, observation, iteration — to the eval platform itself. Dogfood it.
- **Eval quality degrades by default.** Without the intelligence layer actively retiring stale evals and generating fresh ones, any eval suite decays within 6-12 months. The adaptive system fights entropy.
- **Developer adoption is the leading indicator.** If engineers aren't writing and running evals, nothing else matters. Optimize the SDK and CLI experience above all.
- **Local-first is a feature, not a limitation.** Data sovereignty, GPU access, reproducibility, and zero cloud cost make Docker deployment the right default. Cloud deployment is an optional extension, not a requirement.
- **The loop:** Define quality bar → Instrument evals → Observe model behavior → Develop targeted improvements → Ship and measure → Safeguard against gaming and staleness → Repeat. The three layers (platform, SDK, intelligence) are the infrastructure that makes this loop run continuously and automatically.

---

## Design Principles Summary

| Principle | Application |
|---|---|
| **`docker compose up` and go** | The entire platform — orchestrator, database, queue, dashboard, registry, intelligence — deploys with one command. Ollama serves models on the host. Zero cloud dependency. |
| **Eval as code** | Evals are Python functions with decorators. Version-controlled, testable, reviewable, shareable. Write them like pytest tests. |
| **Tiered speed vs. depth** | Smoke tests (30 min) gate every checkpoint. Full suites (24 hrs) gate releases. Right eval at the right moment. |
| **Statistical rigor by default** | Every score includes confidence intervals and significance tests. Eliminate gut-feel ship decisions. |
| **One source of truth** | Single dashboard at `localhost:8080` replaces scattered notebooks, spreadsheets, and Slack threads. |
| **Evals decay; the system fights entropy** | Adaptive intelligence retires saturated benchmarks, generates fresh evals, and maintains discrimination power automatically. |
| **Stable anchor + adaptive core** | 20% anchor evals for long-term trends. 80% adaptive evals for fresh, discriminative signal. |
| **Ollama is the model layer** | aeval evaluates models, Ollama serves them. Clean separation — aeval never touches GPU drivers, model weights, or VRAM. If Ollama can run it, aeval can eval it. |
| **Data never leaves your machine** | Model weights (Ollama), eval datasets, and results stay on local disk. Air-gap compatible. No external API calls required. |
| **The best eval is the one that runs** | A fast, approximate eval on every commit beats a perfect eval that runs quarterly. |
