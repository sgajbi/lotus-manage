# RFC-0018: lotus-manage Async Operations Resource

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0013, RFC-0016, RFC-0017 |
| **Doc Location** | `docs/rfcs/RFC-0018-dpm-async-operations-resource.md` |

## 1. Executive Summary

Add asynchronous operation APIs for long-running lotus-manage workloads, starting with batch analysis:
- `POST /rebalance/analyze/async`
- `GET /rebalance/operations/{operation_id}`
- `GET /rebalance/operations/by-correlation/{correlation_id}`
- `POST /rebalance/operations/{operation_id}/execute`

## 2. Problem Statement

Large what-if batches can be slow and are currently synchronous, which creates timeout/orchestration pressure for enterprise clients.

## 3. Goals and Non-Goals

### 3.1 Goals
- Provide operation resource contract with deterministic status lifecycle.
- Reuse advisory-style operation vocabulary.
- Keep behavior configurable and backward compatible.

### 3.2 Non-Goals
- Replace existing synchronous endpoints.
- Distributed durable queue (tracked as a follow-up slice).

## 4. Proposed Design

- Operation statuses: `PENDING | RUNNING | SUCCEEDED | FAILED`
- Store operation metadata + result/error payload.
- Config:
  - `DPM_ASYNC_OPERATIONS_ENABLED` (default `true`)
  - `DPM_ASYNC_OPERATIONS_TTL_SECONDS` (default `86400`)
  - `DPM_ASYNC_EXECUTION_MODE` (`INLINE` for MVP; future worker-backed modes allowed)
  - `DPM_ASYNC_EXECUTION_LEASE_SECONDS` (default `300`, minimum `1`)

### 4.1 API Surface

- `POST /rebalance/analyze/async`
  - Returns `202 Accepted` with operation resource.
  - Uses request `X-Correlation-Id` when provided; otherwise generates one.
  - Echoes resolved `X-Correlation-Id` in response header.
  - Includes `execute_url` in accepted payload for deferred execution workflows.
  - Requires normalized `X-Tenant-Id`; correlation uniqueness is scoped to that tenant.
- `GET /rebalance/operations/{operation_id}`
  - Returns operation state, `is_executable` signal, and once complete, normalized result/error envelope.
- `GET /rebalance/operations/by-correlation/{correlation_id}`
  - Deterministic lookup for support teams and orchestrators.
- `POST /rebalance/operations/{operation_id}/execute`
  - Executes pending operation for `ACCEPT_ONLY` flows and returns updated status payload.

Every operation read, list, and execute is tenant scoped. A foreign or legacy NULL-tenant operation
is non-disclosing. Claiming is one atomic PostgreSQL compare-and-set from `PENDING`, or from
`RUNNING` only after its lease expires. Each successful claim receives an opaque fencing token and
increments `execution_attempt`. Status responses expose the attempt and lease expiry for recovery
triage but never serialize the token.

Terminal success or failure is accepted only from the current token. Repeating the same terminal
payload with that token is idempotent; a different payload, an earlier token, or a competing worker
is rejected without changing the authoritative result. A worker crash before publication leaves a
recoverable RUNNING row; general TTL cleanup never deletes RUNNING recovery state. Lease expiry
permits a new owner and increments the attempt. This provides durable ownership and restart
recovery, not a distributed queue, exactly-once calculation, measured capacity, or trade execution.

### 4.2 Storage and Compatibility

- PostgreSQL is the durable production profile; SQLite and in-memory adapters implement the same
  claim/fence semantics for supported local and test profiles.
- Migration `0033` preserves existing rows. Because their owner cannot be inferred, old rows retain
  `tenant_id = NULL` and are visible only through the read-only quarantine inventory. Existing
  PENDING, RUNNING, and terminal evidence is not silently reassigned or replayed.
- Existing synchronous `POST /rebalance/analyze` remains canonical and fully supported.

## 5. Test Plan

- Accept + poll happy path.
- Not found cases.
- Feature flag disabled case.
- Correlation lookup happy path.
- Operation status transition coverage.
- Separate-process PostgreSQL claim race, expired-lease restart, stale publication, tenant
  isolation, SQLite upgrade, and registered-HTTP financial regression proof.

## 6. Rollout

Additive only; synchronous APIs remain canonical and supported.

## 6.1 Implementation Status (2026-02-20)

Implemented in current codebase:
- Asynchronous API surface:
  - `POST /rebalance/analyze/async`
  - `GET /rebalance/operations/{operation_id}`
  - `GET /rebalance/operations/by-correlation/{correlation_id}`
- Operation lifecycle persistence in lotus-manage supportability repository:
  - `PENDING -> RUNNING -> SUCCEEDED | FAILED`
- Feature flag:
  - `DPM_ASYNC_OPERATIONS_ENABLED`
- TTL cleanup enforcement for async operation records:
  - `DPM_ASYNC_OPERATIONS_TTL_SECONDS`
- Execution mode:
  - `DPM_ASYNC_EXECUTION_MODE=INLINE` (default, execute immediately)
  - `DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY` (accept and persist `PENDING`; execution deferred)
  - Invalid execution mode values fall back to `INLINE`.
- Manual execute toggle:
  - `DPM_ASYNC_MANUAL_EXECUTION_ENABLED` (default `true`)
- Atomic tenant-owned execution claim, bounded lease, monotonic attempt, and token-fenced terminal
  publication across PostgreSQL, SQLite, and in-memory profiles.
- Status fields `execution_attempt` and `execution_lease_expires_at`; execution tokens remain
  internal and excluded from response serialization.

Deferred to later slices:
- Worker/queue-backed execution mode.

Review-draft reconciliation for issue #719: `<workspace-root>/review/lotus-manage` was inspected
during implementation and again before validation on 2026-10-01. It contained no files, so no
draft was adopted or superseded; repository implementation, this RFC, the operator runbook,
README, wiki, and repository context were reconciled directly.

## 7. Status and Reason Code Conventions

- Operation lifecycle status values are strictly: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`.
- Business domain run status semantics remain unchanged (`READY`, `PENDING_REVIEW`, `BLOCKED`) per RFC conventions.
