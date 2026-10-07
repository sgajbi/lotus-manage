-- Extend existing control custody. Legacy payloads and 0040/0041 checksums remain unchanged.
CREATE TABLE dpm_composite_eligibility_subjects (
    tenant_id TEXT NOT NULL, composite_id TEXT NOT NULL, definition_version TEXT NOT NULL,
    subject_revision TEXT NOT NULL, month TEXT NOT NULL CHECK (month ~ '^[0-9]{4}-[0-9]{2}$'),
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^sha256:[0-9a-f]{64}$'), payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, composite_id, definition_version, subject_revision),
    UNIQUE (tenant_id, composite_id, definition_version),
    UNIQUE (tenant_id, composite_id, definition_version, subject_revision, content_hash)
);

ALTER TABLE dpm_composite_monthly_policy_proposals
    ADD COLUMN subject_revision TEXT,
    ADD COLUMN subject_content_hash TEXT,
    ADD COLUMN custody_mode TEXT GENERATED ALWAYS AS
        (CASE WHEN subject_revision IS NULL THEN 'LEGACY' ELSE 'STAGED' END) STORED NOT NULL,
    ADD COLUMN retained_definition_version TEXT GENERATED ALWAYS AS
        (CASE WHEN subject_revision IS NULL THEN definition_version ELSE NULL END) STORED,
    ADD CONSTRAINT monthly_policy_subject_pair CHECK (
        (subject_revision IS NULL AND subject_content_hash IS NULL) OR
        (subject_revision IS NOT NULL AND subject_content_hash IS NOT NULL)),
    ADD CONSTRAINT monthly_policy_subject_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, subject_revision, subject_content_hash)
        REFERENCES dpm_composite_eligibility_subjects
        (tenant_id, composite_id, definition_version, subject_revision, content_hash),
    ADD CONSTRAINT monthly_policy_proposal_subject_identity UNIQUE
        (tenant_id, composite_id, definition_version, month, proposal_revision, content_hash, subject_revision, subject_content_hash),
    ADD CONSTRAINT monthly_policy_proposal_mode_identity UNIQUE
        (tenant_id, composite_id, definition_version, month, proposal_revision, content_hash, custody_mode);
DO $$
DECLARE legacy_fk TEXT;
BEGIN
    SELECT conname INTO STRICT legacy_fk FROM pg_constraint
        WHERE conrelid='dpm_composite_monthly_policy_proposals'::regclass
        AND confrelid='dpm_composite_definitions'::regclass AND contype='f';
    EXECUTE format('ALTER TABLE dpm_composite_monthly_policy_proposals DROP CONSTRAINT %I', legacy_fk);
END;
$$;
ALTER TABLE dpm_composite_monthly_policy_proposals
    ADD CONSTRAINT monthly_policy_retained_definition_fk FOREIGN KEY
        (tenant_id, composite_id, retained_definition_version)
        REFERENCES dpm_composite_definitions (tenant_id, composite_id, definition_version);

ALTER TABLE dpm_composite_monthly_policy_approvals
    ADD COLUMN subject_revision TEXT, ADD COLUMN subject_content_hash TEXT,
    ADD COLUMN custody_mode TEXT GENERATED ALWAYS AS
        (CASE WHEN subject_revision IS NULL THEN 'LEGACY' ELSE 'STAGED' END) STORED NOT NULL,
    ADD CONSTRAINT monthly_policy_approval_subject_pair CHECK (
        (subject_revision IS NULL AND subject_content_hash IS NULL) OR
        (subject_revision IS NOT NULL AND subject_content_hash IS NOT NULL)),
    ADD CONSTRAINT monthly_policy_approval_subject_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month, proposal_revision, proposal_content_hash, subject_revision, subject_content_hash)
        REFERENCES dpm_composite_monthly_policy_proposals
        (tenant_id, composite_id, definition_version, month, proposal_revision, content_hash, subject_revision, subject_content_hash),
    ADD CONSTRAINT monthly_policy_approval_subject_identity UNIQUE
        (tenant_id, composite_id, definition_version, month, subject_revision, subject_content_hash, content_hash),
    ADD CONSTRAINT monthly_policy_approval_mode_identity UNIQUE
        (tenant_id, composite_id, definition_version, month, custody_mode, content_hash),
    ADD CONSTRAINT monthly_policy_approval_mode_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month, proposal_revision, proposal_content_hash, custody_mode)
        REFERENCES dpm_composite_monthly_policy_proposals
        (tenant_id, composite_id, definition_version, month, proposal_revision, content_hash, custody_mode);

ALTER TABLE dpm_composite_monthly_evaluation_proposals
    ADD COLUMN subject_revision TEXT, ADD COLUMN subject_content_hash TEXT, ADD COLUMN staged_policy_content_hash TEXT,
    ADD COLUMN custody_mode TEXT GENERATED ALWAYS AS
        (CASE WHEN subject_revision IS NULL THEN 'LEGACY' ELSE 'STAGED' END) STORED NOT NULL,
    ADD COLUMN policy_content_hash TEXT GENERATED ALWAYS AS
        (payload_json->'policy_approval'->>'content_hash') STORED NOT NULL,
    ALTER COLUMN parent_membership_revision DROP NOT NULL,
    ADD CONSTRAINT monthly_evaluation_subject_parent CHECK (
        (subject_revision IS NULL AND subject_content_hash IS NULL AND staged_policy_content_hash IS NULL
            AND parent_membership_revision IS NOT NULL) OR
        (subject_revision IS NOT NULL AND subject_content_hash IS NOT NULL AND staged_policy_content_hash IS NOT NULL
            AND parent_membership_revision IS NULL)),
    ADD CONSTRAINT monthly_evaluation_subject_policy_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month, subject_revision, subject_content_hash, staged_policy_content_hash)
        REFERENCES dpm_composite_monthly_policy_approvals
        (tenant_id, composite_id, definition_version, month, subject_revision, subject_content_hash, content_hash),
    ADD CONSTRAINT monthly_evaluation_subject_identity UNIQUE
        (tenant_id, composite_id, definition_version, month, evaluation_revision, content_hash, subject_revision, subject_content_hash),
    ADD CONSTRAINT monthly_evaluation_mode_identity UNIQUE
        (tenant_id, composite_id, definition_version, month, evaluation_revision, content_hash, custody_mode),
    ADD CONSTRAINT monthly_evaluation_policy_mode_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month, custody_mode, policy_content_hash)
        REFERENCES dpm_composite_monthly_policy_approvals
        (tenant_id, composite_id, definition_version, month, custody_mode, content_hash),
    ADD CONSTRAINT monthly_evaluation_policy_hash_match CHECK
        (subject_revision IS NULL OR staged_policy_content_hash=policy_content_hash);

ALTER TABLE dpm_composite_monthly_evaluation_approvals
    ADD COLUMN subject_revision TEXT, ADD COLUMN subject_content_hash TEXT, ADD COLUMN staged_proposal_content_hash TEXT,
    ADD COLUMN custody_mode TEXT GENERATED ALWAYS AS
        (CASE WHEN subject_revision IS NULL THEN 'LEGACY' ELSE 'STAGED' END) STORED NOT NULL,
    ADD COLUMN evaluation_proposal_content_hash TEXT GENERATED ALWAYS AS
        (payload_json->'proposal'->>'content_hash') STORED NOT NULL,
    ADD COLUMN retained_membership_revision TEXT GENERATED ALWAYS AS
        (CASE WHEN subject_revision IS NULL THEN membership_revision ELSE NULL END) STORED,
    ADD CONSTRAINT monthly_evaluation_approval_subject_pair CHECK (
        (subject_revision IS NULL AND subject_content_hash IS NULL AND staged_proposal_content_hash IS NULL) OR
        (subject_revision IS NOT NULL AND subject_content_hash IS NOT NULL AND staged_proposal_content_hash IS NOT NULL)),
    ADD CONSTRAINT monthly_evaluation_approval_subject_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month, evaluation_revision, staged_proposal_content_hash, subject_revision, subject_content_hash)
        REFERENCES dpm_composite_monthly_evaluation_proposals
        (tenant_id, composite_id, definition_version, month, evaluation_revision, content_hash, subject_revision, subject_content_hash),
    ADD CONSTRAINT monthly_evaluation_approval_subject_identity UNIQUE
        (tenant_id, composite_id, definition_version, subject_revision, subject_content_hash, evaluation_revision, content_hash),
    ADD CONSTRAINT monthly_evaluation_approval_mode_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, month, evaluation_revision, evaluation_proposal_content_hash, custody_mode)
        REFERENCES dpm_composite_monthly_evaluation_proposals
        (tenant_id, composite_id, definition_version, month, evaluation_revision, content_hash, custody_mode),
    ADD CONSTRAINT monthly_evaluation_approval_hash_match CHECK
        (subject_revision IS NULL OR staged_proposal_content_hash=evaluation_proposal_content_hash);
DO $$
DECLARE legacy_fk TEXT;
BEGIN
    SELECT conname INTO STRICT legacy_fk FROM pg_constraint
        WHERE conrelid='dpm_composite_monthly_evaluation_approvals'::regclass
        AND confrelid='dpm_composite_membership_revisions'::regclass AND contype='f';
    EXECUTE format('ALTER TABLE dpm_composite_monthly_evaluation_approvals DROP CONSTRAINT %I', legacy_fk);
END;
$$;
ALTER TABLE dpm_composite_monthly_evaluation_approvals
    ADD CONSTRAINT monthly_evaluation_retained_membership_fk FOREIGN KEY
        (tenant_id, composite_id, definition_version, retained_membership_revision)
        REFERENCES dpm_composite_membership_revisions
        (tenant_id, composite_id, definition_version, membership_revision);

ALTER TABLE dpm_composite_definitions ADD CONSTRAINT composite_definition_hash_identity
    UNIQUE (tenant_id, composite_id, definition_version, content_hash);
ALTER TABLE dpm_composite_universe_attestations ADD CONSTRAINT composite_universe_hash_identity
    UNIQUE (tenant_id, composite_id, definition_version, membership_revision, attestation_version, content_hash);
ALTER TABLE dpm_composite_membership_publications ADD CONSTRAINT composite_publication_full_identity
    UNIQUE (tenant_id, composite_id, definition_version, membership_revision, membership_content_hash, sequence);

CREATE TABLE dpm_composite_eligibility_finalizations (
    tenant_id TEXT NOT NULL, composite_id TEXT NOT NULL, definition_version TEXT NOT NULL,
    subject_revision TEXT NOT NULL, subject_content_hash TEXT NOT NULL,
    evaluation_revision TEXT NOT NULL, approval_content_hash TEXT NOT NULL,
    definition_content_hash TEXT NOT NULL, membership_revision TEXT NOT NULL, membership_content_hash TEXT NOT NULL,
    universe_content_hash TEXT NOT NULL, publication_sequence BIGINT NOT NULL,
    content_hash TEXT NOT NULL, payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, composite_id, definition_version, subject_revision),
    FOREIGN KEY (tenant_id, composite_id, definition_version, subject_revision, subject_content_hash)
        REFERENCES dpm_composite_eligibility_subjects
        (tenant_id, composite_id, definition_version, subject_revision, content_hash),
    FOREIGN KEY (tenant_id, composite_id, definition_version, subject_revision, subject_content_hash, evaluation_revision, approval_content_hash)
        REFERENCES dpm_composite_monthly_evaluation_approvals
        (tenant_id, composite_id, definition_version, subject_revision, subject_content_hash, evaluation_revision, content_hash),
    FOREIGN KEY (tenant_id, composite_id, definition_version, definition_content_hash)
        REFERENCES dpm_composite_definitions (tenant_id, composite_id, definition_version, content_hash),
    FOREIGN KEY (tenant_id, composite_id, definition_version, membership_revision, membership_content_hash)
        REFERENCES dpm_composite_membership_revisions
        (tenant_id, composite_id, definition_version, membership_revision, content_hash),
    FOREIGN KEY (tenant_id, composite_id, definition_version, membership_revision, evaluation_revision, universe_content_hash)
        REFERENCES dpm_composite_universe_attestations
        (tenant_id, composite_id, definition_version, membership_revision, attestation_version, content_hash),
    FOREIGN KEY (tenant_id, composite_id, definition_version, membership_revision, membership_content_hash, publication_sequence)
        REFERENCES dpm_composite_membership_publications
        (tenant_id, composite_id, definition_version, membership_revision, membership_content_hash, sequence)
);

-- Serialize reservations with all old/new publication writers. A reserved definition cannot
-- become visible without its exact finalization receipt in the same transaction.
CREATE FUNCTION dpm_reserve_composite_eligibility_subject() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('dpm-composite-publication:' || NEW.tenant_id)::bigint);
    IF EXISTS (SELECT 1 FROM dpm_composite_definitions WHERE tenant_id=NEW.tenant_id
        AND composite_id=NEW.composite_id AND definition_version=NEW.definition_version) THEN
        RAISE EXCEPTION 'COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER dpm_composite_subject_reservation BEFORE INSERT ON dpm_composite_eligibility_subjects
    FOR EACH ROW EXECUTE FUNCTION dpm_reserve_composite_eligibility_subject();

CREATE TRIGGER dpm_composite_definition_publication_lock BEFORE INSERT ON dpm_composite_definitions
    FOR EACH ROW EXECUTE FUNCTION dpm_lock_composite_membership_publication();

CREATE FUNCTION dpm_require_composite_eligibility_finalization() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM dpm_composite_eligibility_subjects WHERE tenant_id=NEW.tenant_id
        AND composite_id=NEW.composite_id AND definition_version=NEW.definition_version)
        AND NOT EXISTS (SELECT 1 FROM dpm_composite_eligibility_finalizations WHERE tenant_id=NEW.tenant_id
        AND composite_id=NEW.composite_id AND definition_version=NEW.definition_version
        AND definition_content_hash=NEW.content_hash) THEN
        RAISE EXCEPTION 'COMPOSITE_SUBJECT_FINALIZATION_REQUIRED';
    END IF;
    RETURN NEW;
END;
$$;
CREATE CONSTRAINT TRIGGER dpm_composite_reserved_definition_finalization AFTER INSERT ON dpm_composite_definitions
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION dpm_require_composite_eligibility_finalization();
