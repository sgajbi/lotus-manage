-- Additive configuration custody. Existing membership/universe/publication tables are unchanged.
CREATE TABLE IF NOT EXISTS dpm_composite_monthly_policy_proposals (
    tenant_id TEXT NOT NULL,
    composite_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    month TEXT NOT NULL CHECK (month ~ '^[0-9]{4}-[0-9]{2}$'),
    proposal_revision TEXT NOT NULL,
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^sha256:[0-9a-f]{64}$'),
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, composite_id, definition_version, month, proposal_revision),
    FOREIGN KEY (tenant_id, composite_id, definition_version)
        REFERENCES dpm_composite_definitions (tenant_id, composite_id, definition_version)
);

CREATE TABLE IF NOT EXISTS dpm_composite_monthly_policy_approvals (
    tenant_id TEXT NOT NULL,
    composite_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    month TEXT NOT NULL,
    proposal_revision TEXT NOT NULL,
    proposal_content_hash TEXT NOT NULL CHECK (proposal_content_hash ~ '^sha256:[0-9a-f]{64}$'),
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^sha256:[0-9a-f]{64}$'),
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, composite_id, month),
    FOREIGN KEY (tenant_id, composite_id, definition_version, month, proposal_revision)
        REFERENCES dpm_composite_monthly_policy_proposals
            (tenant_id, composite_id, definition_version, month, proposal_revision)
);
