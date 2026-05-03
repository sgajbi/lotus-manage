CREATE TABLE IF NOT EXISTS dpm_rebalance_waves (
    wave_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    wave_json JSONB NOT NULL,
    retention_policy TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dpm_rebalance_waves_correlation
    ON dpm_rebalance_waves (correlation_id);

CREATE INDEX IF NOT EXISTS idx_dpm_rebalance_waves_state_created
    ON dpm_rebalance_waves (state, created_at DESC);

CREATE TABLE IF NOT EXISTS dpm_rebalance_wave_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    wave_id TEXT NOT NULL REFERENCES dpm_rebalance_waves (wave_id) ON DELETE CASCADE,
    request_hash TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS dpm_rebalance_wave_events (
    event_id TEXT PRIMARY KEY,
    wave_id TEXT NOT NULL REFERENCES dpm_rebalance_waves (wave_id) ON DELETE CASCADE,
    from_state TEXT NULL,
    to_state TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    event_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_rebalance_wave_events_wave_created
    ON dpm_rebalance_wave_events (wave_id, created_at ASC);
