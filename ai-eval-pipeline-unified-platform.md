# Product Design — AI Evaluation Pipeline
## Variation 1: Unified Eval Platform — Single Pane of Glass for Model Quality

**Design Philosophy:** Treat evaluation as a first-class product surface, not a research afterthought. Build a unified platform that gives researchers, engineers, and leadership a shared language for model quality across the entire lifecycle — from pre-training checkpoints to post-training alignment to production monitoring.

---

## Phase 1: DEFINE

### Define the Decision
- **Not:** "How do we build an eval pipeline?"
- **Instead:** "How do we give every stakeholder — researcher, engineer, PM, executive — real-time confidence in model quality at every stage, so they can make faster, better decisions about training runs, alignment tuning, and production releases?"

### The Problem Space
Today's evaluation landscape is fragmented:
- Pre-training teams run benchmark suites ad hoc, with results scattered across notebooks, spreadsheets, and Slack threads.
- Post-training teams use separate tooling for RLHF/DPO alignment evals, safety red-teaming, and human preference studies.
- No single system connects a pre-training checkpoint's benchmark scores to its post-training alignment quality to its production behavior.
- Decision-makers lack confidence: "Is this model ready to ship?" requires assembling data from 5+ disconnected systems.

### Core Model Assessment
- **Capabilities to Evaluate:** Reasoning, factuality, instruction-following, multimodality (text, image, code, audio), tool use, long-context, multilingual.
- **Known Limitation Patterns:** Hallucination in long-form generation, inconsistent tool-calling reliability, degradation at context boundary, reward hacking in RLHF.
- **Roadmap Dependencies:** Eval capabilities must evolve as model capabilities evolve — new modalities (video, real-time audio) require new eval frameworks before they can be shipped.

### Mission, Vision & North Star
- **Mission:** Eliminate model quality uncertainty by making evaluation continuous, comprehensive, and accessible to every team in the model lifecycle.
- **Vision:** Every training run, alignment experiment, and production release is accompanied by a living quality profile that stakeholders trust as much as they trust unit tests in software engineering.
- **North Star Metric:** **Eval Coverage Score** — percentage of model capabilities with automated, continuously-running evaluations that produce actionable quality signals (target: >95%).

---

## Phase 2: INSTRUMENT

### Universal Eval Event Schema

| Event Type | Fields |
|---|---|
| **Eval Run** | run_id, model_id, checkpoint, eval_suite, stage (pre-train / post-train / production), trigger (manual / CI / scheduled), timestamp |
| **Eval Task** | task_id, benchmark_name, category (reasoning / safety / factuality / code / multimodal), num_samples, prompt_template_version |
| **Eval Result** | task_id, score, confidence_interval, baseline_delta, pass/fail threshold, latency_p50, latency_p99, cost_per_eval |
| **Human Eval** | evaluator_id (hashed), task_id, rating (1-5 or pairwise), time_spent, agreement_score, calibration_flag |
| **Regression Alert** | model_id, task_id, regression_magnitude, prior_score, new_score, severity (info / warning / critical) |

### Pipeline Architecture

```
Training Checkpoint → Eval Trigger (CI/CD hook)
        ↓
  Eval Orchestrator (task queue, GPU allocation, retry logic)
        ↓
  Eval Runners (benchmark suites, human eval routing, adversarial probes)
        ↓
  Results Ingestion → Normalization → Storage (time-series DB + data warehouse)
        ↓
  Quality Dashboard → Alerts → Decision Gate (ship / hold / investigate)
```

### Privacy & Data Governance
- **Eval datasets versioned and access-controlled.** No training data contamination — eval sets are cryptographically separated from training corpora.
- **Human evaluator PII redacted.** Evaluator performance tracked by anonymized ID for calibration, never linked to personal identity.
- **Eval prompts containing sensitive content flagged and stored in restricted-access tier.** Safety and red-team evals require elevated access controls.

### Who Uses This Product

| Persona | Primary Need | Key Surface |
|---|---|---|
| **Pre-Training Researcher** | "Is this checkpoint improving? Should I continue training or restart?" | Checkpoint comparison dashboard, loss curves + eval overlays |
| **Post-Training/Alignment Engineer** | "Did this RLHF/DPO run improve helpfulness without regressing safety?" | Alignment radar chart, safety regression alerts |
| **ML Platform Engineer** | "Are evals running reliably, on time, and within compute budget?" | Pipeline health dashboard, job queue monitoring |
| **Product Manager** | "Is this model ready to ship to users? What's the risk?" | Release readiness scorecard, competitive comparison |
| **Executive/Leadership** | "How is model quality trending? Are we on track vs. competitors?" | High-level quality trend, capability gap analysis |

---

## Phase 3: OBSERVE

### Behavioral Dimensions (of the Eval System itself)

1. **Volume:** How many eval runs per day/week? Are teams running evals consistently, or sporadically when they remember?
2. **Conversion:** What % of eval runs produce actionable decisions (ship / hold / retrain)? If evals run but don't inform decisions, the system is noise.
3. **Frequency:** How often do teams check the dashboard? Daily active researchers on the eval platform = signal of trust and utility.
4. **Friction:** Where do evals fail or stall? GPU contention, flaky benchmarks, slow human eval turnaround, results that are hard to interpret.
5. **Segmentation:** Which teams run evals most? Which eval categories have lowest coverage? Which models have the most "unknown" quality dimensions?

### Qualitative Context
- **Researcher interviews:** "I don't trust benchmark X because it was contaminated in last training run." → Need eval set integrity verification.
- **Engineer interviews:** "It takes 3 days to get human eval results back." → Human eval latency is the bottleneck for alignment iteration speed.
- **PM interviews:** "I can't tell if the model got better or if the eval got easier." → Need eval difficulty calibration and version tracking.

### Root Cause Diagnosis
- **Symptom:** "Teams ship models without running full eval suites."
- **Root Cause:** Full eval suite takes 48 hours on current GPU allocation. Teams skip evals because the cost of waiting exceeds their perceived risk of shipping without them.
- **Lever:** Tiered eval system — fast smoke tests (2 hours) gate every checkpoint; full suite (24 hours) gates release candidates only.

---

## Phase 4: DEVELOP

### Core Product Surfaces

#### Surface 1: Eval Orchestration Engine
The backbone — schedules, dispatches, and manages eval runs across the model lifecycle.

- **CI/CD Integration:** Every training checkpoint, alignment experiment, and release candidate automatically triggers the appropriate eval tier.
- **Tiered Eval System:**

  | Tier | Trigger | Duration | Scope | Gate |
  |---|---|---|---|---|
  | **Smoke** | Every N training steps | < 30 min | Core benchmarks (10 tasks) | Continue / pause training |
  | **Standard** | Post-training experiment | 2-4 hours | Full benchmark suite (100+ tasks) | Merge / reject alignment change |
  | **Comprehensive** | Release candidate | 12-24 hours | Full suite + human eval + red team + adversarial | Ship / hold release |
  | **Continuous** | Production (sampling) | Ongoing | Live traffic sampling + drift detection | Alert / rollback |

- **GPU-Aware Scheduling:** Eval jobs compete with training for GPU resources. Smart scheduling: run evals on preemptible/spot instances, schedule heavy evals during off-peak training hours, cache intermediate results.

#### Surface 2: Quality Dashboard
The primary interface — where stakeholders understand model quality.

- **Checkpoint Timeline:** Horizontal timeline showing every checkpoint with quality scores overlaid. Click any point to drill into per-task results. Visually obvious when quality regresses.
- **Capability Radar Chart:** Spider chart showing model performance across capability dimensions (reasoning, factuality, safety, code, multilingual, multimodal). Instantly shows strengths and gaps.
- **Comparison View:** Side-by-side comparison of any two models/checkpoints. Per-task deltas, statistical significance indicators, example-level diffs for qualitative inspection.
- **Release Readiness Scorecard:** Binary pass/fail checklist: benchmark thresholds met, safety gates passed, human eval above bar, no critical regressions, latency within SLA. Green = ship. Red = investigate.

#### Surface 3: Human Eval Management
Integrated system for running human evaluations at scale.

- **Task Routing:** Automatically route eval tasks to qualified evaluators based on language, domain expertise, and calibration scores.
- **Evaluator Calibration:** Regular calibration exercises with gold-standard examples. Track inter-rater agreement. Flag and retrain low-agreement evaluators.
- **Pairwise Comparison Engine:** Side-by-side model output comparison with randomized ordering, no model labels. Statistically robust preference measurement (Bradley-Terry model).
- **Turnaround SLA:** Target: 80% of human eval results returned within 24 hours. Dashboard shows current queue depth and estimated completion time.

#### Surface 4: Safety & Red Team Module
Specialized eval surface for safety-critical assessment.

- **Automated Red Teaming:** Adversarial prompt generation using attack models. Categories: jailbreaks, harmful content, bias elicitation, PII extraction, instruction injection.
- **Safety Regression Detection:** Automated alerts when safety scores drop below threshold on any category. Safety regressions block release automatically — no override without VP-level approval.
- **Bias Audit Reports:** Demographic fairness analysis across protected categories. Automated reporting for compliance and transparency.

### Smallest Lever Hypothesis
- **Hypothesis 1:** Adding automated smoke evals to every Nth training step will catch quality regressions 10x faster than current ad-hoc eval runs. (High reach — affects every training run.)
- **Hypothesis 2:** A single "Release Readiness" scorecard will reduce the ship/no-ship decision time from 3 days of manual data gathering to 15 minutes. (High impact — directly accelerates release velocity.)
- **Hypothesis 3:** Automated eval set contamination detection will increase researcher trust in benchmark scores by eliminating the #1 cited concern. (High confidence — clear root cause.)

### Prioritization (RICE)

| Initiative | Reach | Impact | Confidence | Effort | Score |
|---|---|---|---|---|---|
| Tiered eval system (smoke / standard / full) | All training runs | High — catches regressions early | High — proven pattern | Medium (8 weeks) | **Top** |
| Release readiness scorecard | Every release | High — accelerates decisions | High — clear need | Low (3 weeks) | **Top** |
| Eval contamination detection | All benchmarks | Medium — trust improvement | Medium — research needed | Medium (6 weeks) | **Medium** |
| Human eval SLA dashboard | Alignment team | Medium — reduces bottleneck | High — measurable | Low (2 weeks) | **Medium** |
| Automated red teaming suite | Safety team | High — safety critical | Medium — evolving attacks | High (12 weeks) | **Medium** |

### Tradeoffs & Compute Cost
- **Speed vs. Comprehensiveness:** Smoke evals sacrifice coverage for speed. Comprehensive evals sacrifice speed for coverage. The tiered system is the resolution.
- **Automated vs. Human Eval:** Automated evals scale but miss nuance. Human evals capture nuance but don't scale. Use automated for gating, human for calibration and edge cases.
- **Compute Budget:** At scale, evals can consume 5-10% of total training compute. Set an eval compute budget ceiling and optimize within it — caching, sampling, proxy models.

---

## Phase 5: SHIP & ITERATE

### Experiments

| Experiment | Hypothesis | Metric | Duration |
|---|---|---|---|
| Smoke eval on every 1000th step vs. 5000th step | More frequent smoke evals catch regressions earlier without excessive compute cost | Time to detect regression, compute overhead | 4 weeks |
| Scorecard with confidence intervals vs. point estimates | Showing uncertainty improves decision quality (fewer false ships) | Ship decision accuracy, decision time | 6 weeks |
| LLM-as-judge vs. human eval for factuality | LLM judge achieves >90% agreement with human judges at 100x speed | Agreement rate, cost per eval, turnaround time | 4 weeks |
| Automated eval set refresh (quarterly) | Refreshing eval sets prevents overfitting and maintains signal integrity | Score stability, contamination rate | Ongoing |

### Data & Eval Strategy (Meta: Eval the Eval System)
- **Eval System Health Metrics:**

  | Metric | Target |
  |---|---|
  | Eval run success rate | > 99% |
  | Smoke eval latency (end-to-end) | < 30 min |
  | Standard eval latency | < 4 hours |
  | Human eval turnaround (p80) | < 24 hours |
  | False regression alerts | < 5% |
  | Eval coverage (% of capabilities with automated evals) | > 95% |

- **Feedback Loop:** Researchers rate eval usefulness after each run. Low-usefulness evals are investigated and refined or retired.

### Roadmap

| Horizon | Focus |
|---|---|
| **0-3 months** | Tiered eval system (smoke + standard), release readiness scorecard, unified dashboard MVP, CI/CD hooks for top 3 training pipelines |
| **3-12 months** | Human eval management platform, automated red teaming v1, LLM-as-judge for scalable evaluation, eval contamination detection, cross-model comparison tools |
| **1-3 years** | Self-improving eval system (evals that evolve with model capabilities), real-time production eval with drift detection, industry-standard eval benchmarking API, eval-as-a-service for external model providers |

---

## Phase 6: SAFEGUARD

### Responsible AI & Eval Integrity
- **Eval Set Security:** Eval datasets are crown jewels — leak = benchmark gaming. Encrypted storage, access logging, automated contamination scanning against training data.
- **Evaluator Bias Mitigation:** Diverse evaluator pools, randomized task assignment, blinded evaluations, regular bias audits on evaluator ratings.
- **Goodhart's Law Protection:** "When a measure becomes a target, it ceases to be a good measure." Regularly rotate and refresh benchmarks. Use held-out eval sets unknown to training teams.
- **Transparency:** Publish eval methodology, limitations, and known failure modes alongside model releases. Internal eval reports include confidence intervals, not just point scores.

### Metrics / KPIs

| Category | Metrics |
|---|---|
| **Product (Eval Platform)** | DAU (researchers/engineers on dashboard), eval runs/week, decision time reduction, user NPS |
| **Model Quality (Output)** | Capability scores across dimensions, safety pass rate, regression rate, competitive ranking |
| **Operational** | Eval pipeline uptime, job success rate, compute cost per eval, human eval turnaround |
| **Integrity** | Contamination detection rate, evaluator agreement score, benchmark refresh cadence |

### Insights → Repeat
- **Every model generation surfaces new eval gaps.** When a model gains a new capability (e.g., tool use, video understanding), the eval system must immediately instrument that capability. The eval roadmap is a shadow of the model capability roadmap.
- **Feed back:** Eval results don't just gate releases — they inform training decisions. The most valuable evals are those that change researcher behavior during training, not just confirm quality at the end.
- **The loop:** Define what quality means for the next model → Instrument evals for new capabilities → Observe quality during training → Develop targeted improvements → Ship and measure → Safeguard against gaming and bias → Repeat.

---

### Design Principles Summary

| Principle | Application |
|---|---|
| **Eval is infrastructure, not a task** | Build a platform, not a script. Evals run continuously, not when someone remembers. |
| **Tiered speed vs. depth** | Smoke tests gate every checkpoint. Full suites gate releases. Right eval at the right moment. |
| **One source of truth** | Single dashboard replaces scattered notebooks, spreadsheets, and Slack threads. |
| **Trust requires transparency** | Show confidence intervals, contamination status, and evaluator agreement — not just scores. |
| **Eval evolves with the model** | New capabilities require new evals. The eval roadmap shadows the model roadmap. |
