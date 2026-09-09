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
- `make ci-local-docker` followed by `make ci-local-docker-down` for Docker parity. Both commands
  derive the same stable, checkout-specific Compose project identity from the absolute repository
  path. `CI_LOCAL_COMPOSE_PROJECT` may override it when an orchestrator supplies a unique identity.
  Cleanup is therefore limited to CI-owned containers, networks, and volumes and must not stop or
  remove the live product Compose project. The purpose-built CI image includes GNU Make because its
  bounded entrypoint executes the repo-native `make ci-local` target, trusts only the `/workspace`
  bind mount for the Git-backed quality gates on Linux hosts, and mounts the sibling
  `lotus-platform` tree plus the eight manifest-declared repositories' domain-data-product
  declaration directories read-only for governed validators and generated contract evidence.
  Keep those sibling repositories available at the standard workspace paths before running Docker
  parity; no service source tree outside `lotus-manage` is writable inside the CI container.
- `make mesh-contract-validate`

## NULL-tenant quarantine inventory

Migrations `0003` and `0024` through `0028` deliberately retain rows that cannot be attributed to
a verified tenant. Migration `0029` adds the partial index required to inventory the original
`dpm_monitoring_runs` quarantine without scanning full monitoring history. Those rows match no
ordinary tenant-scoped repository read and must not be assigned, updated, deleted, or exposed
through an API merely to make a count disappear.

From the `lotus-manage` repository root, set the same governed PostgreSQL DSN used by the service,
then run either shell's equivalent:

```powershell
$env:DPM_SUPPORTABILITY_POSTGRES_DSN = '<bank-managed PostgreSQL DSN>'
$env:QUARANTINE_INVENTORY_LIMIT = '20'
make quarantine-inventory
```

```bash
export DPM_SUPPORTABILITY_POSTGRES_DSN='<bank-managed PostgreSQL DSN>'
export QUARANTINE_INVENTORY_LIMIT=20
make quarantine-inventory
```

The JSON result covers all seven governed datasets, reports each total and a stable bounded sample,
marks truncation explicitly, and includes the applied migration version and checksum. The command
opens a repeatable-read, read-only transaction and always rolls it back. It hashes idempotency keys
and never emits payloads or the DSN.

- `status: success` with `totalQuarantinedRows: 0` is an explicit successful zero.
- `truncated: true` means increase `QUARANTINE_INVENTORY_LIMIT` within `1..100` or query the
  identified dataset through an approved database-support procedure; it is not authority to infer
  ownership.
- Exit code `1` with `QUARANTINE_INVENTORY_FAILED` means the inventory is not evidence. Verify
  connectivity, the bound, and DPM migration application. The sanitized output intentionally omits
  connection details.
- Treat nonzero counts as an attribution backlog for an authorized data owner. This command is
  observation only and provides no remediation or tenant-assignment path.

## Incident triage

- If health fails, verify startup migration state and storage adapter configuration first.
- For supportability anomalies, inspect persisted supportability state and correlation IDs before retry.
- For PM operating-quality incidents, use
  [wiki/Operations-Runbook.md#pm-quality-lifecycle-operations](../wiki/Operations-Runbook.md#pm-quality-lifecycle-operations).
  Triage by Problem Details `reasonCode`, `correlationId`, route `instance`, content hash,
  `lotus_manage_pm_quality_lifecycle_total`, and `lotus_manage_postgres_access_total`; do not
  inspect raw score payloads, review rationale, generated summary text, prompts, or model
  responses. Use
  [docs/methodologies/pm-quality/scoring-and-fairness.md](methodologies/pm-quality/scoring-and-fairness.md)
  for score, fairness, lookback, and validation interpretation.
- For campaign workflow incidents, use
  [wiki/Operations-Runbook.md#campaign-workflow-operations](../wiki/Operations-Runbook.md#campaign-workflow-operations).
  Handled campaign workflow errors return `application/problem+json`; triage by Problem Details
  `reasonCode`, compatibility `code`, `correlationId`, route `instance`, content hash, and
  `lotus_manage_campaign_workflow_total`. Use
  `lotus_manage_campaign_read_model_scan_total` to distinguish bounded-prefix campaign read-model
  requests from correctness-preserving derived-filter full scans. Do not paste raw campaign
  payloads, portfolio ids, actor ids, idempotency keys, correlation ids, source hashes, or
  diagnostics payloads into public incident notes.
- For Core, Risk, or Advise source HTTP transport incidents, use
  [wiki/Operations-Runbook.md#source-http-transport-operations](../wiki/Operations-Runbook.md#source-http-transport-operations)
  and triage with `lotus_manage_source_http_request_total`,
  `lotus_manage_source_http_request_duration_seconds_bucket`, and
  `lotus_manage_source_http_retry_total`.
- For OpenAPI or contract drift, run:
  - `python scripts/openapi_quality_gate.py`
  - `python scripts/api_vocabulary_inventory.py --validate-only`

## Ownership

- This runbook reflects repository-native evidence and does not include downstream UI or gateway-only
  diagnostics.
