-- Issue #648. Monitoring exceptions are derived mandate-health evidence and
-- carry the same identifiers, so they need the same tenant fence. Without it
-- two tenants calculating health for the same portfolio, business date and
-- dimension derive the same exception_id, the second write replaces the
-- first's payload and state, and the unscoped list and resolve routes then
-- expose or mutate whichever record survived.
--
-- Nullable and NOT backfilled, for the same reason as the snapshot tenant in
-- 0024: no value would have been true. An unattributed row matches no equality
-- predicate, so it is quarantined rather than handed to whichever tenant a
-- default would have named, and remains present for an operator to attribute
-- deliberately.
ALTER TABLE dpm_monitoring_exceptions
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

-- Tenant-leading, because every read filters on it first.
CREATE INDEX IF NOT EXISTS idx_dpm_monitoring_exceptions_tenant_state
    ON dpm_monitoring_exceptions (tenant_id, state, detected_at DESC, exception_id DESC);

CREATE INDEX IF NOT EXISTS idx_dpm_monitoring_exceptions_tenant_mandate
    ON dpm_monitoring_exceptions (tenant_id, mandate_id, detected_at DESC);
