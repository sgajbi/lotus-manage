CREATE TABLE IF NOT EXISTS dpm_pm_quality_policies (
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    as_of_date TEXT NOT NULL,
    access_purpose TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (policy_id, policy_version)
);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_policy_enabled_as_of
ON dpm_pm_quality_policies (enabled, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_policy_as_of
ON dpm_pm_quality_policies (as_of_date, policy_id);
