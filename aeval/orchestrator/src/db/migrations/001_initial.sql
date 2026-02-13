-- aeval Phase 2: Initial schema
-- Runs automatically via TimescaleDB docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Models tracked from Ollama
CREATE TABLE IF NOT EXISTS models (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    family      TEXT NOT NULL DEFAULT '',
    param_size  TEXT NOT NULL DEFAULT '',
    quant       TEXT NOT NULL DEFAULT '',
    multimodal  BOOLEAN NOT NULL DEFAULT FALSE,
    digest      TEXT NOT NULL DEFAULT '',
    first_seen  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Eval definitions loaded from .py files
CREATE TABLE IF NOT EXISTS eval_definitions (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    file_path   TEXT NOT NULL DEFAULT '',
    tags        TEXT[] NOT NULL DEFAULT '{}',
    threshold   DOUBLE PRECISION,
    description TEXT NOT NULL DEFAULT '',
    metadata    JSONB NOT NULL DEFAULT '{}'
);

-- Eval runs (one per eval+model invocation)
CREATE TABLE IF NOT EXISTS eval_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_id         INTEGER NOT NULL REFERENCES eval_definitions(id),
    model_id        INTEGER NOT NULL REFERENCES models(id),
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    score           DOUBLE PRECISION,
    ci_lower        DOUBLE PRECISION,
    ci_upper        DOUBLE PRECISION,
    ci_level        DOUBLE PRECISION DEFAULT 0.95,
    num_tasks       INTEGER,
    passed          BOOLEAN,
    threshold       DOUBLE PRECISION,
    tier            TEXT,
    error           TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}',
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_eval_id ON eval_runs(eval_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_model_id ON eval_runs(model_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_status ON eval_runs(status);
CREATE INDEX IF NOT EXISTS idx_eval_runs_submitted ON eval_runs(submitted_at DESC);

-- Per-task results (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS eval_results (
    time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_id          UUID NOT NULL REFERENCES eval_runs(id),
    task_id         TEXT NOT NULL,
    score           DOUBLE PRECISION NOT NULL,
    passed          BOOLEAN,
    prediction      TEXT NOT NULL DEFAULT '',
    reference       TEXT NOT NULL DEFAULT '',
    latency_ms      DOUBLE PRECISION NOT NULL DEFAULT 0,
    tokens_used     INTEGER NOT NULL DEFAULT 0,
    metadata        JSONB NOT NULL DEFAULT '{}'
);

SELECT create_hypertable('eval_results', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_eval_results_run_id ON eval_results(run_id, time DESC);
