CREATE TABLE IF NOT EXISTS dpm_post_trade_outcome_reviews (
    outcome_review_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    mandate_id TEXT NULL,
    rebalance_run_id TEXT NULL,
    alternative_set_id TEXT NOT NULL,
    selected_alternative_id TEXT NOT NULL,
    proof_pack_id TEXT NOT NULL,
    wave_id TEXT NULL,
    wave_item_id TEXT NULL,
    state TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    idempotency_key TEXT NULL UNIQUE,
    retention_policy TEXT NOT NULL,
    retention_expires_at TEXT NULL,
    legal_hold_state TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    correlation_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_outcome_reviews_portfolio_created
ON dpm_post_trade_outcome_reviews (portfolio_id, created_at);

CREATE INDEX IF NOT EXISTS idx_dpm_outcome_reviews_wave_created
ON dpm_post_trade_outcome_reviews (wave_id, created_at);

CREATE INDEX IF NOT EXISTS idx_dpm_outcome_reviews_run
ON dpm_post_trade_outcome_reviews (rebalance_run_id);

CREATE INDEX IF NOT EXISTS idx_dpm_outcome_reviews_state_created
ON dpm_post_trade_outcome_reviews (state, created_at);

CREATE TABLE IF NOT EXISTS dpm_post_trade_outcome_events (
    event_id TEXT PRIMARY KEY,
    outcome_review_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_time TEXT NOT NULL,
    actor TEXT NOT NULL,
    state TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_outcome_events_review_time
ON dpm_post_trade_outcome_events (outcome_review_id, event_time);
