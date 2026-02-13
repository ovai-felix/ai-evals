-- Phase 5: Adaptive Intelligence — Taxonomy & Health Tables
-- Adds capability taxonomy tree, eval-to-taxonomy mapping, and per-eval health metrics.

-- Capability taxonomy tree
CREATE TABLE IF NOT EXISTS taxonomy_nodes (
    id          SERIAL PRIMARY KEY,
    parent_id   INTEGER REFERENCES taxonomy_nodes(id),
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    level       INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_taxonomy_parent_name
    ON taxonomy_nodes(parent_id, name);

-- Maps evals to taxonomy nodes (many-to-many)
CREATE TABLE IF NOT EXISTS taxonomy_eval_map (
    taxonomy_id INTEGER NOT NULL REFERENCES taxonomy_nodes(id),
    eval_id     INTEGER NOT NULL REFERENCES eval_definitions(id),
    PRIMARY KEY (taxonomy_id, eval_id)
);

-- Per-eval health metrics (updated by monitor worker)
CREATE TABLE IF NOT EXISTS eval_health (
    eval_id              INTEGER PRIMARY KEY REFERENCES eval_definitions(id),
    discrimination_power DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    saturation_type      TEXT,
    lifecycle_state      TEXT NOT NULL DEFAULT 'active'
                         CHECK (lifecycle_state IN ('active','watch','saturated','archived')),
    scores_by_model      JSONB NOT NULL DEFAULT '{}',
    last_checked         TIMESTAMPTZ,
    state_changed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    watch_entered_at     TIMESTAMPTZ
);

-- ============================================================
-- Seed taxonomy: 7 top-level categories + ~30 leaf nodes
-- ============================================================

-- 1. Reasoning
INSERT INTO taxonomy_nodes (id, parent_id, name, description, level)
VALUES (1, NULL, 'Reasoning', 'Logical and analytical reasoning capabilities', 0)
ON CONFLICT DO NOTHING;

INSERT INTO taxonomy_nodes (parent_id, name, description, level) VALUES
    (1, 'Logical Deduction',       'Deriving conclusions from premises using formal logic', 1),
    (1, 'Mathematical Reasoning',  'Solving math problems and numerical reasoning', 1),
    (1, 'Causal Reasoning',        'Understanding cause-and-effect relationships', 1),
    (1, 'Analogical Reasoning',    'Drawing parallels between different domains', 1),
    (1, 'Multi-Step Planning',     'Breaking down complex problems into sequential steps', 1),
    (1, 'Counterfactual Reasoning','Reasoning about hypothetical alternative scenarios', 1)
ON CONFLICT DO NOTHING;

-- 2. Knowledge & Factuality
INSERT INTO taxonomy_nodes (id, parent_id, name, description, level)
VALUES (2, NULL, 'Knowledge & Factuality', 'Factual accuracy and world knowledge', 0)
ON CONFLICT DO NOTHING;

INSERT INTO taxonomy_nodes (parent_id, name, description, level) VALUES
    (2, 'World Knowledge',       'Broad factual knowledge across domains', 1),
    (2, 'Temporal Reasoning',    'Understanding time, dates, and temporal sequences', 1),
    (2, 'Source Attribution',    'Correctly attributing information to sources', 1),
    (2, 'Uncertainty Calibration','Expressing appropriate confidence levels', 1)
ON CONFLICT DO NOTHING;

-- 3. Language & Communication
INSERT INTO taxonomy_nodes (id, parent_id, name, description, level)
VALUES (3, NULL, 'Language & Communication', 'Natural language understanding and generation', 0)
ON CONFLICT DO NOTHING;

INSERT INTO taxonomy_nodes (parent_id, name, description, level) VALUES
    (3, 'Instruction Following', 'Accurately following complex multi-part instructions', 1),
    (3, 'Long-Form Generation',  'Producing coherent extended text passages', 1),
    (3, 'Summarization',         'Condensing information while preserving key points', 1),
    (3, 'Translation',           'Converting text between natural languages', 1),
    (3, 'Tone & Style Adaptation','Adjusting writing style, register, and tone', 1)
ON CONFLICT DO NOTHING;

-- 4. Code & Tool Use
INSERT INTO taxonomy_nodes (id, parent_id, name, description, level)
VALUES (4, NULL, 'Code & Tool Use', 'Programming and tool interaction capabilities', 0)
ON CONFLICT DO NOTHING;

INSERT INTO taxonomy_nodes (parent_id, name, description, level) VALUES
    (4, 'Code Generation',        'Writing correct code from natural language specs', 1),
    (4, 'Code Debugging',         'Finding and fixing bugs in existing code', 1),
    (4, 'API / Tool Calling',     'Correctly invoking APIs and external tools', 1),
    (4, 'Agentic Task Completion','Completing multi-step tasks with tool use', 1)
ON CONFLICT DO NOTHING;

-- 5. Multimodal
INSERT INTO taxonomy_nodes (id, parent_id, name, description, level)
VALUES (5, NULL, 'Multimodal', 'Cross-modal understanding and reasoning', 0)
ON CONFLICT DO NOTHING;

INSERT INTO taxonomy_nodes (parent_id, name, description, level) VALUES
    (5, 'Image Understanding',   'Interpreting and describing visual content', 1),
    (5, 'Audio Understanding',   'Processing and understanding audio content', 1),
    (5, 'Cross-Modal Reasoning', 'Reasoning across text, image, and audio modalities', 1)
ON CONFLICT DO NOTHING;

-- 6. Safety & Alignment
INSERT INTO taxonomy_nodes (id, parent_id, name, description, level)
VALUES (6, NULL, 'Safety & Alignment', 'Safety behaviors and value alignment', 0)
ON CONFLICT DO NOTHING;

INSERT INTO taxonomy_nodes (parent_id, name, description, level) VALUES
    (6, 'Harmful Content Refusal','Refusing to generate harmful or dangerous content', 1),
    (6, 'Bias & Fairness',        'Avoiding biased or discriminatory outputs', 1),
    (6, 'Privacy Protection',     'Protecting private and sensitive information', 1),
    (6, 'Jailbreak Resistance',   'Resisting prompt injection and jailbreak attempts', 1)
ON CONFLICT DO NOTHING;

-- 7. Meta-Cognitive
INSERT INTO taxonomy_nodes (id, parent_id, name, description, level)
VALUES (7, NULL, 'Meta-Cognitive', 'Self-awareness and metacognitive abilities', 0)
ON CONFLICT DO NOTHING;

INSERT INTO taxonomy_nodes (parent_id, name, description, level) VALUES
    (7, 'Self-Correction',           'Identifying and correcting own errors', 1),
    (7, 'Uncertainty Expression',    'Communicating uncertainty appropriately', 1),
    (7, 'Asking Clarifying Questions','Requesting clarification when instructions are ambiguous', 1),
    (7, 'Knowing Limitations',       'Recognizing the boundaries of own knowledge', 1)
ON CONFLICT DO NOTHING;

-- ============================================================
-- Seed taxonomy_eval_map: link existing 5 core evals to nodes
-- Uses subqueries to resolve IDs dynamically (safe if evals exist)
-- ============================================================

-- factuality-v1 → World Knowledge
INSERT INTO taxonomy_eval_map (taxonomy_id, eval_id)
SELECT t.id, e.id
FROM taxonomy_nodes t, eval_definitions e
WHERE t.name = 'World Knowledge' AND e.name = 'factuality-v1'
ON CONFLICT DO NOTHING;

-- reasoning-v1 → Logical Deduction
INSERT INTO taxonomy_eval_map (taxonomy_id, eval_id)
SELECT t.id, e.id
FROM taxonomy_nodes t, eval_definitions e
WHERE t.name = 'Logical Deduction' AND e.name = 'reasoning-v1'
ON CONFLICT DO NOTHING;

-- reasoning-v1 → Analogical Reasoning
INSERT INTO taxonomy_eval_map (taxonomy_id, eval_id)
SELECT t.id, e.id
FROM taxonomy_nodes t, eval_definitions e
WHERE t.name = 'Analogical Reasoning' AND e.name = 'reasoning-v1'
ON CONFLICT DO NOTHING;

-- safety-v1 → Harmful Content Refusal
INSERT INTO taxonomy_eval_map (taxonomy_id, eval_id)
SELECT t.id, e.id
FROM taxonomy_nodes t, eval_definitions e
WHERE t.name = 'Harmful Content Refusal' AND e.name = 'safety-v1'
ON CONFLICT DO NOTHING;

-- instruction-following-v1 → Instruction Following
INSERT INTO taxonomy_eval_map (taxonomy_id, eval_id)
SELECT t.id, e.id
FROM taxonomy_nodes t, eval_definitions e
WHERE t.name = 'Instruction Following' AND e.name = 'instruction-following-v1'
ON CONFLICT DO NOTHING;

-- code-gen-v1 → Code Generation
INSERT INTO taxonomy_eval_map (taxonomy_id, eval_id)
SELECT t.id, e.id
FROM taxonomy_nodes t, eval_definitions e
WHERE t.name = 'Code Generation' AND e.name = 'code-gen-v1'
ON CONFLICT DO NOTHING;
