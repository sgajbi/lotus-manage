CREATE TABLE IF NOT EXISTS dpm_policy_packs (
    policy_pack_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    definition_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
