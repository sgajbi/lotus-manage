-- Issue #664. Twins persisted before the source-authority correction carry a
-- fabricated cash band and a 0.15 turnover budget inside payload_json. Those
-- fields are now nullable, so the old values still deserialize and every read
-- would keep publishing limits no source ever stated.
--
-- Scope is the hard part. /health/recalculate persists a caller-supplied twin
-- unchanged, so a non-null cash band or turnover budget is NOT by itself
-- evidence of fabrication - it may be a genuine contractual limit somebody
-- supplied. Clearing those would destroy real source data and mislabel it as
-- unsourced, which is the same class of error this issue exists to fix, only
-- pointing the other way.
--
-- The old compiler is identifiable instead of guessed at. It set
--   cash_band_min_weight = cash_reserve_weight
--   cash_band_max_weight = max(cash_reserve_weight, 0.10)
--   turnover_budget      = 0.15
-- and had no cash_reserve_weight field of its own. Every statement below
-- matches that whole shape, so a row that fails any part of it is left alone.
--
-- The deletions run BEFORE the rewrite because the predicate can only
-- recognise a fabricated row while it is still fabricated.

-- Monitoring exceptions raised against limits that were never real. Breaches
-- of an invented threshold are not findings, and leaving them published would
-- keep operators acting on them.
DELETE FROM dpm_monitoring_exceptions
    WHERE mandate_id IN (
        SELECT DISTINCT mandate_id
        FROM dpm_mandate_snapshots
        WHERE payload_json::jsonb #> '{constraints}' IS NOT NULL
          AND payload_json::jsonb #> '{constraints,cash_reserve_weight}' IS NULL
          AND payload_json::jsonb #>> '{constraints,cash_band_min_weight}' IS NOT NULL
          AND payload_json::jsonb #>> '{constraints,turnover_budget}' ~ '^0\.150*$'
          AND (payload_json::jsonb #>> '{constraints,cash_band_max_weight}')::numeric
              = GREATEST(
                    (payload_json::jsonb #>> '{constraints,cash_band_min_weight}')::numeric,
                    0.10
                )
    );

-- Health snapshots scored against those limits. A snapshot derived from
-- fabricated inputs is not evidence, and it cannot be recomputed here because
-- the scoring lives in Python. Removing it makes GET /health answer 404 - its
-- documented "not yet assessed" state - instead of continuing to publish a
-- READY result that the corrected engine would now report as PENDING_REVIEW.
-- These are derived artifacts, reproducible with /health/recalculate, so no
-- source-owned fact is lost.
DELETE FROM dpm_mandate_health_snapshots
    WHERE mandate_id IN (
        SELECT DISTINCT mandate_id
        FROM dpm_mandate_snapshots
        WHERE payload_json::jsonb #> '{constraints}' IS NOT NULL
          AND payload_json::jsonb #> '{constraints,cash_reserve_weight}' IS NULL
          AND payload_json::jsonb #>> '{constraints,cash_band_min_weight}' IS NOT NULL
          AND payload_json::jsonb #>> '{constraints,turnover_budget}' ~ '^0\.150*$'
          AND (payload_json::jsonb #>> '{constraints,cash_band_max_weight}')::numeric
              = GREATEST(
                    (payload_json::jsonb #>> '{constraints,cash_band_min_weight}')::numeric,
                    0.10
                )
    );

-- The rewrite itself. The reserve is recovered from cash_band_min_weight,
-- which is where the old compiler put it, so a real source-owned value is
-- preserved under its own meaning rather than discarded with the invented
-- ones. The gap codes are appended in the same statement, so a rewritten row
-- reports its absences exactly as a freshly compiled twin does and no row can
-- end up rewritten but unlabelled.
--
-- source_hash is recomputed with the payload. PostgresDpmMandateRepository
-- establishes it as the SHA-256 of the serialized payload, so leaving the old
-- digest would make every migrated row fail any audit that recomputes it.
UPDATE dpm_mandate_snapshots
    SET payload_json = _retired.rewritten::text,
        source_hash = 'sha256:' || encode(sha256(convert_to(_retired.rewritten::text, 'UTF8')), 'hex')
    FROM (
        SELECT
            mandate_snapshot_id AS snapshot_id,
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                payload_json::jsonb,
                                '{constraints,cash_reserve_weight}',
                                payload_json::jsonb #> '{constraints,cash_band_min_weight}',
                                true
                            ),
                            '{constraints,cash_band_min_weight}', 'null'::jsonb, true
                        ),
                        '{constraints,cash_band_max_weight}', 'null'::jsonb, true
                    ),
                    '{constraints,turnover_budget}', 'null'::jsonb, true
                ),
                '{field_gap_codes}',
                COALESCE(payload_json::jsonb -> 'field_gap_codes', '[]'::jsonb)
                    || '["MANDATE_CASH_BAND_NOT_YET_SOURCED",
                         "MANDATE_TURNOVER_BUDGET_NOT_YET_SOURCED"]'::jsonb,
                true
            ) AS rewritten
        FROM dpm_mandate_snapshots
        WHERE payload_json::jsonb #> '{constraints}' IS NOT NULL
          AND payload_json::jsonb #> '{constraints,cash_reserve_weight}' IS NULL
          AND payload_json::jsonb #>> '{constraints,cash_band_min_weight}' IS NOT NULL
          AND payload_json::jsonb #>> '{constraints,turnover_budget}' ~ '^0\.150*$'
          AND (payload_json::jsonb #>> '{constraints,cash_band_max_weight}')::numeric
              = GREATEST(
                    (payload_json::jsonb #>> '{constraints,cash_band_min_weight}')::numeric,
                    0.10
                )
    ) AS _retired
    WHERE dpm_mandate_snapshots.mandate_snapshot_id = _retired.snapshot_id;
