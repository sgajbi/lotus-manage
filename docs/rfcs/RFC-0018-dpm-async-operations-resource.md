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

### 4.1 API Surface

- `POST /rebalance/analyze/async`
  - Returns `202 Accepted` with operation resource.
  - Uses request `X-Correlation-Id` when provided; otherwise generates one.
  - Echoes resolved `X-Correlation-Id` in response header.
  - Includes `execute_url` in accepted payload for deferred execution workflows.
- `GET /rebalance/operations/{operation_id}`
  - Returns operation state, `is_executable` signal, and once complete, normalized result/error envelope.
- `GET /rebalance/operations/by-correlation/{correlation_id}`
  - Deterministic lookup for support teams and orchestrators.
- `POST /rebalance/operations/{operation_id}/execute`
  - Executes pending operation for `ACCEPT_ONLY` flows and returns updated status payload.

### 4.2 Storage and Compatibility

- First slice may use existing in-memory supportability repository patterns.
- Storage contract must be adapter-friendly so SQL persistence can be added without API contract changes.
- Existing synchronous `POST /rebalance/analyze` remains canonical and fully supported.

## 5. Test Plan

- Accept + poll happy path.
- Not found cases.
- Feature flag disabled case.
- Correlation lookup happy path.
- Operation status transition coverage.

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

Deferred to later slices:
- Worker/queue-backed execution mode.

## 7. Status and Reason Code Conventions

- Operation lifecycle status values are strictly: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`.
- Business domain run status semantics remain unchanged (`READY`, `PENDING_REVIEW`, `BLOCKED`) per RFC conventions.
