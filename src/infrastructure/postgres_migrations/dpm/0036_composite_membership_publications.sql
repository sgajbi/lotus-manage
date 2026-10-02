CREATE TABLE IF NOT EXISTS dpm_composite_membership_publications (
    sequence BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    composite_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    membership_revision TEXT NOT NULL,
    membership_content_hash TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, sequence),
    UNIQUE (tenant_id, composite_id, definition_version, membership_revision),
    FOREIGN KEY (tenant_id, composite_id, definition_version, membership_revision)
        REFERENCES dpm_composite_membership_revisions
            (tenant_id, composite_id, definition_version, membership_revision)
);

CREATE INDEX IF NOT EXISTS idx_dpm_composite_publications_tenant_sequence
    ON dpm_composite_membership_publications (tenant_id, sequence);

-- This trigger is installed before the backfill. CREATE TRIGGER takes a table
-- lock that fences legacy application writers until this migration commits;
-- subsequent legacy INSERTs publish atomically even before every replica is
-- upgraded. The same per-tenant lock is used by the new repository writer so
-- tenant-visible sequence allocation follows commit order across versions.
CREATE FUNCTION dpm_publish_composite_membership_revision() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtext('dpm-composite-publication:' || NEW.tenant_id)::bigint
    );
    INSERT INTO dpm_composite_membership_publications (
        tenant_id, composite_id, definition_version, membership_revision,
        membership_content_hash
    ) VALUES (
        NEW.tenant_id, NEW.composite_id, NEW.definition_version,
        NEW.membership_revision, NEW.content_hash
    ) ON CONFLICT (tenant_id, composite_id, definition_version, membership_revision)
      DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE TRIGGER dpm_composite_membership_revision_publish
AFTER INSERT ON dpm_composite_membership_revisions
FOR EACH ROW EXECUTE FUNCTION dpm_publish_composite_membership_revision();

-- Existing immutable source revisions acquire a retrievable publication record.
-- The publication time is migration time, not the original decision time.
INSERT INTO dpm_composite_membership_publications (
    tenant_id, composite_id, definition_version, membership_revision,
    membership_content_hash
)
SELECT tenant_id, composite_id, definition_version, membership_revision, content_hash
FROM dpm_composite_membership_revisions
ORDER BY decided_at, tenant_id, composite_id, definition_version, membership_revision
ON CONFLICT (tenant_id, composite_id, definition_version, membership_revision) DO NOTHING;

CREATE TABLE IF NOT EXISTS dpm_composite_publication_receipts (
    tenant_id TEXT NOT NULL,
    publication_sequence BIGINT NOT NULL,
    consumer_id TEXT NOT NULL,
    membership_content_hash TEXT NOT NULL,
    receipt_evidence_hash TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK (disposition IN ('RECEIVED', 'REJECTED')),
    reason_code TEXT,
    received_at TIMESTAMPTZ NOT NULL,
    correlation_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, publication_sequence, consumer_id),
    FOREIGN KEY (tenant_id, publication_sequence)
        REFERENCES dpm_composite_membership_publications (tenant_id, sequence),
    CHECK ((disposition = 'RECEIVED' AND reason_code IS NULL)
        OR (disposition = 'REJECTED' AND reason_code IS NOT NULL))
);
