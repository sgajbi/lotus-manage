ALTER TABLE dpm_monitoring_runs
    ADD COLUMN IF NOT EXISTS payload_json JSONB;
