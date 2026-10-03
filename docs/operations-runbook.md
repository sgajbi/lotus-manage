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

## Source mandate cash reserve

Stateful single/batch and source-bound wave execution require the effective binding's reserve scope
`TOTAL_PORTFOLIO_MARKET_VALUE`, currency basis `PORTFOLIO_BASE_CURRENCY`, authority
`MANDATE_BINDING` and explicit `consumer_override_allowed=false`. These source facts, target,
binding version and effective dates survive in retained run lineage. An absent target differs from
zero. Missing authority or `MANDATE_CASH_RESERVE_INVALID` returns 424 before financial or mandate
writes. Invalid-reserve validation belongs to shared binding ingestion, including mandate refresh;
restore valid source evidence, not a caller override. Old artifacts remain readable.

No-override authority also rejects a caller-supplied target when the source target is absent,
including explicit zero. The independent request-level `min_cash_buffer_pct` remains available
in that case; it does not create a mandate target or reserve-target rule.

The target is not a hard cash band. Absolute cash-weight tolerance is 0.0001; larger post-trade
deviation requires review. With USD NAV 100,000, one security and no costs:

| Target | Price | Whole Shares After | Cash After | Reserve Result |
| --- | --- | --- | --- | --- |
| 0.02 | 100 | 980 | 2,000 | Within tolerance |
| 0 or absent | 100 | 1,000 | 0 | Explicit zero passes; absence emits no target rule |
| 0.50 | 100 | 500 | 50,000 | Within tolerance |
| 0.02 | 123 | 796 | 2,092 | Weight 0.02092 requires review |

Independent reconciliation is `shares * price + cash = NAV`. See
[native HTTP/PostgreSQL tests](../tests/integration/dpm/supportability/test_source_cash_reserve_network.py)
for controlled-producer proof, batch position-cap deviation, tenant isolation and retained replay
after process replacement. No real Core, bank IAM, capacity, approval, settlement or booking
acceptance is claimed. Stateless wave inputs are explicit counterfactuals, not Core-binding proof.

For synchronous or durable waves, supply an item selector with `input_mode=stateful` and optional
`options_override`; do not send snapshots, source context or repeated tenant/date/mandate/model
selectors. Manage derives scope from the checked wave and resolves Core inputs before calculation
or admission. A changed checked mandate revision returns409; missing authority or conflicting
controls return424. Durable workers/retries consume frozen inputs without refetching Core;
hash corruption becomes a non-retryable failure. Existing readiness/approval gates remain intact.
Core's missing cash-band/turnover applicability leaves health review-required; fix source data,
not readiness flags. [Wave proof and limitations](evidence/issue-733-source-bound-waves/README.md).

## NULL-tenant quarantine inventory

Migrations `0003`, `0024` through `0029`, `0032`, `0033`, and `0037` deliberately retain rows that cannot
be attributed to a verified tenant. Partial quarantine indexes keep bounded sampling from scanning
unrelated history. Those rows match no
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

The JSON result covers all fourteen governed datasets, reports each total and a stable bounded sample,
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

### Construction ownership migration `0037`

Migration `0037` is forward-only. It adds construction-set and selection ownership, replaces the
global idempotency constraint with tenant-scoped uniqueness, and leaves pre-existing rows at NULL
because no verified owner can be inferred. Before applying it, pause construction generation and
selection writes. Apply the migration, deploy the tenant-aware binary, verify readiness and the
quarantine inventory, and only then restore write traffic. Do not run an older writer concurrently
or after the migration: it cannot supply the new owner and its global-idempotency assumptions are
obsolete. Failure recovery is a forward fix; if environment policy requires rollback, restore the
complete pre-upgrade database backup and matching application revision as one unit. Never delete,
backfill, or hand-assign legacy construction rows merely to obtain a zero inventory.

## Async operation ownership and crash recovery

All async submission, status, inventory, and manual-execute routes require normalized
`X-Tenant-Id`. The PostgreSQL production profile stores tenant ownership and uses one atomic claim
to move a `PENDING` operation to `RUNNING`. A claim receives an opaque fencing token, increments
`execution_attempt`, and sets `execution_lease_expires_at`. API responses expose only the attempt
and expiry. The token is internal and must not appear in responses, logs, metrics, or evidence
packs.

`DPM_ASYNC_EXECUTION_LEASE_SECONDS` defaults to `300` and is clamped to at least one second. Size it
above the observed upper bound for one batch calculation plus persistence, then alert on RUNNING
rows approaching expiry. This implementation does not heartbeat a claim. Expiry deliberately lets
a new worker recover work after process loss, so an undersized lease can cause duplicate
calculation; fencing still ensures only the current owner can publish authoritative success or
failure. General async TTL cleanup never removes RUNNING rows.

Recovery procedure:

1. Read the tenant-scoped operation status. Record `operation_id`, `correlation_id`, `status`,
   `execution_attempt`, and `execution_lease_expires_at`; do not infer ownership from logs.
2. If the lease is still active, do not force a second execution. A competing manual execute
   returns `409 DPM_ASYNC_OPERATION_NOT_EXECUTABLE`.
3. After confirmed expiry, retry the same operation through the supported execute route or worker
   path. A successful claim increments the attempt. A prior worker's terminal write is refused as
   `DPM_ASYNC_OPERATION_STALE_EXECUTION_OWNER` and cannot replace the accepted result.
4. Re-read status. Identical publication by the current token is idempotent; a different terminal
   payload is a conflict and requires investigation rather than database repair.

Migration `0033` preserves pre-ownership PENDING, RUNNING, and terminal rows with `tenant_id =
NULL`. They are quarantined from every tenant route and included in `make quarantine-inventory`;
operators must not guess an owner or manually add a claim token. SQLite performs the equivalent
transactional table upgrade for portable local stores. These controls prove durable ownership and
restart recovery with PostgreSQL; they do not certify a distributed queue, measured horizontal
capacity, authenticated tenant principals, or external trade delivery.

## Legacy mandate-limit provenance

Migration `0030` handles snapshots written before the repository recorded whether Core compilation
or explicit caller health input supplied the twin. Historical lineage cannot decide this because a
caller could submit the same lineage.

- Stored cash-band and turnover values remain intact for audit and recovery.
- `MANDATE_LIMIT_PROVENANCE_AMBIGUOUS` makes them ineffective on reads and health calculations.
- No legacy zero cash minimum is promoted into an explicit cash reserve.
- All health snapshots and limit-dependent cash/turnover exceptions for the same tenant and mandate
  are retired when any retained snapshot is ambiguous. Recalculation accepted a caller-selected
  non-latest version, evidence did not record its snapshot identity, and snapshot upserts refreshed
  `created_at`; neither a clean latest snapshot nor timestamp ordering can prove which version
  produced it. Projected cash-flow, tax-lot, restriction, and workflow findings survive.
- Successful monitoring runs that reference an affected mandate remain auditable but become
  `FAILED` with empty aggregates. Their overall execution window cannot reconstruct per-mandate
  reads once snapshot timestamps have been refreshed; runs that already failed retain their
  original evidence.
- NULL-tenant snapshots may receive the non-authoritative provenance marker, but their quarantined
  runs, health, and exceptions are never changed or deleted before audited tenant attribution.
- Future snapshots record `CORE_COMPILED` or `CALLER_SUPPLIED` producer provenance. After the
  backfill the database drops the legacy default, so an old replica that omits provenance fails
  instead of creating or overwriting an unmarked ambiguous row.
- Recalculation resolves the exact tenant-scoped stored snapshot identity before trusting any
  caller gap codes. A forged marker fails with `DPM_MANDATE_AMBIGUOUS_SNAPSHOT_NOT_FOUND`; omitting
  a stored marker cannot bypass the fence. Manage calculates ambiguous history from the retained
  effective snapshot, so caller changes to restrictions, policy, lineage, risk profile, or other
  twin fields cannot alter evidence or overwrite the retained raw snapshot limits. A changed
  portfolio is rejected because persistence identity is tenant/mandate/version/as-of, not portfolio.

After rollout, verify `dpm:0030`, refresh the affected mandate from governed Core sources, then
recalculate health and run monitoring again. Never clear the marker or reconstruct derived evidence
by direct SQL. Rollback restores the pre-migration database backup as one unit; do not reverse only
the payload marker while leaving dependent evidence migrated.

## Incident triage

- If health fails, verify startup migration state and storage adapter configuration first.
- For supportability anomalies, inspect persisted supportability state and correlation IDs before retry.
- For `POST /api/v1/rebalance/waves` conflicts, retain the admitted tenant and hashed support
  identifiers. `DPM_WAVE_IDEMPOTENCY_CONFLICT` means the key already owns a different canonical
  create request; do not retry it with changed economics. `DPM_WAVE_CORRELATION_CONFLICT` means a
  caller-supplied correlation already identifies another wave in that tenant; use a new correlation
  only for a genuinely distinct command. Do not add random correlation headers to exact retries:
  omitting the header deliberately derives a stable correlation from the tenant and idempotency key.
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
