ALTER TABLE dpm_mandate_snapshots
    -- Issue #648. The mandate digital twin is the one DPM resource without
    -- tenant scope, while sibling resources in this service already carry it.
    --
    -- The column is deliberately left NULLABLE, and there is deliberately no
    -- backfill. Sibling migrations 0017 and 0018 attributed unknown rows to a
    -- 'legacy-default' tenant, which is not safe here: no source of verified
    -- attribution exists for these rows. The twin payload carries no tenant,
    -- and dpm_monitoring_runs.tenant_id is a run-level filter rather than a
    -- per-mandate fact, so any value chosen would be invented authority over
    -- client data.
    --
    -- Rows with a NULL tenant_id are QUARANTINED: every read filters on an
    -- explicit tenant, and NULL matches no filter, so a row that cannot be
    -- attributed becomes unreachable rather than visible to the wrong tenant.
    -- That is the fail-closed direction. Attributing them later is an operator
    -- action with evidence, not a migration default.
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE dpm_mandate_health_snapshots
    -- Same reasoning, same quarantine posture.
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE dpm_mandate_snapshots
    -- The identity constraint must include the tenant, or two tenants using
    -- the same mandate id, version and business date collide on one row -
    -- which is the isolation failure this issue exists to close, expressed as
    -- a constraint. Dropping the tenant-blind constraint from 0020 is required
    -- rather than additive: leaving it in place would keep rejecting the
    -- second tenant's legitimate row.
    DROP CONSTRAINT IF EXISTS dpm_mandate_snapshots_mandate_version_as_of_key;

ALTER TABLE dpm_mandate_snapshots
    -- Quarantined rows keep NULL here, and PostgreSQL treats NULLs as
    -- distinct, so they neither collide with each other nor block a
    -- tenant-scoped insert.
    ADD CONSTRAINT dpm_mandate_snapshots_tenant_identity_key
    UNIQUE (tenant_id, mandate_id, mandate_version, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_tenant_portfolio
    -- Reads filter on tenant first, so it leads the index.
    ON dpm_mandate_snapshots (tenant_id, portfolio_id, as_of_date DESC);

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_tenant_mandate
    ON dpm_mandate_snapshots (tenant_id, mandate_id, as_of_date DESC);

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_health_tenant_mandate
    ON dpm_mandate_health_snapshots (tenant_id, mandate_id, as_of_date DESC);
