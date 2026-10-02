ALTER TABLE dpm_composite_membership_revisions
    ADD CONSTRAINT uq_dpm_composite_membership_revision_content_hash
    UNIQUE (tenant_id, composite_id, definition_version, membership_revision, content_hash);

CREATE TABLE IF NOT EXISTS dpm_composite_universe_attestations (
    tenant_id TEXT NOT NULL,
    composite_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    membership_revision TEXT NOT NULL,
    membership_content_hash TEXT NOT NULL,
    attestation_version TEXT NOT NULL,
    attested_at TIMESTAMPTZ NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (
        tenant_id, composite_id, definition_version, membership_revision, attestation_version
    ),
    FOREIGN KEY (
        tenant_id, composite_id, definition_version, membership_revision,
        membership_content_hash
    )
        REFERENCES dpm_composite_membership_revisions
            (
                tenant_id, composite_id, definition_version, membership_revision,
                content_hash
            )
);

CREATE INDEX IF NOT EXISTS idx_dpm_composite_universe_attestations_revision_time
    ON dpm_composite_universe_attestations (
        tenant_id, composite_id, definition_version, membership_revision,
        attested_at DESC, attestation_version DESC
    );
