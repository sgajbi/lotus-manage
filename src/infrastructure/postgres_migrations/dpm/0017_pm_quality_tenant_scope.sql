ALTER TABLE dpm_pm_quality_summary_invocations
DROP CONSTRAINT IF EXISTS fk_pm_quality_summary_invocations_score_run;

ALTER TABLE dpm_pm_quality_summary_invocations
DROP CONSTRAINT IF EXISTS fk_pm_quality_summary_invocations_review_action;

ALTER TABLE dpm_pm_quality_score_runs
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE dpm_pm_quality_policies
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE dpm_pm_quality_fairness_analyses
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE dpm_pm_quality_review_actions
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE dpm_pm_quality_summary_invocations
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

UPDATE dpm_pm_quality_score_runs
SET tenant_id = COALESCE(NULLIF(payload_json::jsonb ->> 'tenant_id', ''), 'legacy-default')
WHERE tenant_id IS NULL;

UPDATE dpm_pm_quality_score_runs
SET payload_json = jsonb_set(payload_json::jsonb, '{tenant_id}', to_jsonb(tenant_id), true)::text
WHERE payload_json::jsonb ->> 'tenant_id' IS DISTINCT FROM tenant_id;

UPDATE dpm_pm_quality_policies
SET tenant_id = COALESCE(NULLIF(payload_json::jsonb ->> 'tenant_id', ''), 'legacy-default')
WHERE tenant_id IS NULL;

UPDATE dpm_pm_quality_policies
SET payload_json = jsonb_set(payload_json::jsonb, '{tenant_id}', to_jsonb(tenant_id), true)::text
WHERE payload_json::jsonb ->> 'tenant_id' IS DISTINCT FROM tenant_id;

UPDATE dpm_pm_quality_fairness_analyses
SET tenant_id = COALESCE(NULLIF(payload_json::jsonb ->> 'tenant_id', ''), 'legacy-default')
WHERE tenant_id IS NULL;

UPDATE dpm_pm_quality_fairness_analyses
SET payload_json = jsonb_set(payload_json::jsonb, '{tenant_id}', to_jsonb(tenant_id), true)::text
WHERE payload_json::jsonb ->> 'tenant_id' IS DISTINCT FROM tenant_id;

UPDATE dpm_pm_quality_review_actions
SET tenant_id = COALESCE(NULLIF(payload_json::jsonb ->> 'tenant_id', ''), 'legacy-default')
WHERE tenant_id IS NULL;

UPDATE dpm_pm_quality_review_actions
SET payload_json = jsonb_set(payload_json::jsonb, '{tenant_id}', to_jsonb(tenant_id), true)::text
WHERE payload_json::jsonb ->> 'tenant_id' IS DISTINCT FROM tenant_id;

UPDATE dpm_pm_quality_summary_invocations
SET tenant_id = COALESCE(NULLIF(payload_json::jsonb ->> 'tenant_id', ''), 'legacy-default')
WHERE tenant_id IS NULL;

UPDATE dpm_pm_quality_summary_invocations
SET payload_json = jsonb_set(payload_json::jsonb, '{tenant_id}', to_jsonb(tenant_id), true)::text
WHERE payload_json::jsonb ->> 'tenant_id' IS DISTINCT FROM tenant_id;

ALTER TABLE dpm_pm_quality_score_runs
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE dpm_pm_quality_policies
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE dpm_pm_quality_fairness_analyses
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE dpm_pm_quality_review_actions
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE dpm_pm_quality_summary_invocations
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE dpm_pm_quality_score_runs
DROP CONSTRAINT IF EXISTS dpm_pm_quality_score_runs_pkey;

ALTER TABLE dpm_pm_quality_policies
DROP CONSTRAINT IF EXISTS dpm_pm_quality_policies_pkey;

ALTER TABLE dpm_pm_quality_fairness_analyses
DROP CONSTRAINT IF EXISTS dpm_pm_quality_fairness_analyses_pkey;

ALTER TABLE dpm_pm_quality_review_actions
DROP CONSTRAINT IF EXISTS dpm_pm_quality_review_actions_pkey;

ALTER TABLE dpm_pm_quality_summary_invocations
DROP CONSTRAINT IF EXISTS dpm_pm_quality_summary_invocations_pkey;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'dpm_pm_quality_score_runs_pkey'
          AND conrelid = 'dpm_pm_quality_score_runs'::regclass
    ) THEN
        ALTER TABLE dpm_pm_quality_score_runs
        ADD CONSTRAINT dpm_pm_quality_score_runs_pkey
        PRIMARY KEY (tenant_id, score_run_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'dpm_pm_quality_policies_pkey'
          AND conrelid = 'dpm_pm_quality_policies'::regclass
    ) THEN
        ALTER TABLE dpm_pm_quality_policies
        ADD CONSTRAINT dpm_pm_quality_policies_pkey
        PRIMARY KEY (tenant_id, policy_id, policy_version);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'dpm_pm_quality_fairness_analyses_pkey'
          AND conrelid = 'dpm_pm_quality_fairness_analyses'::regclass
    ) THEN
        ALTER TABLE dpm_pm_quality_fairness_analyses
        ADD CONSTRAINT dpm_pm_quality_fairness_analyses_pkey
        PRIMARY KEY (tenant_id, fairness_analysis_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'dpm_pm_quality_review_actions_pkey'
          AND conrelid = 'dpm_pm_quality_review_actions'::regclass
    ) THEN
        ALTER TABLE dpm_pm_quality_review_actions
        ADD CONSTRAINT dpm_pm_quality_review_actions_pkey
        PRIMARY KEY (tenant_id, review_action_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'dpm_pm_quality_summary_invocations_pkey'
          AND conrelid = 'dpm_pm_quality_summary_invocations'::regclass
    ) THEN
        ALTER TABLE dpm_pm_quality_summary_invocations
        ADD CONSTRAINT dpm_pm_quality_summary_invocations_pkey
        PRIMARY KEY (tenant_id, summary_invocation_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_pm_quality_summary_invocations_score_run'
          AND conrelid = 'dpm_pm_quality_summary_invocations'::regclass
    ) THEN
        ALTER TABLE dpm_pm_quality_summary_invocations
        ADD CONSTRAINT fk_pm_quality_summary_invocations_score_run
        FOREIGN KEY (tenant_id, score_run_id)
        REFERENCES dpm_pm_quality_score_runs(tenant_id, score_run_id)
        ON DELETE RESTRICT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_pm_quality_summary_invocations_review_action'
          AND conrelid = 'dpm_pm_quality_summary_invocations'::regclass
    ) THEN
        ALTER TABLE dpm_pm_quality_summary_invocations
        ADD CONSTRAINT fk_pm_quality_summary_invocations_review_action
        FOREIGN KEY (tenant_id, review_action_id)
        REFERENCES dpm_pm_quality_review_actions(tenant_id, review_action_id)
        ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_score_runs_tenant_pm_generated
ON dpm_pm_quality_score_runs (tenant_id, pm_id, generated_at);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_score_runs_tenant_book_generated
ON dpm_pm_quality_score_runs (tenant_id, book_id, generated_at);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_score_runs_tenant_policy_as_of
ON dpm_pm_quality_score_runs (tenant_id, policy_id, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_policies_tenant_enabled_as_of
ON dpm_pm_quality_policies (tenant_id, enabled, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_fairness_tenant_policy_as_of
ON dpm_pm_quality_fairness_analyses (tenant_id, policy_id, policy_version, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_review_actions_tenant_target
ON dpm_pm_quality_review_actions (tenant_id, target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_summary_tenant_score_run
ON dpm_pm_quality_summary_invocations (tenant_id, score_run_id);

CREATE INDEX IF NOT EXISTS idx_dpm_pm_quality_summary_tenant_review_action
ON dpm_pm_quality_summary_invocations (tenant_id, review_action_id);
