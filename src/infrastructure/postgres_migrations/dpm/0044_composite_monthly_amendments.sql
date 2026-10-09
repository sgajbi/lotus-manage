-- Retain approved monthly source amendments in the existing custody and publication estate.
-- LEGACY/STAGED mode still binds the original policy and staged finalization foreign keys.
ALTER TABLE dpm_composite_monthly_evaluation_proposals
    ADD COLUMN amendment_kind TEXT GENERATED ALWAYS AS
        (payload_json->'amendment'->>'correction_kind') STORED,
    ADD COLUMN amendment_predecessor_revision TEXT GENERATED ALWAYS AS
        (payload_json->'amendment'->'predecessor_approval_binding'->>'revision') STORED,
    ADD COLUMN amendment_predecessor_hash TEXT GENERATED ALWAYS AS
        (payload_json->'amendment'->'predecessor_approval_binding'->>'digest') STORED,
    ADD COLUMN amendment_original_revision TEXT GENERATED ALWAYS AS
        (payload_json->'amendment'->'original_approval_binding'->>'revision') STORED,
    ADD COLUMN amendment_original_hash TEXT GENERATED ALWAYS AS
        (payload_json->'amendment'->'original_approval_binding'->>'digest') STORED,
    ADD CONSTRAINT monthly_evaluation_amendment_wire CHECK (COALESCE(
        (NOT (payload_json ? 'amendment')
            AND COALESCE(payload_json->>'product_version', 'v1')='v1')
        OR (custody_mode='LEGACY' AND payload_json->>'product_version'='v2'
            AND amendment_kind='SOURCE_CORRECTION'
            AND amendment_predecessor_revision IS NOT NULL
            AND amendment_predecessor_hash ~ '^sha256:[0-9a-f]{64}$'
            AND amendment_original_revision IS NOT NULL
            AND amendment_original_hash ~ '^sha256:[0-9a-f]{64}$'
            AND payload_json->'amendment'->'expected_authority_binding'
                = payload_json->'amendment'->'predecessor_approval_binding'), FALSE));

ALTER TABLE dpm_composite_monthly_evaluation_approvals
    ADD COLUMN amendment_kind TEXT GENERATED ALWAYS AS
        (payload_json->'proposal'->'amendment'->>'correction_kind') STORED,
    ADD COLUMN amendment_predecessor_revision TEXT GENERATED ALWAYS AS
        (payload_json->'proposal'->'amendment'->'predecessor_approval_binding'->>'revision') STORED,
    ADD COLUMN amendment_predecessor_hash TEXT GENERATED ALWAYS AS
        (payload_json->'proposal'->'amendment'->'predecessor_approval_binding'->>'digest') STORED,
    ADD CONSTRAINT monthly_evaluation_approval_amendment_wire CHECK (COALESCE(
        (NOT (payload_json->'proposal' ? 'amendment')
            AND COALESCE(payload_json->>'product_version', 'v1')='v1'
            AND COALESCE(payload_json->'proposal'->>'product_version', 'v1')='v1')
        OR (custody_mode='LEGACY' AND payload_json->>'product_version'='v2'
            AND payload_json->'proposal'->>'product_version'='v2'
            AND amendment_kind='SOURCE_CORRECTION'
            AND amendment_predecessor_revision IS NOT NULL
            AND amendment_predecessor_hash ~ '^sha256:[0-9a-f]{64}$'), FALSE));

-- The old monthly primary key is the capability seam: it cannot retain a second approval.
-- Replace it with immutable revision identity without leaving a duplicate revision index.
ALTER TABLE dpm_composite_monthly_evaluation_approvals
    DROP CONSTRAINT dpm_composite_monthly_evaluation_approvals_pkey;
DO $$
DECLARE revision_unique TEXT;
BEGIN
    SELECT conname INTO STRICT revision_unique FROM pg_constraint
        WHERE conrelid='dpm_composite_monthly_evaluation_approvals'::regclass
        AND contype='u'
        AND pg_get_constraintdef(oid)=
            'UNIQUE (tenant_id, composite_id, definition_version, evaluation_revision)';
    EXECUTE format('ALTER TABLE dpm_composite_monthly_evaluation_approvals DROP CONSTRAINT %I', revision_unique);
END;
$$;
ALTER TABLE dpm_composite_monthly_evaluation_approvals
    ADD CONSTRAINT monthly_evaluation_approval_revision_identity PRIMARY KEY
        (tenant_id, composite_id, definition_version, evaluation_revision),
    ADD CONSTRAINT monthly_evaluation_approval_full_identity UNIQUE
        (tenant_id, composite_id, definition_version, month, evaluation_revision, content_hash),
    ADD CONSTRAINT monthly_evaluation_amendment_one_successor UNIQUE
        (tenant_id, composite_id, month, amendment_predecessor_hash),
    ADD CONSTRAINT monthly_evaluation_amendment_predecessor_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month,
            amendment_predecessor_revision, amendment_predecessor_hash)
        REFERENCES dpm_composite_monthly_evaluation_approvals
        (tenant_id, composite_id, definition_version, month, evaluation_revision, content_hash);

-- Ordinary and staged approvals continue to compete for one monthly root across definitions.
-- Pending proposals and explicit amendments cannot acquire that ordinary root slot.
CREATE UNIQUE INDEX monthly_evaluation_one_root
    ON dpm_composite_monthly_evaluation_approvals (tenant_id, composite_id, month)
    WHERE amendment_predecessor_hash IS NULL;

ALTER TABLE dpm_composite_monthly_evaluation_proposals
    ADD CONSTRAINT monthly_evaluation_proposal_predecessor_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month,
            amendment_predecessor_revision, amendment_predecessor_hash)
        REFERENCES dpm_composite_monthly_evaluation_approvals
        (tenant_id, composite_id, definition_version, month, evaluation_revision, content_hash),
    ADD CONSTRAINT monthly_evaluation_proposal_original_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month,
            amendment_original_revision, amendment_original_hash)
        REFERENCES dpm_composite_monthly_evaluation_approvals
        (tenant_id, composite_id, definition_version, month, evaluation_revision, content_hash);
