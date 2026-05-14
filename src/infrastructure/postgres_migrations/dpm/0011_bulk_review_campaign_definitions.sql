CREATE TABLE IF NOT EXISTS dpm_bulk_review_campaign_definitions (
    campaign_id TEXT NOT NULL,
    campaign_version TEXT NOT NULL,
    status TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (campaign_id, campaign_version)
);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_definitions_status
    ON dpm_bulk_review_campaign_definitions (status);

CREATE INDEX IF NOT EXISTS idx_dpm_bulk_review_campaign_definitions_as_of_date
    ON dpm_bulk_review_campaign_definitions (as_of_date);
