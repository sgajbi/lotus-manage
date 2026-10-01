CREATE TABLE IF NOT EXISTS dpm_approved_instruction_packages (
    tenant_id TEXT NOT NULL,
    package_id TEXT NOT NULL,
    package_version TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    wave_id TEXT NOT NULL,
    wave_item_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, package_id, package_version)
);

CREATE INDEX IF NOT EXISTS idx_dpm_approved_instruction_packages_tenant_snapshot
    ON dpm_approved_instruction_packages (
        tenant_id, created_at DESC, package_id DESC, package_version DESC
    );

CREATE INDEX IF NOT EXISTS idx_dpm_approved_instruction_packages_tenant_wave_item
    ON dpm_approved_instruction_packages (tenant_id, wave_id, wave_item_id);

CREATE TABLE IF NOT EXISTS dpm_approved_instruction_package_receipts (
    tenant_id TEXT NOT NULL,
    package_id TEXT NOT NULL,
    package_version TEXT NOT NULL,
    consumer_id TEXT NOT NULL,
    receipt_id TEXT NOT NULL,
    receipt_evidence_hash TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (tenant_id, package_id, package_version, consumer_id),
    FOREIGN KEY (tenant_id, package_id, package_version)
        REFERENCES dpm_approved_instruction_packages (tenant_id, package_id, package_version)
);
