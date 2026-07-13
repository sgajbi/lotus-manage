# Lotus Manage Operations Runbook

## Local proof posture

- Install dependencies: `make install`
- Local API: `make run` (default) or `make run-canonical`
- Canonical local stack: `powershell -ExecutionPolicy Bypass -File scripts/Start-CanonicalManage.ps1`

## Validation sequence

1. `make lint`
2. `make typecheck`
3. `make openapi-gate`
4. `make api-vocabulary-gate`
5. `make test-unit`
6. `make security-audit`
7. `make migration-smoke`

For full repo-native evidence in production-oriented work, run:

- `make ci-local` (unit/integration/e2e with merge-gate coverage and gates)
- `make mesh-contract-validate`

## Incident triage

- If health fails, verify startup migration state and storage adapter configuration first.
- For supportability anomalies, inspect persisted supportability state and correlation IDs before retry.
- For PM operating-quality incidents, use
  [wiki/Operations-Runbook.md#pm-quality-lifecycle-operations](../wiki/Operations-Runbook.md#pm-quality-lifecycle-operations).
  Triage by Problem Details `reasonCode`, `correlationId`, route `instance`, content hash,
  `lotus_manage_pm_quality_lifecycle_total`, and `lotus_manage_postgres_access_total`; do not
  inspect raw score payloads, review rationale, generated summary text, prompts, or model
  responses.
- For OpenAPI or contract drift, run:
  - `python scripts/openapi_quality_gate.py`
  - `python scripts/api_vocabulary_inventory.py --validate-only`

## Ownership

- This runbook reflects repository-native evidence and does not include downstream UI or gateway-only
  diagnostics.
