-- Issue #674. Before this migration the snapshot row recorded the service as
-- created_by for both Core-compiled and caller-supplied twins. source_lineage
-- is also caller-controlled on /health/recalculate, so it cannot prove which
-- path produced a historical row. Existing rows therefore remain unknown;
-- future writes carry a repository-owned producer classification.
ALTER TABLE dpm_mandate_snapshots
    ADD COLUMN IF NOT EXISTS producer_kind TEXT NOT NULL DEFAULT 'UNKNOWN_LEGACY';

DO $producer_constraint$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'dpm_mandate_snapshots_producer_kind_check'
          AND conrelid = 'dpm_mandate_snapshots'::regclass
    ) THEN
        ALTER TABLE dpm_mandate_snapshots
            ADD CONSTRAINT dpm_mandate_snapshots_producer_kind_check
            CHECK (producer_kind IN ('UNKNOWN_LEGACY', 'CORE_COMPILED', 'CALLER_SUPPLIED'));
    END IF;
END
$producer_constraint$;

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_unknown_producer
    ON dpm_mandate_snapshots (mandate_snapshot_id)
    WHERE producer_kind = 'UNKNOWN_LEGACY';

-- A historical non-null contractual limit might be genuine caller input or
-- an old compiler fabrication. Mark the whole unknown-producer cohort by
-- field presence, not by the old compiler's numeric fingerprint. Values are
-- retained for audit; application reads and scoring suppress them while this
-- marker is present. No zero reserve is invented.
UPDATE dpm_mandate_snapshots
SET payload_json = marked.rewritten::text,
    source_hash = 'sha256:' || encode(sha256(convert_to(marked.rewritten::text, 'UTF8')), 'hex')
FROM (
    SELECT
        mandate_snapshot_id,
        jsonb_set(
            payload_json::jsonb,
            '{field_gap_codes}',
            COALESCE(payload_json::jsonb -> 'field_gap_codes', '[]'::jsonb)
                || '["MANDATE_LIMIT_PROVENANCE_AMBIGUOUS"]'::jsonb,
            true
        ) AS rewritten
    FROM dpm_mandate_snapshots
    WHERE producer_kind = 'UNKNOWN_LEGACY'
      AND (
          payload_json::jsonb #>> '{constraints,cash_band_min_weight}' IS NOT NULL
          OR payload_json::jsonb #>> '{constraints,cash_band_max_weight}' IS NOT NULL
          OR payload_json::jsonb #>> '{constraints,turnover_budget}' IS NOT NULL
      )
      AND NOT (
          COALESCE(payload_json::jsonb -> 'field_gap_codes', '[]'::jsonb)
              ? 'MANDATE_LIMIT_PROVENANCE_AMBIGUOUS'
      )
) AS marked
WHERE dpm_mandate_snapshots.mandate_snapshot_id = marked.mandate_snapshot_id;

-- A successful run containing an affected mandate can no longer truthfully
-- publish its old distribution. Preserve the attempted mandate ids for audit,
-- but fail the run and clear result aggregates instead of manufacturing a
-- replacement calculation inside SQL.
UPDATE dpm_monitoring_runs AS run
SET status = 'FAILED',
    failure_reason = 'MANDATE_LIMIT_PROVENANCE_AMBIGUOUS',
    source_readiness_summary_json = '{}',
    payload_json = run.payload_json || jsonb_build_object(
        'status', 'FAILED',
        'failure_reason', 'MANDATE_LIMIT_PROVENANCE_AMBIGUOUS',
        'total_mandates', 0,
        'health_distribution', '{}'::jsonb,
        'exception_count', 0,
        'source_readiness_summary', '{}'::jsonb
    )
WHERE run.payload_json IS NOT NULL
  AND run.status = 'SUCCEEDED'
  AND EXISTS (
      SELECT 1
      FROM dpm_mandate_snapshots AS snapshot
      WHERE snapshot.producer_kind = 'UNKNOWN_LEGACY'
        AND COALESCE(snapshot.payload_json::jsonb -> 'field_gap_codes', '[]'::jsonb)
            ? 'MANDATE_LIMIT_PROVENANCE_AMBIGUOUS'
        AND snapshot.tenant_id IS NOT NULL
        AND snapshot.tenant_id = run.tenant_id
        AND run.payload_json -> 'mandate_ids' ? snapshot.mandate_id
  );

-- Retire only evidence whose meaning depended on the ambiguous cash band or
-- turnover budget. Independent restriction/workflow findings survive.
DELETE FROM dpm_monitoring_exceptions AS exception
WHERE exception.reason_code IN (
    'CASH_BELOW_BAND',
    'CASH_ABOVE_BAND',
    'TURNOVER_BUDGET_NEAR_LIMIT'
)
  AND EXISTS (
      SELECT 1
      FROM dpm_mandate_snapshots AS snapshot
      WHERE snapshot.mandate_id = exception.mandate_id
        AND snapshot.tenant_id IS NOT NULL
        AND snapshot.tenant_id = exception.tenant_id
        AND snapshot.producer_kind = 'UNKNOWN_LEGACY'
        AND COALESCE(snapshot.payload_json::jsonb -> 'field_gap_codes', '[]'::jsonb)
            ? 'MANDATE_LIMIT_PROVENANCE_AMBIGUOUS'
  );

-- A health snapshot is one indivisible assessment. It cannot be repaired in
-- SQL without replaying the Python scoring inputs, so remove it rather than
-- leave GET /health asserting a state derived from untrusted limits.
DELETE FROM dpm_mandate_health_snapshots AS health
WHERE EXISTS (
    SELECT 1
    FROM dpm_mandate_snapshots AS snapshot
    WHERE snapshot.mandate_id = health.mandate_id
      AND snapshot.tenant_id IS NOT NULL
      AND snapshot.tenant_id = health.tenant_id
      AND snapshot.producer_kind = 'UNKNOWN_LEGACY'
      AND COALESCE(snapshot.payload_json::jsonb -> 'field_gap_codes', '[]'::jsonb)
          ? 'MANDATE_LIMIT_PROVENANCE_AMBIGUOUS'
);

-- The backfill is complete inside this migration transaction. Do not leave a
-- compatibility default behind: an older replica that omits producer_kind
-- must fail its insert/upsert instead of creating an unmarked UNKNOWN_LEGACY
-- row after the one-time marker pass.
ALTER TABLE dpm_mandate_snapshots
    ALTER COLUMN producer_kind DROP DEFAULT;
