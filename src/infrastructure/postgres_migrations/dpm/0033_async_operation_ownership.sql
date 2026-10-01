ALTER TABLE dpm_async_operations
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NULL;

ALTER TABLE dpm_async_operations
    ADD COLUMN IF NOT EXISTS execution_token TEXT NULL;

ALTER TABLE dpm_async_operations
    ADD COLUMN IF NOT EXISTS execution_attempt INTEGER NOT NULL DEFAULT 0;

ALTER TABLE dpm_async_operations
    ADD COLUMN IF NOT EXISTS execution_claimed_at TEXT NULL;

ALTER TABLE dpm_async_operations
    ADD COLUMN IF NOT EXISTS execution_lease_expires_at TEXT NULL;

ALTER TABLE dpm_async_operations
    ADD CONSTRAINT dpm_async_operations_execution_attempt_nonnegative
    CHECK (execution_attempt >= 0) NOT VALID;

ALTER TABLE dpm_async_operations
    ADD CONSTRAINT dpm_async_operations_running_owner_complete
    CHECK (
        tenant_id IS NULL
        OR status <> 'RUNNING'
        OR (
            execution_token IS NOT NULL
            AND execution_attempt > 0
            AND execution_claimed_at IS NOT NULL
            AND execution_lease_expires_at IS NOT NULL
        )
    ) NOT VALID;

ALTER TABLE dpm_async_operations
    VALIDATE CONSTRAINT dpm_async_operations_execution_attempt_nonnegative;

ALTER TABLE dpm_async_operations
    VALIDATE CONSTRAINT dpm_async_operations_running_owner_complete;

ALTER TABLE dpm_async_operations
    DROP CONSTRAINT IF EXISTS dpm_async_operations_correlation_id_key;

CREATE INDEX IF NOT EXISTS idx_dpm_async_operations_tenant_operation
    ON dpm_async_operations (tenant_id, operation_id)
    WHERE tenant_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dpm_async_operations_tenant_correlation
    ON dpm_async_operations (tenant_id, correlation_id)
    WHERE tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_async_operations_recoverable_lease
    ON dpm_async_operations (execution_lease_expires_at, operation_id)
    WHERE status = 'RUNNING';

CREATE INDEX IF NOT EXISTS idx_dpm_async_operations_legacy_quarantine
    ON dpm_async_operations (operation_id)
    WHERE tenant_id IS NULL;
