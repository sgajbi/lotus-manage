-- Add explicit tenant ownership without guessing owners for historical rows.
-- Existing NULL rows remain quarantined because every repository read uses tenant equality.

ALTER TABLE dpm_construction_alternative_sets
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE dpm_construction_alternative_selections
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE dpm_construction_alternative_sets
    DROP CONSTRAINT IF EXISTS dpm_construction_alternative_sets_idempotency_key_key;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dpm_construction_sets_tenant_idempotency
    ON dpm_construction_alternative_sets (tenant_id, idempotency_key)
    WHERE tenant_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dpm_construction_sets_id_tenant
    ON dpm_construction_alternative_sets (alternative_set_id, tenant_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_dpm_construction_selection_owner'
          AND conrelid = 'dpm_construction_alternative_selections'::regclass
    ) THEN
        ALTER TABLE dpm_construction_alternative_selections
            ADD CONSTRAINT fk_dpm_construction_selection_owner
            FOREIGN KEY (alternative_set_id, tenant_id)
            REFERENCES dpm_construction_alternative_sets (alternative_set_id, tenant_id);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_dpm_construction_sets_tenant_portfolio
    ON dpm_construction_alternative_sets (tenant_id, portfolio_id, created_at DESC)
    WHERE tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_construction_selections_tenant_set
    ON dpm_construction_alternative_selections (tenant_id, alternative_set_id)
    WHERE tenant_id IS NOT NULL;

-- Keep the operator quarantine inventory bounded as tenant-owned history grows.
CREATE INDEX IF NOT EXISTS idx_dpm_construction_sets_null_tenant_inventory
    ON dpm_construction_alternative_sets (alternative_set_id)
    WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_construction_selections_null_tenant_inventory
    ON dpm_construction_alternative_selections (selection_id)
    WHERE tenant_id IS NULL;
