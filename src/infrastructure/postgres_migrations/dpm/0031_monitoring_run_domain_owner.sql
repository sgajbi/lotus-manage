-- Promote valid monitoring-run ownership into the domain payload. Only rows
-- whose stored column and legacy filter already agree receive the new field;
-- NULL or contradictory history remains quarantined rather than assigned.
UPDATE dpm_monitoring_runs
SET payload_json = jsonb_set(
    payload_json,
    '{tenant_id}',
    to_jsonb(tenant_id),
    true
)
WHERE tenant_id IS NOT NULL
  AND payload_json IS NOT NULL
  AND payload_json -> 'filters' ->> 'tenant_id' = tenant_id;
