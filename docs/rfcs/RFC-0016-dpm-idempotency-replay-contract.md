# RFC-0016: lotus-manage Idempotency Replay Contract for `/rebalance/simulate`

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-20 |
| **Current implementation** | 2026-10-01 tenant-scoped durable admission hardening |
| **Depends On** | RFC-0001, RFC-0002, RFC-0007A |
| **Compatibility** | Strengthens the required `Idempotency-Key` contract and requires `X-Tenant-Id` |

## Executive summary

`POST /api/v1/rebalance/simulate` admits one logical synchronous rebalance request under the
durable identity `(tenant_id, Idempotency-Key)` and an immutable canonical request hash.

- same tenant, key, and hash returns one authoritative run, including under concurrent workers;
- same tenant and key with a different hash returns `409`;
- the same key is independent across tenants;
- missing or foreign tenant scope cannot read the winning run or its supportability descendants.

The original 2026-02 implementation used a process-local replay cache and a replay-disable flag.
Those controls are historical and are not the current safety boundary. Durable admission cannot be
disabled because doing so would permit duplicate economic decisions under retry or concurrency.

## Contract

Required headers:

1. `Idempotency-Key` identifies one logical request within a tenant.
2. `X-Tenant-Id` supplies the normalized caller-asserted ownership scope. In stateful mode it must
   also match `stateful_input.tenant_id` before Core sourcing.

The tenant header is a routing and persistence scope, not authenticated-principal proof. Production
identity and grant resolution remain a separate security dependency.

Canonical hashing includes the economic request envelope. `X-Correlation-Id` is operational trace
context and is not part of economic identity, so concurrent retries with different correlation ids
still resolve to the winning run.

## Durable admission flow

1. Begin a PostgreSQL transaction and insert or lock the claim for `(tenant_id, idempotency_key)`.
2. Bind a new claim to the canonical request hash, a random fencing token, and a bounded lease.
3. Reject a changed hash under the owned key with
   `IDEMPOTENCY_KEY_CONFLICT: request hash mismatch`.
4. If a completed claim exists, load the exact tenant-owned run and return it.
5. If another unexpired claim exists, wait for a bounded winner-recovery interval. Return the
   winner when it commits; otherwise return `409 DPM_REBALANCE_REQUEST_IN_PROGRESS` with
   `Retry-After`.
6. The claim owner calculates the rebalance.
7. In one transaction, verify the fencing token, mark the claim completed, and persist the run,
   optional artifact, tenant-scoped mapping, append-only history, and lineage.

The database transaction, not a process-local lock, is the concurrency boundary. This works across
workers and processes sharing the same PostgreSQL authority.

## Crash and retry behavior

| Failure window | Durable state | Recovery |
| --- | --- | --- |
| Before claim | No accepted identity | Normal retry claims the identity. |
| After claim or calculation, before commit | An in-progress leased claim; no successful run | The worker abandons the claim on handled persistence failure. A crashed worker's lease expires and a new fencing token may take over. |
| During atomic publication | PostgreSQL commits all owned records or none | Retry either takes over an expired claim or recovers the completed winner. |
| After commit, before response | Completed claim and one authoritative run | Identical retry returns the original run. |

A worker that loses its fencing token cannot publish. A still-active winner is reported as
in-progress, not as a fabricated storage failure. A completed claim whose run is absent is a
`503 DPM_IDEMPOTENCY_STORE_INCONSISTENT` integrity incident.

## Tenant ownership and legacy history

New run, mapping, history, claim, artifact, workflow, and support-bundle access paths are fenced by
the owning tenant. Foreign and missing scopes receive product-safe denial without object disclosure.

Migration `0032_rebalance_submission_ownership.sql` does not guess ownership for historical rows.
It keeps old runs with `tenant_id IS NULL` and renames the original unscoped mapping table to
`dpm_run_idempotency_legacy_unattributed`. Normal tenant-scoped APIs match neither. Any future
attribution requires separately governed evidence and migration; destructive cleanup or default
assignment is prohibited.

## Operational limits

This contract proves correctness and bounded recovery. It does not, by itself, certify production
IAM, throughput, database failover, multi-region behavior, or horizontal capacity. Those require
deployment-specific identity and measured runtime evidence.

The deprecated `DPM_IDEMPOTENCY_REPLAY_ENABLED` and cache-size settings do not weaken durable
admission. They may remain accepted for compatibility while the runtime always enforces this
contract.

## Verification

Required evidence includes:

1. independent financial oracle and sequential replay/conflict regression tests;
2. supported HTTP concurrency resolving to one run;
3. separate-process PostgreSQL claim contention;
4. expired-claim takeover and post-restart winner readback;
5. same-key cross-tenant independence and foreign read denial;
6. upgrade migration proof preserving unattributed legacy history.

Run from the `lotus-manage` repository root:

```powershell
python -m pytest tests/unit/dpm/api/test_api_rebalance.py -q
$env:DPM_POSTGRES_INTEGRATION_DSN='<postgres-dsn>'
$env:DPM_POSTGRES_INTEGRATION_REQUIRED='1'
python -m pytest tests/integration/dpm/supportability/test_rebalance_submission_ownership_postgres.py -q
```

The PostgreSQL proof must not be replaced by mocked repository lookups or replica-count claims.
