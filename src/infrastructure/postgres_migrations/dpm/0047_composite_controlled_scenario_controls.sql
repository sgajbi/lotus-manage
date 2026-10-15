-- Additive controlled scenario graph. All 0046 acceptance predicates remain verbatim.
-- Current-issued declarations are synthetic only, never historical signature evidence.
ALTER TABLE dpm_composite_monthly_evaluation_proposals
    DROP CONSTRAINT monthly_evaluation_amendment_wire,
    ADD CONSTRAINT monthly_evaluation_amendment_wire CHECK ((COALESCE(
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
            AND payload_json->'policy_approval'->>'content_hash'=staged_policy_content_hash), FALSE)) OR COALESCE(
        (custody_mode='STAGED'
            AND payload_json->>'product_name'='CompositeSubjectEvaluationProposal'
            AND payload_json->>'product_version'='v3'
            AND payload_json->>'evaluation_kind'='INITIAL'
            AND NOT (payload_json ? 'amendment')
            AND payload_json->'policy_approval'->>'product_name'='CompositeSubjectPolicyApproval'
            AND payload_json->'policy_approval'->>'product_version'='v3'
            AND payload_json->'policy_approval'->'proposal'->>'product_name'='CompositeSubjectPolicyProposal'
            AND payload_json->'policy_approval'->'proposal'->>'product_version'='v3'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->>'product_name'='CompositeMonthlyPolicyProposal'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->>'product_version'='v3'
            AND payload_json->'policy_approval'->'approval'->>'product_name'='CompositeMonthlyPolicyApproval'
            AND payload_json->'policy_approval'->'approval'->>'product_version'='v3'
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'product_name'='CompositeEligibilitySubject'
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'product_version'='v1'
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'subject_revision'=subject_revision
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'content_hash'=subject_content_hash
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'tenant_id'=tenant_id
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'composite_id'=composite_id
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'definition_version'=definition_version
            AND payload_json->'policy_approval'->'proposal'->'subject'->>'month'=month
            AND payload_json->'operation_verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'operation_verification'->>'product_version'='v2'
            AND payload_json->'operation_verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_PROPOSAL'
            AND payload_json->'operation_verification'->'request'->>'purpose'='COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION'
            AND payload_json->'operation_verification'->'request'->>'revision'=evaluation_revision
            AND payload_json->'operation_verification'->'request'->>'month'=month
            AND payload_json->'operation_verification'->'request'->'scope'->>'tenant_id'=tenant_id
            AND payload_json->'operation_verification'->'request'->'scope'->>'composite_id'=composite_id
            AND payload_json->'operation_verification'->'request'->'scope'->>'definition_version'=definition_version
            AND payload_json->'operation_verification'->'request'->>'intent_digest' ~ '^sha256:[0-9a-f]{64}$'
            AND payload_json->'operation_verification'->'mapping'->>'content_hash'
                = payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'content_hash'
            AND payload_json->'policy_approval'->>'content_hash'=staged_policy_content_hash
            AND payload_json->'operation_verification'->>'original_signature_status'='VERIFIED_AT_ACTUAL_ISSUANCE'
            AND payload_json->'operation_verification'->>'signature_semantics'='SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE'
            AND payload_json->'operation_verification'->'request'->>'product_name'='CompositeHistoricalPolicyVerificationRequest'
            AND payload_json->'operation_verification'->'request'->>'product_version'='v2'
            AND NOT (payload_json->'operation_verification'->'mapping' ?| ARRAY['original_proposed_at','original_approved_at','original_proposed_by','original_approved_by'])
            AND payload_json->'operation_verification'->'mapping'->>'scenario_proposed_by' <> payload_json->'operation_verification'->'mapping'->>'scenario_approved_by'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_proposed_at' <= payload_json->'operation_verification'->'mapping'->>'scenario_approved_at'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_approved_at' < month || '-01T00:00:00.000000Z'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_approved_at' <= payload_json->'operation_verification'->'mapping'->>'actual_issued_at'
            AND payload_json->'operation_verification'->'mapping'->>'actual_issued_at' <= payload_json->'operation_verification'->'request'->>'requested_at'
            AND payload_json->'operation_verification'->'request'->>'requested_at' <= payload_json->'operation_verification'->>'admitted_at'
            AND payload_json->'operation_verification'->>'checked_at' <= payload_json->'operation_verification'->'request'->>'requested_at'
            AND payload_json->'operation_verification'->>'admitted_at' < payload_json->'operation_verification'->>'expires_at'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'original_signature_status'='VERIFIED_AT_ACTUAL_ISSUANCE'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'signature_semantics'='SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->'request'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->'request'->>'purpose'='COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'content_hash'=payload_json->'operation_verification'->'mapping'->>'content_hash'
            AND payload_json->'policy_approval'->'approval'->'verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'policy_approval'->'approval'->'verification'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'approval'->'verification'->>'original_signature_status'='VERIFIED_AT_ACTUAL_ISSUANCE'
            AND payload_json->'policy_approval'->'approval'->'verification'->>'signature_semantics'='SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE'
            AND payload_json->'policy_approval'->'approval'->'verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'policy_approval'->'approval'->'verification'->'request'->>'product_version'='v2'
            AND payload_json->'policy_approval'->'approval'->'verification'->'request'->>'purpose'='COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION'
            AND payload_json->'policy_approval'->'approval'->'verification'->'mapping'->>'content_hash'=payload_json->'operation_verification'->'mapping'->>'content_hash'
            AND payload_json->'policy_approval'->'approval'->'proposal'->>'product_version'='v3'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'current_revocation_status'='CLEAR'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'signer_principal_id' <> payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'verifier_principal_id'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'signer_key_digest' <> payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->>'verifier_key_digest'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'scenario_proposed_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'scenario_approved_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'actual_issued_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'policy_approval'->'approval'->'verification'->>'current_revocation_status'='CLEAR'
            AND payload_json->'policy_approval'->'approval'->'verification'->>'signer_principal_id' <> payload_json->'policy_approval'->'approval'->'verification'->>'verifier_principal_id'
            AND payload_json->'policy_approval'->'approval'->'verification'->>'signer_key_digest' <> payload_json->'policy_approval'->'approval'->'verification'->>'verifier_key_digest'
            AND payload_json->'policy_approval'->'approval'->'verification'->'mapping'->>'scenario_proposed_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'policy_approval'->'approval'->'verification'->'mapping'->>'scenario_approved_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'policy_approval'->'approval'->'verification'->'mapping'->>'actual_issued_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'operation_verification'->>'current_revocation_status'='CLEAR'
            AND payload_json->'operation_verification'->>'signer_principal_id' <> payload_json->'operation_verification'->>'verifier_principal_id'
            AND payload_json->'operation_verification'->>'signer_key_digest' <> payload_json->'operation_verification'->>'verifier_key_digest'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_proposed_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_approved_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'operation_verification'->'mapping'->>'actual_issued_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'), FALSE));

ALTER TABLE dpm_composite_monthly_evaluation_approvals
    DROP CONSTRAINT monthly_evaluation_approval_amendment_wire,
    ADD CONSTRAINT monthly_evaluation_approval_amendment_wire CHECK ((COALESCE(
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
                = payload_json->'proposal'->'operation_verification'->'mapping'->>'content_hash'), FALSE)) OR COALESCE(
        (custody_mode='STAGED'
            AND payload_json->'proposal'->>'product_name'='CompositeSubjectEvaluationProposal'
            AND payload_json->'proposal'->>'product_version'='v3'
            AND payload_json->'proposal'->>'evaluation_kind'='INITIAL'
            AND NOT (payload_json->'proposal' ? 'amendment')
            AND payload_json->'proposal'->'policy_approval'->>'product_name'='CompositeSubjectPolicyApproval'
            AND payload_json->'proposal'->'policy_approval'->>'product_version'='v3'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->>'product_name'='CompositeSubjectPolicyProposal'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->>'product_version'='v3'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->>'product_name'='CompositeMonthlyPolicyProposal'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->>'product_version'='v3'
            AND payload_json->'proposal'->'policy_approval'->'approval'->>'product_name'='CompositeMonthlyPolicyApproval'
            AND payload_json->'proposal'->'policy_approval'->'approval'->>'product_version'='v3'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'product_name'='CompositeEligibilitySubject'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'product_version'='v1'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'subject_revision'=subject_revision
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'content_hash'=subject_content_hash
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'tenant_id'=tenant_id
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'composite_id'=composite_id
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'definition_version'=definition_version
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'subject'->>'month'=month
            AND payload_json->'proposal'->'operation_verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'proposal'->'operation_verification'->>'product_version'='v2'
            AND payload_json->'proposal'->'operation_verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'operation'='EVALUATION_PROPOSAL'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'purpose'='COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'revision'=evaluation_revision
            AND payload_json->'proposal'->'operation_verification'->'request'->>'month'=month
            AND payload_json->'proposal'->'operation_verification'->'request'->'scope'->>'tenant_id'=tenant_id
            AND payload_json->'proposal'->'operation_verification'->'request'->'scope'->>'composite_id'=composite_id
            AND payload_json->'proposal'->'operation_verification'->'request'->'scope'->>'definition_version'=definition_version
            AND payload_json->'proposal'->'operation_verification'->'request'->>'intent_digest' ~ '^sha256:[0-9a-f]{64}$'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'content_hash'
                = payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'content_hash'
            AND payload_json->>'product_name'='CompositeSubjectEvaluationApproval'
            AND payload_json->>'product_version'='v3'
            AND NOT (payload_json ? 'amendment')
            AND payload_json->>'official_activation'='UNAVAILABLE'
            AND payload_json->'proposal'->>'content_hash'=staged_proposal_content_hash
            AND payload_json->'operation_verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'operation_verification'->>'product_version'='v2'
            AND payload_json->'operation_verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'operation_verification'->'request'->>'operation'='EVALUATION_APPROVAL'
            AND payload_json->'operation_verification'->'request'->>'purpose'='COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION'
            AND payload_json->'operation_verification'->'request'->>'intent_digest'=staged_proposal_content_hash
            AND payload_json->'operation_verification'->'request'->>'revision'=evaluation_revision
            AND payload_json->'operation_verification'->'request'->>'month'=month
            AND payload_json->'operation_verification'->'request'->'scope'->>'tenant_id'=tenant_id
            AND payload_json->'operation_verification'->'request'->'scope'->>'composite_id'=composite_id
            AND payload_json->'operation_verification'->'request'->'scope'->>'definition_version'=definition_version
            AND payload_json->'operation_verification'->'mapping'->>'content_hash'
                = payload_json->'proposal'->'operation_verification'->'mapping'->>'content_hash'
            AND payload_json->'proposal'->'operation_verification'->>'original_signature_status'='VERIFIED_AT_ACTUAL_ISSUANCE'
            AND payload_json->'proposal'->'operation_verification'->>'signature_semantics'='SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'product_name'='CompositeHistoricalPolicyVerificationRequest'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'product_version'='v2'
            AND NOT (payload_json->'proposal'->'operation_verification'->'mapping' ?| ARRAY['original_proposed_at','original_approved_at','original_proposed_by','original_approved_by'])
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'scenario_proposed_by' <> payload_json->'proposal'->'operation_verification'->'mapping'->>'scenario_approved_by'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'scenario_proposed_at' <= payload_json->'proposal'->'operation_verification'->'mapping'->>'scenario_approved_at'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'scenario_approved_at' < month || '-01T00:00:00.000000Z'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'scenario_approved_at' <= payload_json->'proposal'->'operation_verification'->'mapping'->>'actual_issued_at'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'actual_issued_at' <= payload_json->'proposal'->'operation_verification'->'request'->>'requested_at'
            AND payload_json->'proposal'->'operation_verification'->'request'->>'requested_at' <= payload_json->'proposal'->'operation_verification'->>'admitted_at'
            AND payload_json->'proposal'->'operation_verification'->>'checked_at' <= payload_json->'proposal'->'operation_verification'->'request'->>'requested_at'
            AND payload_json->'proposal'->'operation_verification'->>'admitted_at' < payload_json->'proposal'->'operation_verification'->>'expires_at'
            AND payload_json->'operation_verification'->>'original_signature_status'='VERIFIED_AT_ACTUAL_ISSUANCE'
            AND payload_json->'operation_verification'->>'signature_semantics'='SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE'
            AND payload_json->'operation_verification'->'request'->>'product_name'='CompositeHistoricalPolicyVerificationRequest'
            AND payload_json->'operation_verification'->'request'->>'product_version'='v2'
            AND NOT (payload_json->'operation_verification'->'mapping' ?| ARRAY['original_proposed_at','original_approved_at','original_proposed_by','original_approved_by'])
            AND payload_json->'operation_verification'->'mapping'->>'scenario_proposed_by' <> payload_json->'operation_verification'->'mapping'->>'scenario_approved_by'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_proposed_at' <= payload_json->'operation_verification'->'mapping'->>'scenario_approved_at'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_approved_at' < month || '-01T00:00:00.000000Z'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_approved_at' <= payload_json->'operation_verification'->'mapping'->>'actual_issued_at'
            AND payload_json->'operation_verification'->'mapping'->>'actual_issued_at' <= payload_json->'operation_verification'->'request'->>'requested_at'
            AND payload_json->'operation_verification'->'request'->>'requested_at' <= payload_json->'operation_verification'->>'admitted_at'
            AND payload_json->'operation_verification'->>'checked_at' <= payload_json->'operation_verification'->'request'->>'requested_at'
            AND payload_json->'operation_verification'->>'admitted_at' < payload_json->'operation_verification'->>'expires_at'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'original_signature_status'='VERIFIED_AT_ACTUAL_ISSUANCE'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'signature_semantics'='SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->'request'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->'request'->>'purpose'='COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'content_hash'=payload_json->'proposal'->'operation_verification'->'mapping'->>'content_hash'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'product_name'='CompositeHistoricalPolicyVerification'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'original_signature_status'='VERIFIED_AT_ACTUAL_ISSUANCE'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'signature_semantics'='SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'posture'='SYNTHETIC_NON_CERTIFYING'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->'request'->>'product_version'='v2'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->'request'->>'purpose'='COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->'mapping'->>'content_hash'=payload_json->'proposal'->'operation_verification'->'mapping'->>'content_hash'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'proposal'->>'product_version'='v3'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'current_revocation_status'='CLEAR'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'signer_principal_id' <> payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'verifier_principal_id'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'signer_key_digest' <> payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->>'verifier_key_digest'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'scenario_proposed_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'scenario_approved_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'proposal'->'policy_approval'->'proposal'->'proposal'->'verification'->'mapping'->>'actual_issued_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'current_revocation_status'='CLEAR'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'signer_principal_id' <> payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'verifier_principal_id'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'signer_key_digest' <> payload_json->'proposal'->'policy_approval'->'approval'->'verification'->>'verifier_key_digest'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->'mapping'->>'scenario_proposed_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->'mapping'->>'scenario_approved_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'proposal'->'policy_approval'->'approval'->'verification'->'mapping'->>'actual_issued_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'proposal'->'operation_verification'->>'current_revocation_status'='CLEAR'
            AND payload_json->'proposal'->'operation_verification'->>'signer_principal_id' <> payload_json->'proposal'->'operation_verification'->>'verifier_principal_id'
            AND payload_json->'proposal'->'operation_verification'->>'signer_key_digest' <> payload_json->'proposal'->'operation_verification'->>'verifier_key_digest'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'scenario_proposed_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'scenario_approved_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'proposal'->'operation_verification'->'mapping'->>'actual_issued_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'operation_verification'->>'current_revocation_status'='CLEAR'
            AND payload_json->'operation_verification'->>'signer_principal_id' <> payload_json->'operation_verification'->>'verifier_principal_id'
            AND payload_json->'operation_verification'->>'signer_key_digest' <> payload_json->'operation_verification'->>'verifier_key_digest'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_proposed_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'operation_verification'->'mapping'->>'scenario_approved_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'
            AND payload_json->'operation_verification'->'mapping'->>'actual_issued_at' ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{6}Z$'), FALSE));
