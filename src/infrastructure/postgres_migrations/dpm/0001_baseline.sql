CREATE TABLE IF NOT EXISTS dpm_runs (
    rebalance_run_id TEXT PRIMARY KEY,
    correlation_id TEXT NOT NULL UNIQUE,
    request_hash TEXT NOT NULL,
    idempotency_key TEXT NULL,
    portfolio_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    result_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dpm_run_artifacts (
    rebalance_run_id TEXT PRIMARY KEY,
    artifact_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dpm_run_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    rebalance_run_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dpm_run_idempotency_history (
    idempotency_key TEXT NOT NULL,
    rebalance_run_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dpm_async_operations (
    operation_id TEXT PRIMARY KEY,
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    correlation_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    started_at TEXT NULL,
    finished_at TEXT NULL,
    result_json TEXT NULL,
    error_json TEXT NULL,
    request_json TEXT NULL
);

CREATE TABLE IF NOT EXISTS dpm_workflow_decisions (
    decision_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    action TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    comment TEXT NULL,
    actor_id TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    correlation_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dpm_lineage_edges (
    source_entity_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
