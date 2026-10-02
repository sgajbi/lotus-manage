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
