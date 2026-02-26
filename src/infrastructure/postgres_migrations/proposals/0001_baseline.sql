CREATE TABLE IF NOT EXISTS proposal_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    proposal_version_no INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposal_async_operations (
    operation_id TEXT PRIMARY KEY,
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    correlation_id TEXT NOT NULL UNIQUE,
    idempotency_key TEXT NULL,
    proposal_id TEXT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT NULL,
    finished_at TEXT NULL,
    result_json TEXT NULL,
    error_json TEXT NULL
);

CREATE TABLE IF NOT EXISTS proposal_records (
    proposal_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    mandate_id TEXT NULL,
    jurisdiction TEXT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_event_at TEXT NOT NULL,
    current_state TEXT NOT NULL,
    current_version_no INTEGER NOT NULL,
    title TEXT NULL,
    advisor_notes TEXT NULL
);

CREATE TABLE IF NOT EXISTS proposal_versions (
    proposal_version_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    version_no INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    simulation_hash TEXT NOT NULL,
    status_at_creation TEXT NOT NULL,
    proposal_result_json TEXT NOT NULL,
    artifact_json TEXT NOT NULL,
    evidence_bundle_json TEXT NOT NULL,
    gate_decision_json TEXT NULL,
    PRIMARY KEY (proposal_id, version_no)
);

CREATE TABLE IF NOT EXISTS proposal_workflow_events (
    event_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_state TEXT NULL,
    to_state TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    reason_json TEXT NOT NULL,
    related_version_no INTEGER NULL
);

CREATE TABLE IF NOT EXISTS proposal_approvals (
    approval_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    approval_type TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    details_json TEXT NOT NULL,
    related_version_no INTEGER NULL
);
