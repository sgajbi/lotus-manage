-- Forward-only extension: preserve every 0045 ordinary/LEGACY predicate.
-- Typed STAGED historical initial controls share existing subject/policy custody FKs.
-- Cryptographic verification and canonical hashes remain domain admission obligations.
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
            AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_PROPOSAL')
        OR (custody_mode='STAGED'
            AND payload_json->>'product_name'='CompositeSubjectEvaluationProposal'
            AND payload_json->>'product_version'='v2'
            AND payload_json->>'evaluation_kind'='INITIAL'
            AND NOT (payload_json ? 'amendment')
            AND payload_json->'policy_approval'->>'product_name'='CompositeSubjectPolicyApproval'
            AND payload_json->'policy_approval'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'proposal'->>'product_name'='CompositeSubjectPolicyProposal'
            AND payload_json->'policy_approval'->'proposal'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->>'product_name'='CompositeMonthlyPolicyProposal'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'approval'->>'product_name'='CompositeMonthlyPolicyApproval'
            AND payload_json->'policy_approval'->'approval'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'product_name'='CompositeEligibilitySubject'
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'product_version'='v1'
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'subject_revision'=subject_revision
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'content_hash'=subject_content_hash
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'tenant_id'=tenant_id
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'composite_id'=composite_id
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'definition_version'=definition_version
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'month'=month
            AND payload_json->'operation_verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'operation_verification'->>'product_version'='v1'
            AND payload_json->'operation_verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_PROPOSAL'
            AND payload_json->'operation_verification'->'request'->>'purpose'='COMPOSITE_HISTORICAL_MONTHLY_POLICY_ADMISSION'
            AND payload_json->'operation_verification'->'request'->>'revision'=evaluation_revision
            AND payload_json->'operation_verification'->'request'->>'month'=month
            AND payload_json->'operation_verification'->'request'->'scope'->>'tenant_id'=tenant_id
            AND payload_json->'operation_verification'->'request'->'scope'->>'composite_id'=composite_id
            AND payload_json->'operation_verification'->'request'->'scope'->>'definition_version'=definition_version
            AND payload_json->'operation_verification'->'request'->>'intent_digest' ~ '^sha256:[0-9a-f]{64}$'
            AND payload_json->'operation_verification'->'mapping'->>'content_hash'
                = payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'content_hash'
            AND payload_json->'policy_approval'->>'content_hash'=staged_policy_content_hash), FALSE));

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
            AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_APPROVAL')
        OR (custody_mode='STAGED'
            AND payload_json->'proposal'->>'product_name'='CompositeSubjectEvaluationProposal'
            AND payload_json->'proposal'->>'product_version'='v2'
            AND payload_json->'proposal'->>'evaluation_kind'='INITIAL'
            AND NOT (payload_json->'proposal' ? 'amendment')
            AND payload_json->'proposal'->'policy_approval'->>'product_name'='CompositeSubjectPolicyApproval'
            AND payload_json->'proposal'->'policy_approval'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->>'product_name'='CompositeSubjectPolicyProposal'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->>'product_name'='CompositeMonthlyPolicyProposal'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'approval'->>'product_name'='CompositeMonthlyPolicyApproval'
            AND payload_json->'proposal'->'policy_approval'->'approval'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'product_name'='CompositeEligibilitySubject'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'product_version'='v1'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'subject_revision'=subject_revision
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'content_hash'=subject_content_hash
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'tenant_id'=tenant_id
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'composite_id'=composite_id
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'definition_version'=definition_version
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'month'=month
            AND payload_json->'proposal'->'operation_verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'proposal'->'operation_verification'->>'product_version'='v1'
            AND payload_json->'proposal'->'operation_verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'operation'='EVALUATION_PROPOSAL'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'purpose'='COMPOSITE_HISTORICAL_MONTHLY_POLICY_ADMISSION'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'revision'=evaluation_revision
            AND payload_json->'proposal'->'operation_verification'->'request'->>'month'=month
            AND payload_json->'proposal'->'operation_verification'->'request'->'scope'->>'tenant_id'=tenant_id
            AND payload_json->'proposal'->'operation_verification'->'request'->'scope'->>'composite_id'=composite_id
            AND payload_json->'proposal'->'operation_verification'->'request'->'scope'->>'definition_version'=definition_version
            AND payload_json->'proposal'->'operation_verification'->'request'->>'intent_digest' ~ '^sha256:[0-9a-f]{64}$'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'content_hash'
                = payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'content_hash'
            AND payload_json->>'product_name'='CompositeSubjectEvaluationApproval'
            AND payload_json->>'product_version'='v2'
            AND NOT (payload_json ? 'amendment')
            AND payload_json->>'official_activation'='UNAVAILABLE'
            AND payload_json->'proposal'->>'content_hash'=staged_proposal_content_hash
            AND payload_json->'operation_verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'operation_verification'->>'product_version'='v1'
            AND payload_json->'operation_verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_APPROVAL'
            AND payload_json->'operation_verification'->'request'->>'purpose'='COMPOSITE_HISTORICAL_MONTHLY_POLICY_ADMISSION'
            AND payload_json->'operation_verification'->'request'->>'intent_digest'=staged_proposal_content_hash
            AND payload_json->'operation_verification'->'request'->>'revision'=evaluation_revision
            AND payload_json->'operation_verification'->'request'->>'month'=month
            AND payload_json->'operation_verification'->'request'->'scope'->>'tenant_id'=tenant_id
            AND payload_json->'operation_verification'->'request'->'scope'->>'composite_id'=composite_id
            AND payload_json->'operation_verification'->'request'->'scope'->>'definition_version'=definition_version
            AND payload_json->'operation_verification'->'mapping'->>'content_hash'
                = payload_json->'proposal'->'operation_verification'->'mapping'->>'content_hash'), FALSE));

