CREATE TABLE IF NOT EXISTS dpm_composite_definitions (
    tenant_id TEXT NOT NULL,
    composite_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    inception_date DATE NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, composite_id, definition_version)
);

CREATE INDEX IF NOT EXISTS idx_dpm_composite_definitions_tenant_inception
    ON dpm_composite_definitions (tenant_id, inception_date DESC, composite_id DESC, definition_version DESC);

CREATE TABLE IF NOT EXISTS dpm_composite_membership_revisions (
    tenant_id TEXT NOT NULL,
    composite_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    membership_revision TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, composite_id, definition_version, membership_revision),
    FOREIGN KEY (tenant_id, composite_id, definition_version)
        REFERENCES dpm_composite_definitions (tenant_id, composite_id, definition_version)
);

CREATE INDEX IF NOT EXISTS idx_dpm_composite_membership_revisions_tenant_definition_decided
    ON dpm_composite_membership_revisions (
        tenant_id, composite_id, definition_version, decided_at DESC, membership_revision DESC
    );
