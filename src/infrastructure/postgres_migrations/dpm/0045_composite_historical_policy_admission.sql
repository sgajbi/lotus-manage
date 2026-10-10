-- Extend existing ordinary custody only. Original applied checksums and rows are unchanged.
ALTER TABLE dpm_composite_monthly_evaluation_proposals
    DROP CONSTRAINT monthly_evaluation_amendment_wire,
    ADD CONSTRAINT monthly_evaluation_amendment_wire CHECK (COALESCE(
        (NOT (payload_json ? 'amendment')
            AND COALESCE(payload_json->>'product_version', 'v1')='v1'
            AND COALESCE(payload_json->'policy_approval'->>'product_version','v1')='v1'
            AND COALESCE(payload_json->'policy_approval'->'proposal'->>'product_version','v1')='v1')
        OR (custody_mode='LEGACY' AND payload_json->>'product_version' IN ('v2','v4')
            AND amendment_kind='SOURCE_CORRECTION'
            AND amendment_predecessor_revision IS NOT NULL
            AND amendment_predecessor_hash ~ '^sha256:[0-9a-f]{64}$'
            AND amendment_original_revision IS NOT NULL
            AND amendment_original_hash ~ '^sha256:[0-9a-f]{64}$'
            AND payload_json->'amendment'->'expected_authority_binding'
                = payload_json->'amendment'->'predecessor_approval_binding'
            AND ((payload_json->>'product_version'='v2'
                AND payload_json->'policy_approval'->>'product_version'='v1'
                AND payload_json->'amendment'->'original_approval_binding'->>'product_version' IN ('v1','v2')
                AND payload_json->'amendment'->'predecessor_approval_binding'->>'product_version' IN ('v1','v2'))
            OR (payload_json->>'product_version'='v4'
                AND payload_json->'policy_approval'->>'product_version'='v2'
                AND payload_json->'policy_approval'->'proposal'->>'product_version'='v2'
                AND payload_json->'amendment'->'original_approval_binding'->>'product_version'='v3'
                AND payload_json->'amendment'->'predecessor_approval_binding'->>'product_version' IN ('v3','v4')
                AND jsonb_typeof(payload_json->'operation_verification')='object'
                AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_PROPOSAL'))
            AND payload_json->'amendment'->'predecessor_receipt_binding'->>'product_version'
                = payload_json->'amendment'->'predecessor_approval_binding'->>'product_version')
        OR (custody_mode='LEGACY' AND payload_json->>'product_version'='v3'
            AND NOT (payload_json ? 'amendment')
            AND payload_json->'policy_approval'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'proposal'->>'product_version'='v2'
            AND jsonb_typeof(payload_json->'operation_verification')='object'
            AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_PROPOSAL'), FALSE));

ALTER TABLE dpm_composite_monthly_evaluation_approvals
    DROP CONSTRAINT monthly_evaluation_approval_amendment_wire,
    ADD CONSTRAINT monthly_evaluation_approval_amendment_wire CHECK (COALESCE(
        (NOT (payload_json->'proposal' ? 'amendment')
            AND COALESCE(payload_json->>'product_version', 'v1')='v1'
            AND COALESCE(payload_json->'proposal'->>'product_version', 'v1')='v1'
            AND COALESCE(payload_json->'proposal'->'policy_approval'->>'product_version','v1')='v1'
            AND COALESCE(payload_json->'proposal'->'policy_approval'->'proposal'->>'product_version','v1')='v1')
        OR (custody_mode='LEGACY' AND payload_json->>'product_version' IN ('v2','v4')
            AND payload_json->'proposal'->>'product_version'=payload_json->>'product_version'
            AND amendment_kind='SOURCE_CORRECTION'
            AND amendment_predecessor_revision IS NOT NULL
            AND amendment_predecessor_hash ~ '^sha256:[0-9a-f]{64}$'
            AND ((payload_json->>'product_version'='v2'
                AND payload_json->'proposal'->'policy_approval'->>'product_version'='v1')
                OR (payload_json->>'product_version'='v4'
                    AND payload_json->'proposal'->'policy_approval'->>'product_version'='v2'
                    AND payload_json->'proposal'->'policy_approval'->'proposal'->>'product_version'='v2'
                    AND jsonb_typeof(payload_json->'operation_verification')='object'
                    AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_APPROVAL')))
        OR (custody_mode='LEGACY' AND payload_json->>'product_version'='v3'
            AND payload_json->'proposal'->>'product_version'='v3'
            AND NOT (payload_json->'proposal' ? 'amendment')
            AND payload_json->'proposal'->'policy_approval'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->>'product_version'='v2'
            AND jsonb_typeof(payload_json->'operation_verification')='object'
            AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_APPROVAL'), FALSE));

ALTER TABLE dpm_composite_monthly_policy_proposals
    ADD CONSTRAINT monthly_policy_historical_wire CHECK (COALESCE(
        custody_mode='STAGED'
        OR (COALESCE(payload_json->>'product_version','v1')='v1'
            AND NOT (payload_json ? 'verification'))
        OR (custody_mode='LEGACY' AND payload_json->>'product_version'='v2'
            AND payload_json->>'product_name'='CompositeMonthlyPolicyProposal'
            AND jsonb_typeof(payload_json->'verification')='object'
            AND payload_json->'verification'->'request'->>'operation'='POLICY_PROPOSAL'
            AND payload_json->'verification'->'mapping'->'reference'->>'raw_digest' ~ '^sha256:[0-9a-f]{64}$'
            AND payload_json->'policy'->'scope'->>'tenant_id'=tenant_id
            AND payload_json->'policy'->'scope'->>'composite_id'=composite_id
            AND payload_json->'policy'->'scope'->>'definition_version'=definition_version
            AND payload_json->'policy'->>'month'=month), FALSE));

ALTER TABLE dpm_composite_monthly_policy_approvals
    ADD CONSTRAINT monthly_policy_historical_approval_wire CHECK (COALESCE(
        custody_mode='STAGED'
        OR (COALESCE(payload_json->>'product_version','v1')='v1'
            AND NOT (payload_json ? 'verification'))
        OR (custody_mode='LEGACY' AND payload_json->>'product_version'='v2'
            AND payload_json->>'product_name'='CompositeMonthlyPolicyApproval'
            AND payload_json->'proposal'->>'product_version'='v2'
            AND jsonb_typeof(payload_json->'verification')='object'
            AND payload_json->'verification'->'request'->>'operation'='POLICY_APPROVAL'
            AND payload_json->'verification'->'request'->>'intent_digest'=proposal_content_hash
            AND payload_json->>'official_activation'='UNAVAILABLE'), FALSE));
