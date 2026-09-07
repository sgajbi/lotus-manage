-- Scope wave idempotency mappings by tenant (issue #648).
--
-- Idempotency keys are caller-chosen, so two tenants can present the same one.
-- The create path looked a wave up by that key alone and returned whatever it
-- found as a replay, so a second tenant reusing another tenant's key was handed
-- that tenant's wave. Adding the tenant to the request hash did not close this:
-- the hash was only written on save and never compared on the lookup path.
--
-- The stored mapping key is now derived from the tenant and the caller's key
-- rather than being the caller's key itself, because idempotency_key is this
-- table's PRIMARY KEY - two tenants presenting one key could not otherwise both
-- hold a mapping, and refusing the second would disclose that some other tenant
-- holds it. The derivation hashes a length-prefixed sequence, so a tenant or key
-- containing the separator cannot forge another pair's mapping.
--
-- The tenant is stored rather than compared through the request hash because
-- the hash is not stable across identical requests: campaign-derived source
-- refs carry content hashes that differ between two reads of the same unchanged
-- definition, so an identical retry would have been refused as a conflict. That
-- instability is pre-existing and tracked separately; it was invisible while
-- nothing compared the hash on this path.
--
-- tenant_id is nullable with no backfill, matching migrations 0024 and 0025.
-- Mappings written before this migration keep their raw caller-chosen key and
-- carry no tenant, so they match no derived lookup: a caller replaying against
-- one gets a fresh wave rather than another tenant's, and the rows remain for
-- deliberate attribution instead of being assigned an assumed tenant.
ALTER TABLE dpm_rebalance_wave_idempotency
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_dpm_wave_idempotency_tenant
    ON dpm_rebalance_wave_idempotency (tenant_id);
