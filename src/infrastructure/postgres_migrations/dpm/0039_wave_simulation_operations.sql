CREATE TABLE IF NOT EXISTS dpm_wave_simulation_operations (
    operation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    wave_id TEXT NOT NULL REFERENCES dpm_rebalance_waves (wave_id) ON DELETE CASCADE,
    request_hash TEXT NOT NULL,
    idempotency_key_hash TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    source_identity_hash TEXT NOT NULL,
    admitted_wave_version INTEGER NOT NULL CHECK (admitted_wave_version > 0),
    methods_json JSONB NOT NULL,
    max_concurrency INTEGER NOT NULL CHECK (max_concurrency BETWEEN 1 AND 64),
    max_attempts INTEGER NOT NULL CHECK (max_attempts BETWEEN 1 AND 10),
    status TEXT NOT NULL CHECK (
        status IN (
            'PENDING', 'RUNNING', 'PARTIALLY_COMPLETED', 'SUCCEEDED', 'FAILED',
            'CANCEL_REQUESTED', 'CANCELLED'
        )
    ),
    cancel_reason_code TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, idempotency_key_hash),
    UNIQUE (tenant_id, correlation_id),
    UNIQUE (operation_id, tenant_id, wave_id)
);

CREATE INDEX IF NOT EXISTS idx_dpm_wave_simulation_operations_wave
    ON dpm_wave_simulation_operations (tenant_id, wave_id, created_at DESC);

CREATE TABLE IF NOT EXISTS dpm_wave_simulation_items (
    operation_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    wave_id TEXT NOT NULL,
    wave_item_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    portfolio_id TEXT NOT NULL,
    input_json JSONB NOT NULL,
    input_hash TEXT NOT NULL,
    source_identity_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')
    ),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    claim_generation INTEGER NOT NULL DEFAULT 0 CHECK (claim_generation >= 0),
    worker_id TEXT NULL,
    claim_token TEXT NULL,
    claimed_at TIMESTAMPTZ NULL,
    lease_expires_at TIMESTAMPTZ NULL,
    result_item_json JSONB NULL,
    error_code TEXT NULL,
    error_message TEXT NULL,
    retryable BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (operation_id, wave_item_id),
    FOREIGN KEY (operation_id, tenant_id, wave_id)
        REFERENCES dpm_wave_simulation_operations (operation_id, tenant_id, wave_id)
        ON DELETE CASCADE,
    UNIQUE (operation_id, ordinal),
    CHECK (
        status <> 'RUNNING'
        OR (
            worker_id IS NOT NULL
            AND claim_token IS NOT NULL
            AND claimed_at IS NOT NULL
            AND lease_expires_at IS NOT NULL
            AND attempt_count > 0
            AND claim_generation > 0
        )
    ),
    CHECK (status NOT IN ('SUCCEEDED', 'FAILED', 'CANCELLED') OR completed_at IS NOT NULL),
    CHECK (status <> 'SUCCEEDED' OR result_item_json IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_dpm_wave_simulation_items_claimable
    ON dpm_wave_simulation_items (operation_id, status, ordinal);

CREATE INDEX IF NOT EXISTS idx_dpm_wave_simulation_items_expired_lease
    ON dpm_wave_simulation_items (operation_id, lease_expires_at, ordinal)
    WHERE status = 'RUNNING';
