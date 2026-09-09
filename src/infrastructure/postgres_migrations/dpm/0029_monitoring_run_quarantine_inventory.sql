-- Monitoring runs have carried a nullable tenant_id since 0003. The NULL rows
-- remain deliberately quarantined, and the operator census must not turn the
-- common zero-row case into a full history scan as this table grows.
CREATE INDEX IF NOT EXISTS idx_dpm_monitoring_runs_null_tenant_inventory
    ON dpm_monitoring_runs (monitoring_run_id)
    WHERE tenant_id IS NULL;
