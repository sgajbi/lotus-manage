CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_portfolio_temporal
    ON dpm_mandate_snapshots (
        portfolio_id,
        as_of_date DESC,
        mandate_version DESC,
        mandate_id DESC
    );

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_health_mandate_temporal
    ON dpm_mandate_health_snapshots (
        mandate_id,
        as_of_date DESC,
        created_at DESC,
        health_snapshot_id DESC
    );
