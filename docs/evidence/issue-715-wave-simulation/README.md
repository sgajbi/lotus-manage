# Issue #715 durable wave-simulation evidence

This evidence supports the bounded asynchronous RFC-0041 wave-simulation implementation. It does
not certify production capacity, external execution, order routing, fills, settlement, or core
booking.

## Implemented contract

- Admission persists a tenant-owned operation, immutable item input hashes, source-identity hashes,
  configured methods, concurrency budget, attempt budget, and the `SIMULATING` wave transition in
  one local PostgreSQL transaction before returning `202`.
- Exact idempotent retries return the existing operation. Reusing a key with changed economics,
  methods, limits, or source identity returns an explicit conflict.
- Workers claim at most the remaining operation concurrency budget. Claims carry an opaque token,
  monotonic generation, attempt count, and lease. Financial calculation runs outside the claim
  transaction; only the current unexpired fence can publish a terminal result.
- Construction uses the deterministic operation/item key
  `wave-operation:{operation_id}:{wave_item_id}:simulate`. If a worker dies after committing the
  construction artifact, a replacement reuses that artifact and publishes one item disposition.
- Item status and result pages are tenant-scoped. Retry preserves attempt history. Cancellation
  cancels pending/failed work but allows already claimed work to publish before its lease expires;
  existing construction, approval, and handoff artifacts are never deleted or relabelled.

Supported routes are under `/api/v1/rebalance/waves`:

- `POST /{wave_id}/simulation-operations`
- `GET /simulation-operations/{operation_id}`
- `GET /simulation-operations/{operation_id}/results`
- `POST /simulation-operations/{operation_id}/work`
- `POST /simulation-operations/{operation_id}/retry`
- `POST /simulation-operations/{operation_id}/cancel`

The synchronous `/simulate` route remains available for explicitly bounded callers. It does not
provide restart or competing-worker guarantees and must not be represented as the book-scale path.

## Verification

`tests/integration/dpm/waves/test_wave_simulation_operations_postgres.py` uses real PostgreSQL and
proves competing claims, shared concurrency limits, stale-owner fencing, artifact-commit/process-
replacement recovery, retry exhaustion, cancellation races, source-revision conflicts, tenant-
scoped stable paging, and the deterministic 100-item evaluation condition. The 100-item test uses
concurrency 4, interrupts four items after construction artifacts commit, resumes with replacement
repository/worker instances, reaches 100 explained terminal dispositions, preserves one alternative
set per item, and compares financial comparison metrics with a sequential oracle.

API and in-memory repository regression tests additionally prove admission replay/conflict behavior,
supported status/result/retry/cancel surfaces, persisted wave reconciliation, and foreign-tenant
non-disclosure.

## Measured local operating envelope

The reproducible probe is:

```powershell
# Run from the lotus-manage repository root against an isolated PostgreSQL database.
python scripts/measure_wave_simulation_workload.py `
  --dsn $env:DPM_POSTGRES_INTEGRATION_DSN `
  --items 100 --concurrency 4 --interrupt-count 4
```

```bash
# Run from the lotus-manage repository root against an isolated PostgreSQL database.
python scripts/measure_wave_simulation_workload.py \
  --dsn "$DPM_POSTGRES_INTEGRATION_DSN" \
  --items 100 --concurrency 4 --interrupt-count 4
```

The committed result is
[`issue-715-wave-simulation-load-probe.json`](../issue-715-wave-simulation-load-probe.json).
On the declared Windows AMD64 / Python 3.13.3 / PostgreSQL 16 local profile it recorded:

- 100 `SUCCEEDED`, zero typed errors, zero duplicate alternatives;
- four workers completing 25 portfolios each;
- 5.4357 completed portfolios/s during restart drain;
- p95 17.178981s, p99 18.107293s, maximum 18.316561s completion latency;
- 18.396981s restart backlog drain;
- 23.734375 process CPU seconds, 10,358,126 bytes peak traced Python heap, and 1,441,792
  bytes PostgreSQL database growth.

This is a controlled local operating envelope. Production sizing must repeat the probe on the
target deployment tier with representative network, database, source-service, workload-mix, and
contention conditions. Replica counts, mocks, this deterministic test, and this one workstation run
are not production capacity evidence.

## Review-inbox disposition

`<workspace-root>/review/lotus-manage/INTEGRATION-RUNTIME-WINDOW.md` was reviewed during this slice.
It is reviewer coordination for a stable canonical checkout, not proposed repository documentation,
so none of its prose was adopted into product docs. Its exact #722 checkpoint was preserved in the
review inbox, and #715 remained isolated in its own worktree as requested. No other proposed
`lotus-manage` draft was present for adoption or supersession at this checkpoint.
