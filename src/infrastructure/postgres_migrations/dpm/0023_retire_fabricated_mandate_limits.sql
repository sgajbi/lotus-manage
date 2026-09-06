UPDATE dpm_mandate_snapshots
    -- Issue #664. Twins persisted before the source-authority correction carry
    -- a fabricated cash band and a 0.15 turnover budget inside payload_json.
    -- Those fields are now nullable, so the old values still deserialize and
    -- every read would keep publishing limits no source ever stated.
    --
    -- The old compiler set cash_band_min_weight to the rebalance cash reserve,
    -- so the reserve is recoverable from it. COALESCE keeps an existing
    -- cash_reserve_weight ahead of that fallback, and the WHERE clause matches
    -- only rows that still carry a fabricated value, so rows written by the
    -- corrected compiler are not touched at all.
    SET payload_json = jsonb_set(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    payload_json::jsonb,
                    '{constraints,cash_reserve_weight}',
                    COALESCE(
                        payload_json::jsonb #> '{constraints,cash_reserve_weight}',
                        payload_json::jsonb #> '{constraints,cash_band_min_weight}',
                        'null'::jsonb
                    ),
                    true
                ),
                '{constraints,cash_band_min_weight}', 'null'::jsonb, true
            ),
            '{constraints,cash_band_max_weight}', 'null'::jsonb, true
        ),
        '{constraints,turnover_budget}', 'null'::jsonb, true
    )::text
    WHERE payload_json::jsonb #> '{constraints}' IS NOT NULL
      AND (
          payload_json::jsonb #>> '{constraints,cash_band_min_weight}' IS NOT NULL
          OR payload_json::jsonb #>> '{constraints,cash_band_max_weight}' IS NOT NULL
          OR payload_json::jsonb #>> '{constraints,turnover_budget}' IS NOT NULL
      );

UPDATE dpm_mandate_snapshots
    -- The same rows must also name the gaps, so a persisted twin reports the
    -- absence exactly as a freshly compiled one does. Appending only when the
    -- code is absent keeps this safe if the statement is ever replayed.
    SET payload_json = jsonb_set(
        payload_json::jsonb,
        '{field_gap_codes}',
        COALESCE(payload_json::jsonb -> 'field_gap_codes', '[]'::jsonb)
            || '["MANDATE_CASH_BAND_NOT_YET_SOURCED", "MANDATE_TURNOVER_BUDGET_NOT_YET_SOURCED"]'::jsonb,
        true
    )::text
    WHERE NOT COALESCE(
        payload_json::jsonb -> 'field_gap_codes',
        '[]'::jsonb
    ) @> '["MANDATE_CASH_BAND_NOT_YET_SOURCED"]'::jsonb;
