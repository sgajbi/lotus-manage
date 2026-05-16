CREATE TABLE IF NOT EXISTS dpm_pm_quality_fairness_analyses (
    fairness_analysis_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    state TEXT NOT NULL,
    observed_average_score_spread TEXT NULL,
    content_hash TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_fairness_policy_as_of
ON dpm_pm_quality_fairness_analyses (policy_id, policy_version, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_fairness_state_generated
ON dpm_pm_quality_fairness_analyses (state, generated_at);
