-- Tenant-scope the rebalance wave aggregate (issue #677).
--
-- Waves carried no tenant at all: every wave was addressable by wave_id alone,
-- so a wave created under one tenant could be read, listed, and - the sharpest
-- of the three - source-checked or selected against by another. #676 added a
-- tenant argument to the MANDATE reads those paths perform, which made the
-- mandate evidence look correctly scoped while the wave itself was never that
-- caller's to touch. An unfenced read on the transition path leads to an
-- unfenced write.
--
-- This is not the same defect as wave idempotency, which #676 closed by
-- deriving the stored mapping key from the tenant (migration 0026). That path
-- is complete and must not be reimplemented here.
--
-- Nullable with no backfill, matching 0024, 0025 and 0026: a wave persisted
-- before the fence carries no tenant and is therefore matched by no equality
-- predicate - reachable from no tenant, including one literally named
-- `default` and the empty string. Assigning those rows an assumed tenant is
-- precisely what would let one tenant read waves it never created. They remain
-- present for deliberate attribution.
ALTER TABLE dpm_rebalance_waves
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NULL;

-- Reads are always (tenant, wave) or (tenant, filters); the tenant leads so the
-- index serves the fence rather than only the lookup.
CREATE INDEX IF NOT EXISTS idx_dpm_rebalance_waves_tenant_wave
    ON dpm_rebalance_waves (tenant_id, wave_id);

CREATE INDEX IF NOT EXISTS idx_dpm_rebalance_waves_tenant_created
    ON dpm_rebalance_waves (tenant_id, created_at DESC, wave_id DESC);

-- Fencing the reads is not enough while a key stays global. `correlation_id`
-- arrives on the caller's own X-Correlation-Id header and was unique across
-- every tenant, so a value one tenant had already used made another tenant's
-- legitimate create fail with a unique violation: a denial caused by data that
-- caller cannot see, and an existence oracle for a value it chose itself. The
-- uniqueness that was intended is per tenant. Migration 0026 made the same
-- correction for the caller-chosen idempotency key; this is the second and last
-- caller-supplied wave key that was still global.
DROP INDEX IF EXISTS idx_dpm_rebalance_waves_correlation;

-- Waves persisted before the fence carry tenant_id NULL, and PostgreSQL treats
-- NULLs as distinct in a unique index, so those rows are no longer constrained
-- against each other. They already satisfied the stricter global index and
-- save_wave stamps the tenant, so no new row can be written without one.
CREATE UNIQUE INDEX IF NOT EXISTS idx_dpm_rebalance_waves_tenant_correlation
    ON dpm_rebalance_waves (tenant_id, correlation_id);
