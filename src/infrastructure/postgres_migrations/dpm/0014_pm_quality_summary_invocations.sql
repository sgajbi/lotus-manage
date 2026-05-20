CREATE TABLE IF NOT EXISTS dpm_pm_quality_summary_invocations (
    summary_invocation_id TEXT PRIMARY KEY,
    score_run_id TEXT NOT NULL,
    review_action_id TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    invocation_state TEXT NOT NULL,
    summary_ref TEXT NOT NULL,
    workflow_pack_name TEXT NOT NULL,
    workflow_pack_version TEXT NOT NULL,
    workflow_run_id TEXT,
    summary_artifact_ref TEXT,
    summary_content_hash TEXT,
    content_hash TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_summary_invocations_score_run
ON dpm_pm_quality_summary_invocations (score_run_id);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_summary_invocations_review_action
ON dpm_pm_quality_summary_invocations (review_action_id);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_summary_invocations_policy_as_of
ON dpm_pm_quality_summary_invocations (policy_id, policy_version, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_summary_invocations_state_generated
ON dpm_pm_quality_summary_invocations (invocation_state, generated_at);
