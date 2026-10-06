-- Evidence custody only; membership authority remains the existing composite ledger.
CREATE TABLE IF NOT EXISTS dpm_composite_monthly_evaluation_proposals (
    tenant_id TEXT NOT NULL,
    composite_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    evaluation_revision TEXT NOT NULL,
    month TEXT NOT NULL,
    parent_membership_revision TEXT NOT NULL,
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^sha256:[0-9a-f]{64}$'),
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, composite_id, definition_version, evaluation_revision),
    FOREIGN KEY (tenant_id, composite_id, definition_version, parent_membership_revision)
        REFERENCES dpm_composite_membership_revisions
            (tenant_id, composite_id, definition_version, membership_revision),
    FOREIGN KEY (tenant_id, composite_id, month)
        REFERENCES dpm_composite_monthly_policy_approvals (tenant_id, composite_id, month)
);

CREATE TABLE IF NOT EXISTS dpm_composite_monthly_evaluation_approvals (
    tenant_id TEXT NOT NULL,
    composite_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    month TEXT NOT NULL,
    evaluation_revision TEXT NOT NULL,
    membership_revision TEXT NOT NULL,
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^sha256:[0-9a-f]{64}$'),
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, composite_id, month),
    UNIQUE (tenant_id, composite_id, definition_version, evaluation_revision),
    FOREIGN KEY (tenant_id, composite_id, definition_version, evaluation_revision)
        REFERENCES dpm_composite_monthly_evaluation_proposals
            (tenant_id, composite_id, definition_version, evaluation_revision),
    FOREIGN KEY (tenant_id, composite_id, definition_version, membership_revision)
        REFERENCES dpm_composite_membership_revisions
            (tenant_id, composite_id, definition_version, membership_revision)
);
