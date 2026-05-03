CREATE TABLE IF NOT EXISTS dpm_mandate_snapshots (
    mandate_snapshot_id TEXT PRIMARY KEY,
    mandate_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    mandate_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    source_lineage_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    UNIQUE (mandate_id, mandate_version)
);

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_portfolio_as_of
ON dpm_mandate_snapshots (portfolio_id, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_mandate_created
ON dpm_mandate_snapshots (mandate_id, created_at);

CREATE TABLE IF NOT EXISTS dpm_mandate_health_snapshots (
    health_snapshot_id TEXT PRIMARY KEY,
    mandate_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    health_score INTEGER NOT NULL,
    health_state TEXT NOT NULL,
    top_reason_code TEXT,
    source_readiness_state TEXT NOT NULL,
    dimension_scores_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_health_portfolio_as_of
ON dpm_mandate_health_snapshots (portfolio_id, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_health_mandate_created
ON dpm_mandate_health_snapshots (mandate_id, created_at);

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_health_state_created
ON dpm_mandate_health_snapshots (health_state, created_at);

CREATE TABLE IF NOT EXISTS dpm_monitoring_runs (
    monitoring_run_id TEXT PRIMARY KEY,
    as_of_date TEXT NOT NULL,
    status TEXT NOT NULL,
    portfolio_manager_id TEXT,
    tenant_id TEXT,
    requested_by TEXT,
    filters_json TEXT NOT NULL,
    source_readiness_summary_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    failure_reason TEXT
);

CREATE TABLE IF NOT EXISTS dpm_monitoring_exceptions (
    exception_id TEXT PRIMARY KEY,
    monitoring_run_id TEXT,
    mandate_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    dimension TEXT NOT NULL,
    severity TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    state TEXT NOT NULL,
    measured_value_json TEXT,
    threshold_value_json TEXT,
    recommended_action TEXT NOT NULL,
    source_lineage_json TEXT NOT NULL,
    resolved_at TEXT,
    resolution_reason TEXT,
    resolved_by TEXT,
    payload_json TEXT NOT NULL,
    detected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_monitoring_exceptions_mandate_state
ON dpm_monitoring_exceptions (mandate_id, state);

CREATE INDEX IF NOT EXISTS idx_dpm_monitoring_exceptions_portfolio_state
ON dpm_monitoring_exceptions (portfolio_id, state);

CREATE INDEX IF NOT EXISTS idx_dpm_monitoring_exceptions_dimension_state
ON dpm_monitoring_exceptions (dimension, state);
