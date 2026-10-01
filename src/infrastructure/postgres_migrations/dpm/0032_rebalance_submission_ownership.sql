-- Tenant-scoped, crash-recoverable synchronous rebalance admission (issue #716).
--
-- Existing runs and mappings pre-date durable tenant ownership. They cannot be
-- attributed safely, so they remain present as quarantined legacy evidence and
-- are deliberately unreachable through tenant-scoped runtime reads.
ALTER TABLE dpm_runs
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NULL;

ALTER TABLE dpm_run_idempotency
    RENAME TO dpm_run_idempotency_legacy_unattributed;

ALTER TABLE dpm_run_idempotency_legacy_unattributed
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NULL;

CREATE TABLE dpm_run_idempotency (
    tenant_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    rebalance_run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, idempotency_key)
);

ALTER TABLE dpm_run_idempotency_history
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NULL;

ALTER TABLE dpm_lineage_edges
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NULL;

CREATE TABLE dpm_run_submission_claims (
    tenant_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    claim_token TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    claim_expires_at TEXT NOT NULL,
    rebalance_run_id TEXT NULL,
    completed_at TEXT NULL,
    PRIMARY KEY (tenant_id, idempotency_key),
    CHECK (status IN ('IN_PROGRESS', 'COMPLETED')),
    CHECK (
        (status = 'IN_PROGRESS' AND rebalance_run_id IS NULL AND completed_at IS NULL)
        OR
        (status = 'COMPLETED' AND rebalance_run_id IS NOT NULL AND completed_at IS NOT NULL)
    )
);

-- Correlation ids are caller-controlled and must not conflict across tenants.
ALTER TABLE dpm_runs
    DROP CONSTRAINT IF EXISTS dpm_runs_correlation_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_dpm_runs_tenant_correlation
    ON dpm_runs (tenant_id, correlation_id)
    WHERE tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_runs_tenant_created
    ON dpm_runs (tenant_id, created_at DESC, rebalance_run_id DESC);

CREATE INDEX IF NOT EXISTS idx_dpm_run_idempotency_history_tenant_key
    ON dpm_run_idempotency_history (tenant_id, idempotency_key, created_at);

CREATE INDEX IF NOT EXISTS idx_dpm_lineage_edges_tenant_source
    ON dpm_lineage_edges (tenant_id, source_entity_id, created_at);

CREATE INDEX IF NOT EXISTS idx_dpm_lineage_edges_tenant_target
    ON dpm_lineage_edges (tenant_id, target_entity_id, created_at);

-- Preserve bounded operator visibility of pre-ownership rows without making
-- any unverifiable tenant attribution. These partial indexes serve the
-- read-only quarantine inventory only.
CREATE INDEX IF NOT EXISTS idx_dpm_runs_null_tenant_inventory
    ON dpm_runs (rebalance_run_id)
    WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_run_idempotency_legacy_null_tenant_inventory
    ON dpm_run_idempotency_legacy_unattributed (idempotency_key)
    WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_run_idempotency_history_null_tenant_inventory
    ON dpm_run_idempotency_history (idempotency_key, created_at)
    WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_lineage_edges_null_tenant_inventory
    ON dpm_lineage_edges (source_entity_id, created_at)
    WHERE tenant_id IS NULL;
