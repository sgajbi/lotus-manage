-- Proof packs created before tenant ownership was persisted remain deliberately
-- unattributed. PostgreSQL equality excludes NULL, so no caller can claim them.
ALTER TABLE dpm_pre_trade_proof_packs
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_pre_trade_proof_packs_tenant_created
    ON dpm_pre_trade_proof_packs (tenant_id, created_at DESC, proof_pack_id DESC);
