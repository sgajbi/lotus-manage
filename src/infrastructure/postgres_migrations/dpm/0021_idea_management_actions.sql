CREATE TABLE IF NOT EXISTS dpm_idea_management_actions (
    action_id TEXT PRIMARY KEY,
    intake_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    legal_entity_code TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    idea_candidate_id TEXT NOT NULL,
    conversion_intent_id TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    idempotency_scope_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    source_event_version INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT dpm_idea_management_actions_intake_scope_key
        UNIQUE (tenant_id, legal_entity_code, intake_id),
    CONSTRAINT dpm_idea_management_actions_status_check
        CHECK (status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')),
    CONSTRAINT dpm_idea_management_actions_version_check
        CHECK (source_event_version >= 1),
    CONSTRAINT dpm_idea_management_actions_scope_check
        CHECK (
            length(trim(tenant_id)) > 0
            AND length(trim(legal_entity_code)) > 0
            AND length(trim(portfolio_id)) > 0
        )
);

CREATE INDEX IF NOT EXISTS idx_dpm_idea_management_actions_portfolio
ON dpm_idea_management_actions (tenant_id, legal_entity_code, portfolio_id, updated_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dpm_idea_management_actions_conversion_scope
ON dpm_idea_management_actions (
    tenant_id,
    legal_entity_code,
    portfolio_id,
    conversion_intent_id
);

CREATE TABLE IF NOT EXISTS dpm_idea_management_action_events (
    event_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL REFERENCES dpm_idea_management_actions(action_id) ON DELETE RESTRICT,
    source_event_version INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload_json TEXT NOT NULL,
    CONSTRAINT dpm_idea_management_action_events_version_key
        UNIQUE (action_id, source_event_version),
    CONSTRAINT dpm_idea_management_action_events_version_check
        CHECK (source_event_version >= 1),
    CONSTRAINT dpm_idea_management_action_events_type_check
        CHECK (event_type IN ('INTAKE_ACCEPTED', 'APPROVE', 'REJECT', 'REQUEST_CHANGES')),
    CONSTRAINT dpm_idea_management_action_events_status_check
        CHECK (status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED'))
);

CREATE INDEX IF NOT EXISTS idx_dpm_idea_management_action_events_history
ON dpm_idea_management_action_events (action_id, source_event_version ASC);
