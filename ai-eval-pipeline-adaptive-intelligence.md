# Product Design — AI Evaluation Pipeline
## Variation 3: Adaptive Eval Intelligence — Self-Evolving Evaluation System

**Design Philosophy:** Static benchmarks decay. Models improve, but the evals measuring them stay frozen — creating a widening gap between what we measure and what matters. Build an evaluation system that adapts: automatically discovers capability gaps, generates new eval cases, retires saturated benchmarks, and continuously calibrates itself against real-world model performance.

---

## Phase 1: DEFINE

### Define the Decision
- **Not:** "How do we build more benchmarks?"
- **Instead:** "How do we build an evaluation system that stays ahead of model capabilities — one that identifies what we're not measuring, generates evaluations for emerging capabilities, and retires evaluations that no longer discriminate between good and bad models?"

### The Problem Space
The fundamental challenge of AI evaluation is eval staleness:
- **Benchmark Saturation:** Models approach or exceed human performance on established benchmarks (MMLU, HumanEval, GSM8K). Saturated benchmarks can't distinguish between models or detect regressions in nuanced capabilities.
- **Capability-Eval Lag:** New model capabilities (tool use, multi-step reasoning, agentic behavior, multimodal understanding) emerge faster than eval suites are created to measure them. Months pass between capability launch and reliable evaluation.
- **Gaming & Overfitting:** When benchmarks become targets, teams (consciously or unconsciously) optimize for them. Scores improve without corresponding real-world quality improvement. Goodhart's Law in action.
- **Coverage Blind Spots:** No team can anticipate every failure mode. Models fail in surprising ways that existing evals don't cover — discovered only after deployment, through user complaints.

### Core Model Assessment
- **Pre-Training Evaluation Challenges:** Predicting downstream capability from pre-training metrics (loss, perplexity) is imprecise. Need eval proxies that correlate with post-training quality earlier in the pipeline.
- **Post-Training Evaluation Challenges:** Alignment tuning (RLHF/DPO) can improve some capabilities while silently degrading others. Need comprehensive regression detection across all capability dimensions simultaneously.
- **Emergent Capability Detection:** Models develop capabilities not explicitly trained for. Need eval methods that discover capabilities, not just measure known ones.

### Mission, Vision & North Star
- **Mission:** Build an evaluation system that is always more comprehensive than the model it evaluates — one that discovers gaps before users do.
- **Vision:** Evaluation that evolves alongside AI capabilities, ensuring that every model improvement is verified, every regression is caught, and every blind spot is surfaced before deployment.
- **North Star Metric:** **Eval Freshness Score** — the percentage of eval tasks that maintain >0.15 discrimination power (ability to distinguish between meaningfully different models) at any given time. Target: >85% of all active evals remain discriminative.

---

## Phase 2: INSTRUMENT

### Adaptive Eval Event Schema

| Event Type | Fields |
|---|---|
| **Eval Task Lifecycle** | task_id, created_date, category, difficulty_estimate, saturation_score, discrimination_power, active_status, retirement_date |
| **Generation Event** | generator_model, generation_method (adversarial / capability-probe / user-derived / synthetic), source_signal (blind spot detected / saturation triggered / new capability) |
| **Calibration Event** | task_id, human_agreement_score, difficulty_recalibration, discrimination_power_update |
| **Saturation Alert** | task_id, saturation_score, models_above_threshold, recommended_action (retire / increase difficulty / replace) |
| **Coverage Map** | capability_dimension, eval_count, average_discrimination, coverage_gap_score, priority_for_generation |

### System Architecture

```
Model Capabilities (Current + Emerging)
        ↓
  Capability Taxonomy (structured map of what the model should do)
        ↓
  Coverage Analyzer → Identifies gaps between taxonomy and existing evals
        ↓
  Eval Generator → Creates new eval tasks for uncovered capabilities
        ↓
  Difficulty Calibrator → Ensures new evals are appropriately challenging
        ↓
  Discrimination Monitor → Tracks which evals still differentiate models
        ↓
  Saturation Detector → Flags evals approaching ceiling → triggers retirement/replacement
        ↓
  Active Eval Suite (continuously curated, always fresh)
        ↓
  Model Evaluation → Results
        ↓
  Feedback Loop → Results inform coverage gaps → cycle repeats
```

### Privacy & Data Governance
- **Synthetic Eval Data:** Generated eval cases use synthetic or publicly-sourced data. No user data in eval sets without explicit consent and anonymization.
- **Adversarial Eval Security:** Red-team and adversarial evals stored in restricted-access environments. Generated attack vectors are sensitive IP.
- **Eval Provenance:** Every eval task has a full audit trail — who/what generated it, when, why, and what it's measuring. Provenance ensures accountability and reproducibility.

### Who Uses This Product

| Persona | Primary Need | Key Interaction |
|---|---|---|
| **Eval Scientist** | Design and maintain evaluation methodology | Capability taxonomy curation, generator tuning, calibration review |
| **Pre-Training Researcher** | Early signal on capability development during training | Capability emergence probes at checkpoints, scaling law eval predictions |
| **Post-Training Engineer** | Comprehensive regression detection after alignment | Full adaptive suite run, blind-spot analysis, regression drill-down |
| **Safety Researcher** | Adversarial eval generation for novel attack vectors | Red-team eval generator, adversarial coverage map, novel risk discovery |
| **Research Leadership** | Confidence that eval system is comprehensive and current | Eval health dashboard, coverage gaps, saturation alerts |

---

## Phase 3: OBSERVE

### Behavioral Dimensions (of the Eval System Health)

1. **Volume:** How many active eval tasks? Growing or stagnating? What's the generation rate of new evals vs. retirement rate of saturated ones?
2. **Discrimination:** What % of active evals can distinguish between the current best model and the next-best? If discrimination power is low, the eval suite is stale.
3. **Coverage:** What % of the capability taxonomy has active, discriminative evals? Gaps = blind spots = undetected regressions.
4. **Freshness:** What is the median age of eval tasks? Old evals are likely saturated or gamed. Fresh evals are more reliable.
5. **Calibration:** How well do automated eval scores correlate with human judgments? Drift in correlation = eval quality decay.

### Qualitative Context
- **Researcher interviews:** "We hit 95% on MMLU but users still complain about factual errors." → Benchmark saturation ≠ capability mastery. Need evals that measure real-world factuality, not test-format factuality.
- **Safety team interviews:** "We red-team manually, but we can't keep up with the rate of model changes." → Need automated adversarial eval generation that scales with model iteration speed.
- **Leadership interviews:** "How do I know our eval suite isn't missing something critical?" → Need coverage maps and gap analysis that make blind spots visible.

### Root Cause Diagnosis
- **Symptom:** "Model scores improve on benchmarks, but user satisfaction is flat."
- **Root Cause:** Benchmark scores are saturated — improvements are in the noise. Real-world capabilities that matter to users (nuanced instruction following, contextual reasoning, creative generation) are under-evaluated.
- **Lever:** Adaptive eval system that retires saturated benchmarks, generates evals aligned with user-reported issues, and maintains discrimination power across all measured capabilities.

---

## Phase 4: DEVELOP

### Core Product Surfaces

#### Surface 1: Capability Taxonomy Engine
A structured, living map of everything the model should be able to do.

- **Taxonomy Structure:**
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
  │   ├── Temporal Reasoning (recent vs. historical)
  │   ├── Source Attribution
  │   └── Uncertainty Calibration
  ├── Language & Communication
  │   ├── Instruction Following (simple → complex)
  │   ├── Long-Form Generation
  │   ├── Summarization
  │   ├── Translation
  │   ├── Tone & Style Adaptation
  │   └── Multilingual (by language family)
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

- **Coverage Heat Map:** Visual overlay showing eval density and discrimination power per taxonomy node. Red = uncovered or saturated. Green = well-evaluated and discriminative. Instantly reveals where to invest eval effort.
- **Taxonomy Evolution:** As models gain new capabilities, taxonomy nodes are added. Research team proposes new nodes; eval scientists validate and instrument.

#### Surface 2: Adaptive Eval Generator
AI-powered system that creates new evaluation tasks to fill coverage gaps.

- **Generation Methods:**

  | Method | Input | Output | Use Case |
  |---|---|---|---|
  | **Adversarial Generation** | Current model + known failure patterns | Hard eval cases that probe weaknesses | Safety, robustness |
  | **Capability Probing** | Taxonomy gap + capability description | Eval tasks testing specific, uncovered capabilities | Coverage expansion |
  | **User-Signal Derived** | Aggregated user complaints/feedback (anonymized) | Eval cases reflecting real-world failure modes | Relevance alignment |
  | **Difficulty Escalation** | Saturated eval + model performance | Harder versions of existing evals | Maintaining discrimination |
  | **Cross-Domain Transfer** | Eval from domain A + domain B description | Analogous eval adapted to new domain | Rapid domain expansion |

- **Quality Gates for Generated Evals:**
  1. **Clarity check:** Is the task unambiguous? (LLM-verified + human spot-check)
  2. **Difficulty calibration:** Test against 3+ models of varying capability. Must discriminate.
  3. **Ground truth validation:** Does the eval have a verifiable correct answer or clear evaluation criteria?
  4. **Contamination check:** Is this task (or close paraphrases) in any known training set?
  5. **Human agreement:** Does human evaluation agree with automated scoring? (Spot-check sample)

- **Generation Cadence:**
  - **Continuous:** Adversarial generation runs daily against latest model, producing 50-100 candidate eval tasks.
  - **Triggered:** Coverage gap detection triggers bulk generation for under-evaluated taxonomy nodes.
  - **Scheduled:** Quarterly full taxonomy review + bulk generation to maintain comprehensive coverage.

#### Surface 3: Saturation & Discrimination Monitor
Continuous health monitoring of every eval task in the active suite.

- **Discrimination Power Score:** For each eval task, measure how well it distinguishes between models of different quality levels. Score = variance in performance across models / total variance. Low discrimination = eval is too easy, too hard, or too noisy.
- **Saturation Detection:**
  - **Ceiling Saturation:** >90% of evaluated models score above 95% → eval is too easy for current generation.
  - **Floor Saturation:** >90% of models score below 10% → eval is too hard and not useful for current generation.
  - **Noise Saturation:** Score variance across repeated runs of the same model exceeds variance across different models → eval is measuring noise, not capability.
- **Automated Lifecycle Management:**

  | Eval State | Trigger | Action |
  |---|---|---|
  | **Active** | Discrimination > 0.15 | Include in standard suite |
  | **Watch** | Discrimination 0.08-0.15 | Flag for review, consider difficulty escalation |
  | **Saturated** | Discrimination < 0.08 for 3 consecutive months | Retire from active suite, trigger replacement generation |
  | **Archived** | Retired | Keep for historical comparison, exclude from active evaluation |

- **Saturation Forecast:** Predict which evals will saturate in 3-6 months based on model improvement trajectories. Generate replacements proactively, not reactively.

#### Surface 4: Pre-Training Eval Integration
Specialized capabilities for evaluating models during the pre-training phase.

- **Checkpoint Probes:** Lightweight eval tasks designed to run on pre-trained (not instruction-tuned) models. Test raw capability emergence without relying on instruction-following ability.
- **Scaling Law Eval Predictions:** Given eval scores at checkpoints N, 2N, 4N... predict eval performance at 10N. Identify which capabilities are on track and which are plateauing before investing full training compute.
- **Data Mixture Quality Signals:** Eval results correlated with training data composition. Identify which data sources contribute to which capabilities. Enable data-driven decisions about training mixture adjustments.
- **Early Termination Signals:** If eval probes show a training run is not developing expected capabilities by checkpoint N, recommend early termination to save compute. "This run is unlikely to achieve target reasoning capability — consider restarting with modified architecture/data."

#### Surface 5: Post-Training Regression Radar
Comprehensive regression detection for alignment and fine-tuning stages.

- **Alignment Tax Calculator:** Quantify the capability cost of alignment tuning. For each RLHF/DPO experiment, measure: what improved (helpfulness, safety) and what degraded (factuality, reasoning, creativity). Make the tradeoff explicit and data-driven.
- **Silent Regression Detection:** Compare post-training model against pre-training checkpoint across full taxonomy. Flag any capability that drops >2% — even if not explicitly targeted by the alignment process.
- **Reward Hacking Detection:** Identify cases where the model optimizes for reward model scores without genuine quality improvement. Compare reward model scores vs. human preference vs. objective metrics. Divergence = hacking.
- **Multi-Turn Regression:** Evaluate conversation quality over extended interactions (5+ turns). Alignment tuning often improves single-turn quality while degrading multi-turn coherence — a regression invisible to single-turn evals.

### Smallest Lever Hypothesis
- **Hypothesis 1:** Replacing the bottom 20% of saturated evals with freshly generated discriminative evals will increase the information content of the eval suite by 35%, catching regressions currently invisible to the existing suite.
- **Hypothesis 2:** Saturation forecasting (predicting which evals will saturate in 6 months) will allow proactive replacement, reducing the average "blind window" (time between eval saturation and replacement) from 4 months to 2 weeks.
- **Hypothesis 3:** User-signal-derived evals (generated from aggregated user complaints) will correlate 2x better with user satisfaction than traditional academic benchmarks, because they measure what users actually care about.

### Prioritization (RICE)

| Initiative | Reach | Impact | Confidence | Effort | Score |
|---|---|---|---|---|---|
| Saturation detection + automated retirement | All active evals | High — removes false confidence | High — measurable | Medium (6 weeks) | **Top** |
| Capability taxonomy + coverage heat map | All eval stakeholders | High — reveals blind spots | High — clear need | Medium (8 weeks) | **Top** |
| Adversarial eval generator | Safety team + all models | High — safety critical | Medium — quality varies | High (12 weeks) | **Top** |
| Discrimination power scoring | All active evals | Medium — quality signal | High — statistical | Low (3 weeks) | **Top** |
| Difficulty escalation generator | Saturated evals | Medium — maintains signal | Medium — needs calibration | Medium (6 weeks) | **Medium** |
| User-signal-derived eval generation | Post-training + production | High — relevance | Low — novel approach | High (12 weeks) | **Medium** |
| Scaling law eval predictions | Pre-training | Medium — saves compute | Low — research needed | High (16 weeks) | **Lower** |

### Tradeoffs & Compute Cost
- **Eval Quality vs. Generation Speed:** AI-generated evals are fast but require quality gates. Human-crafted evals are high quality but slow. Resolution: AI generates candidates at scale, humans review and calibrate a sample, statistical checks validate the rest.
- **Coverage Breadth vs. Depth:** Covering the full taxonomy thinly vs. covering critical capabilities deeply. Resolution: tiered coverage — safety and core reasoning get deep, dense evaluation; long-tail capabilities get lighter probing with escalation on anomalies.
- **Freshness vs. Comparability:** Frequently changing eval suites make historical comparison difficult. Resolution: maintain a stable "anchor set" (20% of evals, never changed) for long-term trends, while the remaining 80% adapts.
- **Compute Budget:** Eval generation consumes ~2% of total eval compute. Monitoring and calibration consume ~5%. Total adaptive overhead: ~7% on top of base eval cost — paid back in higher-quality signals and fewer post-deployment surprises.

---

## Phase 5: SHIP & ITERATE

### Experiments

| Experiment | Hypothesis | Metric | Duration |
|---|---|---|---|
| Replace saturated evals with generated alternatives | Fresh evals catch regressions that saturated evals miss | Regressions caught, discrimination power | 8 weeks |
| Adversarial generation daily vs. weekly | Daily generation catches more novel attack vectors | Novel failure modes discovered, safety score confidence | 6 weeks |
| LLM-generated eval quality vs. human-crafted | Generated evals achieve >80% agreement with human-crafted evals of the same capability | Human agreement rate, discrimination power, false positive rate | 8 weeks |
| Scaling law prediction accuracy | Checkpoint probe predictions at 25% training match final eval scores within ±5% | Prediction accuracy, early termination savings | 12 weeks |
| User-signal-derived evals vs. academic benchmarks | User-derived evals predict user satisfaction better than traditional benchmarks | Correlation with user satisfaction, regression detection rate | 12 weeks |

### Data & Eval Strategy (Meta-Evaluation)
- **Eval Quality Metrics:**

  | Metric | Target | Description |
  |---|---|---|
  | Suite discrimination power | > 0.85 avg | Active suite can distinguish model quality levels |
  | Coverage completeness | > 90% of taxonomy nodes | Every capability has at least one active, discriminative eval |
  | Saturation rate | < 15% of active evals | Majority of evals remain informative |
  | Freshness (median eval age) | < 6 months | Evals are regularly refreshed |
  | Human-auto agreement | > 0.85 correlation | Automated scoring reflects human judgment |
  | Generation quality (acceptance rate) | > 60% | Most generated eval candidates pass quality gates |
  | Anchor set stability | 100% (unchanged) | Long-term comparison baseline maintained |

- **Feedback Loop:** Eval results + model behavior + user signals → identify gaps → generate new evals → calibrate → deploy → measure impact → repeat. The eval system improves itself continuously.

### Roadmap

| Horizon | Focus |
|---|---|
| **0-3 months** | Capability taxonomy v1 (100 nodes), saturation detector + discrimination scorer for existing benchmarks, coverage heat map dashboard, begin adversarial eval generation pilot |
| **3-12 months** | Full adaptive eval generator (all 5 methods), automated eval lifecycle management (generation → calibration → deployment → monitoring → retirement), pre-training checkpoint probes, post-training regression radar, anchor set definition |
| **1-3 years** | Self-improving eval system (eval generator improves itself based on eval quality outcomes), cross-organization eval exchange (anonymized capability signals shared across labs), real-time production capability monitoring, predictive capability modeling (forecast what the model will be able to do N training steps from now) |

---

## Phase 6: SAFEGUARD

### Responsible AI & Eval System Integrity
- **Anti-Gaming Measures:**
  - **Hidden eval sets:** 30% of active evals are never exposed to training teams. Results are visible; tasks are not. Prevents conscious or unconscious optimization.
  - **Rotating eval subsets:** Different eval samples used each run. Full eval set never fully observable from any single run's results.
  - **Contamination scanning:** Every generated eval is checked against all known training data before deployment.
  - **Goodhart's Law monitoring:** Track correlation between eval scores and downstream user satisfaction. If correlation drops, evals are being gamed.

- **Generated Eval Safety:**
  - Adversarial eval generation can create harmful content as a byproduct. Generated content is sandboxed, access-controlled, and automatically reviewed for unsafe material.
  - Eval tasks involving sensitive topics (violence, discrimination, illegal activity) are tagged, restricted, and subject to additional human review.

- **Bias in Eval Generation:**
  - AI eval generators can inherit biases from their training data. Regularly audit generated evals for demographic, cultural, and linguistic bias.
  - Mandate diverse coverage across languages, cultures, and demographic contexts in the capability taxonomy.

- **Transparency & Reproducibility:**
  - Every eval task has full provenance: generation method, quality gate results, calibration data, version history.
  - Eval methodology documented and (where possible) published for external review.
  - Distinction between "anchor set" (stable, comparable) and "adaptive set" (evolving, fresher) is clearly communicated in all reports.

### Metrics / KPIs

| Category | Metrics |
|---|---|
| **Eval System Health** | Discrimination power (suite avg), coverage completeness, saturation rate, freshness score |
| **Generation Quality** | Acceptance rate, human agreement, discrimination of generated evals, generation cost |
| **Model Quality Signal** | Regressions caught pre-deployment, correlation with user satisfaction, blind-spot detection rate |
| **Operational** | Generation pipeline uptime, calibration turnaround time, eval suite update cadence |
| **Integrity** | Hidden eval score divergence, contamination detection rate, gaming indicator trends |

### Insights → Repeat
- **The eval system is itself a product that needs evaluation.** Apply the BOMI framework to the eval system: observe its behavior, measure its effectiveness, iterate on its design.
- **Eval quality degrades by default.** Without active maintenance, every eval suite decays — benchmarks saturate, models overfit, capabilities evolve past what's measured. The adaptive system fights entropy.
- **The most valuable evals are the ones you didn't know you needed.** The coverage gap analysis and user-signal-derived generation are the highest-leverage features — they surface unknown unknowns before they become production incidents.
- **The loop:** Model capabilities evolve → Taxonomy updates → Coverage gaps identified → New evals generated → Saturated evals retired → Suite freshness maintained → Model quality signals remain trustworthy → Better models ship → Capabilities evolve further → Repeat.

---

### Design Principles Summary

| Principle | Application |
|---|---|
| **Evals decay; systems must counteract entropy** | Automated saturation detection and replacement prevent the eval suite from becoming stale. |
| **Measure what matters, not what's easy** | User-signal-derived evals align evaluation with real-world quality. Academic benchmarks are starting points, not endpoints. |
| **Coverage > depth for safety** | A broad capability taxonomy with gap detection catches the long-tail failures that deep-but-narrow benchmarks miss. |
| **Anti-fragile evaluation** | The system gets stronger as models get stronger — harder models trigger harder evals, maintaining signal. |
| **Stable anchor + adaptive core** | 20% stable anchor set for long-term trends + 80% adaptive set for fresh, discriminative signal. Best of both worlds. |
| **The eval system is a product** | Apply the same product rigor (instrumentation, observation, iteration) to the eval system itself. |
