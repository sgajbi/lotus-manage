CREATE TABLE IF NOT EXISTS dpm_pm_quality_review_actions (
    review_action_id TEXT PRIMARY KEY,
    review_action_ref TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    target_state TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_state TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_review_actions_target
ON dpm_pm_quality_review_actions (target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_review_actions_policy_as_of
ON dpm_pm_quality_review_actions (policy_id, policy_version, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_review_actions_state_generated
ON dpm_pm_quality_review_actions (action_state, generated_at);
