CREATE TABLE IF NOT EXISTS dpm_pre_trade_proof_packs (
    proof_pack_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    mandate_id TEXT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    idempotency_key TEXT UNIQUE NULL,
    retention_policy TEXT NOT NULL,
    retention_expires_at TIMESTAMPTZ NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_pre_trade_proof_packs_portfolio
    ON dpm_pre_trade_proof_packs (portfolio_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dpm_pre_trade_proof_packs_status
    ON dpm_pre_trade_proof_packs (status, created_at DESC);

CREATE TABLE IF NOT EXISTS dpm_pre_trade_proof_pack_sections (
    proof_pack_id TEXT NOT NULL
        REFERENCES dpm_pre_trade_proof_packs (proof_pack_id),
    section_id TEXT NOT NULL,
    section_type TEXT NOT NULL,
    state TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (proof_pack_id, section_id)
);

CREATE TABLE IF NOT EXISTS dpm_pre_trade_proof_pack_refs (
    proof_pack_id TEXT NOT NULL
        REFERENCES dpm_pre_trade_proof_packs (proof_pack_id),
    ref_type TEXT NOT NULL,
    ref_id TEXT NOT NULL,
    source_system TEXT NOT NULL,
    content_hash TEXT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dpm_pre_trade_proof_pack_refs_pack
    ON dpm_pre_trade_proof_pack_refs (proof_pack_id, created_at);
