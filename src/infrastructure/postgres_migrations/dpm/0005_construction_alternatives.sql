CREATE TABLE IF NOT EXISTS dpm_construction_alternative_sets (
    alternative_set_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    as_of TEXT NOT NULL,
    status TEXT NOT NULL,
    request_hash TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    input_mode TEXT NOT NULL,
    source_supportability_state TEXT,
    payload_json JSONB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_construction_alternative_sets_portfolio
    ON dpm_construction_alternative_sets (portfolio_id, created_at DESC);

CREATE TABLE IF NOT EXISTS dpm_construction_alternative_selections (
    selection_id TEXT PRIMARY KEY,
    alternative_set_id TEXT NOT NULL UNIQUE
        REFERENCES dpm_construction_alternative_sets (alternative_set_id),
    alternative_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    comment TEXT,
    correlation_id TEXT,
    payload_json JSONB NOT NULL,
    selected_at TEXT NOT NULL
);
