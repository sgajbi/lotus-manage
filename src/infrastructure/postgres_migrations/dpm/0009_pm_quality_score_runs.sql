CREATE TABLE IF NOT EXISTS dpm_pm_quality_score_runs (
    score_run_id TEXT PRIMARY KEY,
    pm_id TEXT NOT NULL,
    book_id TEXT NULL,
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    state TEXT NOT NULL,
    score TEXT NULL,
    content_hash TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_pm_generated
ON dpm_pm_quality_score_runs (pm_id, generated_at);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_book_generated
ON dpm_pm_quality_score_runs (book_id, generated_at);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_policy_as_of
ON dpm_pm_quality_score_runs (policy_id, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_state_generated
ON dpm_pm_quality_score_runs (state, generated_at);
