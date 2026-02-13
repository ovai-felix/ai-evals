# Product Design — AI Evaluation Pipeline
## Variation 2: Developer-First Eval SDK — Evaluation as Code

**Design Philosophy:** Evaluation should be as natural to ML engineers as unit testing is to software engineers. Build a developer-first SDK and CLI that makes writing, running, versioning, and sharing evals as easy as writing pytest tests — embedding evaluation into the development workflow rather than bolting it on as a separate process.

---

## Phase 1: DEFINE

### Define the Decision
- **Not:** "How do we build eval tooling?"
- **Instead:** "How do we make evaluation so frictionless that every ML engineer writes evals as naturally as they write code — and so reliable that no model change ships without automated quality verification?"

### The Problem Space
The gap between "evaluation in research papers" and "evaluation in production workflows" is enormous:
- Researchers write custom eval scripts in notebooks — one-off, non-reproducible, non-shareable.
- Engineers copy-paste eval code between projects, introducing subtle bugs (wrong tokenizer, inconsistent scoring, sampling errors).
- There is no standardized way to define, version, run, and compare evals across teams.
- Evaluation is treated as a phase ("we'll eval at the end") rather than a continuous practice.
- The result: models ship with inconsistent quality bars, regressions are caught late, and teams waste weeks re-implementing eval infrastructure.

### Core Model Assessment
- **Pre-Training Eval Needs:** Loss curves, perplexity, scaling law predictions, benchmark snapshots at checkpoints, data mixture quality signals.
- **Post-Training Eval Needs:** Instruction-following quality, alignment/safety scoring, human preference correlation, task-specific accuracy, robustness to adversarial inputs.
- **Production Eval Needs:** Latency, throughput, drift detection, user satisfaction correlation, A/B test infrastructure.
- **Cross-Cutting:** All stages need reproducibility, versioning, comparison, and statistical rigor.

### Mission, Vision & North Star
- **Mission:** Make AI evaluation a first-class software engineering discipline with professional-grade tools.
- **Vision:** Every model change — from a training hyperparameter tweak to an RLHF reward model update — is automatically validated against a versioned, comprehensive eval suite before it reaches any user.
- **North Star Metric:** **Eval Adoption Rate** — percentage of model changes (commits/experiments) that trigger automated eval runs before merge (target: >90%).

---

## Phase 2: INSTRUMENT

### SDK Telemetry Schema

| Event Type | Fields |
|---|---|
| **SDK Install** | sdk_version, python_version, platform, install_method (pip/conda/docker) |
| **Eval Definition** | eval_id, eval_type (benchmark/custom/llm-judge/human), num_samples, model_target, tags |
| **Eval Run** | run_id, eval_id, model_id, duration, status (pass/fail/error), compute_used, trigger (manual/CI/hook) |
| **Eval Result** | run_id, scores (per-task + aggregate), confidence_intervals, baseline_comparison |
| **Sharing Event** | eval_id, shared_to (team/registry/public), download_count |

### Developer Workflow Instrumentation
Track the developer experience, not just eval results:
- **Time from "pip install" to first eval result** — the activation metric.
- **Eval definition time** — how long to write a new eval? Minutes (good) or days (friction).
- **CI integration rate** — what % of repos with the SDK have CI-triggered evals?
- **Registry engagement** — are developers discovering and reusing existing evals, or writing from scratch every time?

### Who Uses This Product

| Persona | Primary Need | Interaction Mode |
|---|---|---|
| **ML Researcher** | Quick, reproducible eval of experimental models | Notebook / CLI, ad-hoc runs |
| **ML Engineer** | Automated eval in training pipeline CI/CD | SDK in Python, CI integration, programmatic |
| **Alignment/Safety Researcher** | Specialized safety and red-team evals | Custom eval definitions, adversarial datasets |
| **ML Platform Engineer** | Reliable eval infrastructure at scale | Config-as-code, orchestration, monitoring |
| **Technical PM/Lead** | Model comparison and release decisions | Dashboard, reports, comparison views |

---

## Phase 3: OBSERVE

### Developer Behavior Dimensions

1. **Volume:** How many eval runs per developer per week? Are evals becoming habitual or remaining occasional?
2. **Conversion:** What % of SDK installs lead to a first eval run within 24 hours? What % of first runs lead to CI integration within 2 weeks?
3. **Frequency:** How often do developers update their eval suites? Stale evals = false confidence.
4. **Friction:** Where do developers get stuck? Common failure modes: dataset loading errors, GPU OOM during eval, confusing score interpretation, slow runs blocking iteration.
5. **Segmentation:** Researchers vs. engineers use the SDK differently. Researchers want flexibility; engineers want reliability. Design for both without compromising either.

### Qualitative Research
- **Developer interviews:** "I spend 2 days setting up eval infrastructure for every new project." → Eval boilerplate is the #1 friction point.
- **Developer interviews:** "I don't trust my evals because I'm not sure they're statistically sound." → Need built-in statistical rigor (confidence intervals, significance tests).
- **Developer interviews:** "I wrote a great eval suite but nobody else on the team uses it." → Need sharing/registry infrastructure.

### Root Cause Diagnosis
- **Symptom:** "Teams don't run evals consistently."
- **Root Cause:** Writing evals is hard (custom code for every benchmark), running evals is slow (no GPU scheduling), and interpreting results requires statistical expertise most ML engineers don't have.
- **Lever:** Make writing evals as easy as writing a test function, running evals fast and GPU-aware, and interpretation automatic with built-in statistical analysis.

---

## Phase 4: DEVELOP

### Core Product Surfaces

#### Surface 1: Eval SDK (Python Library)

**Design Goal:** Writing an eval should feel like writing a pytest test.

```python
# Example: Define a factuality eval
from aeval import Eval, Dataset, Scorer

@Eval(name="factuality-v2", tags=["safety", "factuality"])
def factuality_eval(model):
    dataset = Dataset.load("factuality-qa-v3")  # versioned dataset

    results = model.generate(dataset.prompts)

    scores = Scorer.factuality(
        predictions=results,
        references=dataset.references,
        method="llm-judge",  # or "exact-match", "human", "custom"
        judge_model="claude-sonnet",
    )

    return scores

# Run from CLI:  aeval run factuality-v2 --model checkpoint-50k
# Run in CI:     aeval run --suite pre-release --model $MODEL_PATH
# Compare:       aeval compare model-a model-b --suite core
```

**Key SDK Features:**
- **Declarative Eval Definition:** Decorator-based API. Define what to evaluate, not how to orchestrate it.
- **Built-in Scorers:** Exact match, BLEU/ROUGE, LLM-as-judge (configurable judge model), embedding similarity, code execution, human eval routing.
- **Dataset Management:** Versioned datasets with integrity hashes. Load from local, cloud, or shared registry. Automatic train/eval contamination checking.
- **Statistical Rigor by Default:** Every score includes confidence intervals, significance tests vs. baseline, effect size. No more "is 0.82 vs 0.81 meaningful?" guessing.
- **Model Adapters:** Unified interface for evaluating any model — local checkpoints, API endpoints, HuggingFace models, custom inference servers.

#### Surface 2: CLI & CI/CD Integration

```bash
# Quick eval from terminal
$ aeval run --eval factuality-v2 --model ./checkpoint-50k
Running factuality-v2 on checkpoint-50k...
━━━━━━━━━━━━━━━━━━━━━━━ 100% ━━━━━━━━━━━━━━━━━━━━━━━
Results:
  factuality_score: 0.847 (±0.023, 95% CI)
  vs. baseline:     +0.031 (p=0.003, significant)
  Status:           PASS (threshold: 0.80)

# Full suite with comparison
$ aeval compare checkpoint-50k checkpoint-45k --suite core
┌─────────────────┬───────────┬───────────┬──────────┬─────────┐
│ Eval            │ 50k       │ 45k       │ Delta    │ Sig?    │
├─────────────────┼───────────┼───────────┼──────────┼─────────┤
│ factuality      │ 0.847     │ 0.816     │ +0.031   │ **yes** │
│ reasoning       │ 0.723     │ 0.718     │ +0.005   │ no      │
│ safety          │ 0.994     │ 0.996     │ -0.002   │ no      │
│ code-gen        │ 0.681     │ 0.652     │ +0.029   │ **yes** │
│ instruction     │ 0.891     │ 0.873     │ +0.018   │ **yes** │
└─────────────────┴───────────┴───────────┴──────────┴─────────┘
Overall: 3/5 significant improvements, 0 regressions. PASS.

# CI/CD integration (GitHub Actions / GitLab CI)
$ aeval ci --suite pre-merge --fail-on regression --model $MODEL_PATH
```

**CI/CD Features:**
- **Pre-Merge Gate:** Eval runs on every model PR. Regressions block merge. Configurable thresholds per eval.
- **Post-Merge Tracking:** Full eval suite runs on merged changes. Results tracked in time-series for trend analysis.
- **GitHub/GitLab Integration:** Eval results posted as PR comments with pass/fail badges, score tables, and regression highlights.
- **Parallel Execution:** Distributes eval tasks across available GPUs. Smart scheduling to minimize wall-clock time.

#### Surface 3: Eval Registry

A shared library of eval definitions that teams can discover, reuse, and contribute to.

- **Registry Structure:**
  ```
  registry/
  ├── core/               # Maintained by platform team
  │   ├── factuality-v3
  │   ├── reasoning-v2
  │   ├── safety-v4
  │   └── code-gen-v2
  ├── community/          # Team contributions
  │   ├── medical-qa-v1
  │   ├── legal-reasoning-v1
  │   └── multilingual-v2
  └── custom/             # Team-private evals
      └── [team-specific]
  ```

- **Eval Metadata:** Each eval in the registry includes: description, capability tested, expected runtime, compute requirements, dataset size, version history, maintainer, and usage statistics.
- **Eval Suites:** Named collections of evals for common workflows: `pre-merge` (fast, core), `pre-release` (comprehensive), `safety` (all safety evals), `reasoning` (all reasoning evals).
- **Versioning:** Semantic versioning for eval definitions and datasets. Breaking changes require major version bump. Old versions remain runnable for historical comparison.

#### Surface 4: Results Dashboard (Web UI)

For stakeholders who prefer visual exploration over CLI output.

- **Experiment Tracker:** Every eval run logged with full provenance — model, dataset version, eval version, scores, config. Searchable and filterable.
- **Trend Charts:** Time-series of eval scores across checkpoints/experiments. Spot regressions visually. Annotate charts with events ("switched to new data mixture," "applied DPO").
- **Comparison Matrix:** Select N models, M evals → matrix of scores with color-coded deltas and significance indicators.
- **Drill-Down:** Click any score → see per-sample results, worst-performing examples, error analysis. Researchers can inspect exactly where and why a model fails.

### Smallest Lever Hypothesis
- **Hypothesis 1:** A `aeval init` command that scaffolds eval boilerplate for a project will increase the % of projects with eval suites from ~30% to ~70%. (Removes the blank-page problem.)
- **Hypothesis 2:** Built-in statistical significance testing will reduce "false ship" decisions by 40% — teams currently ship on score deltas that aren't statistically meaningful. (Improves decision quality without changing workflow.)
- **Hypothesis 3:** Posting eval results as PR comments will increase eval awareness among reviewers and create social pressure to maintain quality bars. (Leverages existing code review workflow.)

### Prioritization (RICE)

| Initiative | Reach | Impact | Confidence | Effort | Score |
|---|---|---|---|---|---|
| Core SDK (eval definition + scorers + runners) | All ML engineers | High — foundational | High | High (12 weeks) | **Top** |
| CLI with CI/CD integration | All repos with models | High — gates quality | High | Medium (6 weeks) | **Top** |
| Built-in statistical significance | All eval runs | Medium — decision quality | High | Low (3 weeks) | **Top** |
| Eval registry (shared evals) | Cross-team | Medium — reduces duplication | Medium | Medium (8 weeks) | **Medium** |
| Web dashboard | PMs, leads | Medium — visibility | Medium | Medium (8 weeks) | **Medium** |
| `aeval init` scaffolding | New projects | Medium — activation | High | Low (2 weeks) | **Medium** |

### Tradeoffs & Compute Cost
- **Flexibility vs. Simplicity:** Researchers want to customize everything. Engineers want sensible defaults. Resolution: opinionated defaults with escape hatches at every layer.
- **Speed vs. Rigor:** Fast evals (sampling, proxy models) trade accuracy for speed. Rigorous evals (full dataset, human judges) are slow. Resolution: fast evals for iteration, rigorous evals for decisions.
- **Centralized vs. Decentralized:** A shared registry creates standards but can bottleneck. Team-private evals allow autonomy but fragment quality bars. Resolution: core evals are centrally maintained and mandatory; teams add custom evals on top.
- **Compute:** Eval compute budget = 3-5% of training compute. SDK tracks and reports compute cost per eval. Teams can set budget caps.

---

## Phase 5: SHIP & ITERATE

### Experiments

| Experiment | Hypothesis | Metric | Duration |
|---|---|---|---|
| `aeval init` adoption | Scaffolding increases eval adoption in new projects | % new projects with eval suite within 1 week | 6 weeks |
| PR comment format A vs. B | Detailed table vs. summary badge — which drives more review engagement? | PR comment click-through rate, reviewer feedback quality | 4 weeks |
| LLM-judge accuracy by category | Measure LLM-judge agreement with human eval across 10 categories to identify where automated scoring is reliable vs. unreliable | Agreement rate per category, false positive/negative rates | 8 weeks |
| Eval caching (skip unchanged) | Cache eval results when model + eval + dataset are unchanged to reduce redundant compute | Compute savings, cache hit rate, developer iteration speed | 4 weeks |

### Data & Eval Strategy
- **Dogfooding:** The eval SDK team uses the eval SDK to evaluate the eval SDK. Meta-eval: are our evals good evals?
- **Eval Quality Metrics:** Inter-rater reliability for human evals, LLM-judge vs. human agreement rates, eval discrimination power (can this eval distinguish good models from bad models?).
- **Feedback Loop:** SDK usage analytics → identify friction points → prioritize improvements. Monthly developer survey on SDK satisfaction (target NPS: 50+).

### Roadmap

| Horizon | Focus |
|---|---|
| **0-3 months** | Core SDK (eval definition, scorers, runners), CLI with basic CI integration, 20 core evals in registry, documentation and tutorials |
| **3-12 months** | Eval registry with search/discovery, web dashboard for results exploration, LLM-as-judge framework, human eval routing, advanced CI features (parallel execution, caching, budget tracking) |
| **1-3 years** | Self-evolving evals (AI generates new eval cases to cover blind spots), cross-organization eval sharing (industry benchmarks as eval-SDK packages), real-time production eval integration, eval marketplace |

---

## Phase 6: SAFEGUARD

### Responsible AI & Eval Integrity
- **Eval Contamination Prevention:** Automated scanning of training data against eval datasets. Contamination detection integrated into eval run — results flagged if contamination risk is detected.
- **Eval Gaming Resistance:** Hold-out eval sets that are never exposed to training teams. Rotating eval subsets to prevent overfitting to specific benchmarks.
- **Diverse Eval Coverage:** Mandatory coverage across demographic groups, languages, and edge cases. Eval coverage report flags blind spots.
- **Open Science:** SDK and core evals are open-source. Community contributions welcomed. Transparency in methodology builds trust across the industry.

### Metrics / KPIs

| Category | Metrics |
|---|---|
| **Adoption** | SDK installs, DAU, eval runs/week, CI integration rate, registry contributions |
| **Quality** | Eval discrimination power, LLM-judge agreement rate, false regression rate |
| **Developer Experience** | Time to first eval, eval definition time, NPS, support ticket volume |
| **Impact** | Regressions caught pre-merge, decision time reduction, model quality trend |

### Insights → Repeat
- **The eval ecosystem evolves with the models.** As models gain new capabilities, the SDK needs new scorers, new dataset types, and new eval patterns. The SDK roadmap is a function of the model roadmap.
- **Developer adoption is the leading indicator.** If ML engineers aren't writing evals, no amount of infrastructure matters. Optimize for developer experience above all else.
- **The loop:** Observe developer friction → Remove barriers → More evals written → Better model quality → More trust in eval system → More investment in eval infrastructure → Repeat.

---

### Design Principles Summary

| Principle | Application |
|---|---|
| **Eval as code** | Evals are version-controlled, testable, reviewable, and shareable — just like application code. |
| **Pytest for ML** | Writing an eval should feel as natural as writing a unit test. Familiar patterns, minimal boilerplate. |
| **Statistical rigor by default** | Every score includes confidence intervals and significance tests. No more gut-feel decisions. |
| **Batteries included, escape hatches available** | Opinionated defaults for 90% of cases. Full customization for the other 10%. |
| **The best eval is the one that runs** | A fast, approximate eval that runs on every commit beats a perfect eval that runs quarterly. |
