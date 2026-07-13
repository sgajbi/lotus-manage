ALTER TABLE dpm_bulk_review_campaign_definitions
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

UPDATE dpm_bulk_review_campaign_definitions
SET tenant_id = COALESCE(NULLIF(payload_json ->> 'tenant_id', ''), 'legacy-default')
WHERE tenant_id IS NULL;

UPDATE dpm_bulk_review_campaign_definitions
SET payload_json = jsonb_set(payload_json, '{tenant_id}', to_jsonb(tenant_id), true)
WHERE payload_json ->> 'tenant_id' IS DISTINCT FROM tenant_id;

ALTER TABLE dpm_bulk_review_campaign_definitions
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE dpm_bulk_review_campaign_workflow_read_model
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

UPDATE dpm_bulk_review_campaign_workflow_read_model workflow
SET tenant_id = definitions.tenant_id
FROM dpm_bulk_review_campaign_definitions definitions
WHERE workflow.tenant_id IS NULL
  AND workflow.campaign_id = definitions.campaign_id
  AND workflow.campaign_version = definitions.campaign_version;

UPDATE dpm_bulk_review_campaign_workflow_read_model
SET tenant_id = 'legacy-default'
WHERE tenant_id IS NULL;

UPDATE dpm_bulk_review_campaign_workflow_read_model
SET projection_payload_json = jsonb_set(
    projection_payload_json,
    '{tenant_id}',
    to_jsonb(tenant_id),
    true
)
WHERE projection_payload_json ->> 'tenant_id' IS DISTINCT FROM tenant_id;

ALTER TABLE dpm_bulk_review_campaign_workflow_read_model
ALTER COLUMN tenant_id SET NOT NULL;

DO $$
DECLARE
    constraint_record record;
BEGIN
    FOR constraint_record IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'dpm_bulk_review_campaign_workflow_read_model'::regclass
          AND contype = 'f'
    LOOP
        EXECUTE format(
            'ALTER TABLE dpm_bulk_review_campaign_workflow_read_model DROP CONSTRAINT IF EXISTS %I',
            constraint_record.conname
        );
    END LOOP;
END $$;

ALTER TABLE dpm_bulk_review_campaign_workflow_read_model
DROP CONSTRAINT IF EXISTS dpm_bulk_review_campaign_workflow_read_model_pkey;

ALTER TABLE dpm_bulk_review_campaign_definitions
DROP CONSTRAINT IF EXISTS dpm_bulk_review_campaign_definitions_pkey;

ALTER TABLE dpm_bulk_review_campaign_definitions
ADD PRIMARY KEY (tenant_id, campaign_id, campaign_version);

ALTER TABLE dpm_bulk_review_campaign_workflow_read_model
ADD PRIMARY KEY (tenant_id, campaign_id, campaign_version);

ALTER TABLE dpm_bulk_review_campaign_workflow_read_model
ADD CONSTRAINT dpm_bulk_review_campaign_workflow_definition_fk
    FOREIGN KEY (tenant_id, campaign_id, campaign_version)
    REFERENCES dpm_bulk_review_campaign_definitions (tenant_id, campaign_id, campaign_version)
    ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_definitions_tenant_status
    ON dpm_bulk_review_campaign_definitions (tenant_id, status, as_of_date);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_tenant_board
    ON dpm_bulk_review_campaign_workflow_read_model (tenant_id, board_status);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_workflow_tenant_next_action
    ON dpm_bulk_review_campaign_workflow_read_model (tenant_id, next_action);
