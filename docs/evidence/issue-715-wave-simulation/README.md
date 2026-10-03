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
- Every supplied item selector and nested construction `portfolio_snapshot.portfolio_id` must agree
  with the admitted wave item. Async and bounded synchronous routes refuse contradictory, unknown,
  or foreign identities before construction. A worker also turns any mismatched returned construction
  association into a non-retryable failure rather than attaching it to the wave item.
- Workers claim at most the remaining operation concurrency budget. Claims carry an opaque token,
  monotonic generation, attempt count, and lease. Financial calculation runs outside the claim
  transaction; serial workers claim each item when execution starts. Only the current unexpired
  fence can publish a terminal result. Retryable failures retain source-ready wave state until
  attempts are exhausted, so explicit retry executes financial work again.
- Construction uses the deterministic operation/item key
  `wave-operation:{operation_id}:{wave_item_id}:simulate`. If a worker dies after committing the
  construction artifact, a replacement reuses that artifact and publishes one item disposition.
- Item status and result pages are tenant-scoped. Retry preserves attempt history. Cancellation
  cancels pending/retry-eligible failed work but preserves terminal failure evidence and allows
  already claimed work to publish before lease expiry;
  repeat cancellation reaps an expired claim while retaining the first reason. Existing
  construction, approval, and handoff artifacts are never deleted or relabelled.
  In-flight failure publication under cancellation preserves its failure evidence but atomically
  removes retry eligibility, allowing terminal wave reconciliation even with a stale worker view.
- Wave projection is serialized by tenant/wave using the existing bounded PostgreSQL coordination
  budget. Each projection reads fresh checkpoints; old operations cannot project a newer admission.

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
proves competing claims, shared concurrency limits, stale-owner fencing, artifact-commit/repository-
instance replacement recovery, retry exhaustion, cancellation races, source-revision conflicts, tenant-
scoped stable paging, and the deterministic 100-item evaluation condition. The 100-item test uses
concurrency 4, interrupts four items after construction artifacts commit, resumes with replacement
repository/worker instances, reaches 100 explained terminal dispositions, preserves one alternative
set per item, and compares financial comparison metrics with a sequential oracle.

`tests/integration/dpm/waves/test_wave_worker_process_recovery.py` proves actual process termination:
the parent kills a spawned worker after PostgreSQL construction and financial-run commits but before
the item checkpoint. A fresh spawned process invokes the registered `/work` API after lease expiry,
reuses the immutable alternative/run artifact, and publishes one terminal item. Assertions verify
one retained run, stale-owner refusal, tenant-scoped status/results and the independent financial
example: SGD 15,000 NAV, 120 shares and SGD 3,000 cash. All stores are PostgreSQL; inputs are synthetic
and manually source-ready. This is not positive upstream/downstream, approval or capacity proof.

`tests/integration/dpm/waves/test_wave_network_recovery.py` extends recovery to unmodified
Uvicorn/HTTP with enabled caller-asserted authorization and real PostgreSQL. Database locks force
the financial-commit/checkpoint gap; an observed blocked publisher is aborted after the API is
killed. A fresh API recovers the same artifact after actual lease expiry, publishes one disposition
and retains immutable input/source identities. Supported status/results/artifact APIs verify
tenant refusal, exact replay and NAV15,000/BUY20/120shares/SGD3,000 cash. Only the UUID test database
receives fault locks/session termination. This combined process/session fault is not a database
failover, shipped-image business test, live source qualification or production capacity result.

API and in-memory repository regression tests additionally prove admission replay/conflict behavior,
selector/nested-portfolio identity binding, returned-association refusal, supported
status/result/retry/cancel surfaces, persisted wave reconciliation, and foreign-tenant
non-disclosure.

The concurrency regression launches 64 repository-instance reconcilers for one retained financial
checkpoint and requires one projection writer, one completion event and unchanged BUY20/run
evidence. This is projection contention proof, not 64-worker financial capacity certification.

The 3 October 2026 review correction passed the full 4,309-test suite against isolated PostgreSQL,
including post-cancel failure controls for both adapters with a stale worker snapshot. Fresh combined
coverage measured 31,653 statements with 315 misses (99.00% against the enforced 99% floor).
The joined regression also proves that the
admitted tenant reaches construction, a 2% cash-reserve target remains 2.00% after construction,
and an active no-buy restriction blocks both the alternative and its selection. This is code and
persistence evidence, not production-capacity or external core-booking readiness.

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
On the declared Windows AMD64 / Python 3.13.3 / PostgreSQL 17 local profile it recorded:

- 100 `SUCCEEDED`, zero typed errors, zero duplicate alternatives;
- four workers completing 25 portfolios each;
- 6.5917 completed portfolios/s during restart drain;
- p95 14.216904s, p99 14.813994s, maximum 15.131246s completion latency;
- 15.170554s restart backlog drain;
- 18.265625 process CPU seconds, 12,651,142 bytes peak traced Python heap, and 1,196,032
  bytes PostgreSQL database growth.

This is a controlled local operating envelope. Production sizing must repeat the probe on the
target deployment tier with representative network, database, source-service, workload-mix, and
contention conditions. Replica counts, mocks, this deterministic test, and this one workstation run
are not production capacity evidence.

## Review-inbox disposition

The original review-inbox files were reviewed. `INTEGRATION-RUNTIME-WINDOW.md` remains
coordination-only; its released runtime hold and #715 takeover were followed without copying it into
product documentation. `AUDIT-REFUSAL-AND-LOG-SAFETY-20261002.md` and
`COMPOSITE-PUBLICATION-QA-20261002.md` concern already merged #756/#757 and #714 work and add no
#715 contract. They are therefore neither adopted nor superseded by this slice.

README, RFC, repository context, evidence, and five wiki pages change with this implementation.
Wiki source must pass the changed-page audit and unpublished-source parity check before merge, then
be published and checked for strict parity from merged `main`.
