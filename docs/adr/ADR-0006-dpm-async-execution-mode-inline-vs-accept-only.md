# ADR-0006: lotus-manage Async Execution Mode (`INLINE` vs `ACCEPT_ONLY`)

- Status: Accepted
- Date: 2026-02-20
- Owners: lotus-manage API / Platform

## Context

RFC-0018 introduces asynchronous operation resources for lotus-manage analysis workflows. Teams need configurable behavior between immediate inline execution and acceptance-only mode where execution is delegated later.

## Decision

Introduce runtime configuration:

- `DPM_ASYNC_EXECUTION_MODE`
  - `INLINE` (default): accept operation and execute immediately in the API process.
  - `ACCEPT_ONLY`: accept operation and persist status as `PENDING`; no inline execution.
- `DPM_ASYNC_MANUAL_EXECUTION_ENABLED`
  - Enables `POST /rebalance/operations/{operation_id}/execute` for deferred execution flows.

Fallback behavior:
- Invalid values default to `INLINE` to preserve backward-compatible behavior.

## Why

- Supports both lightweight deployments (inline execution) and orchestrated enterprise flows (accept-only handoff).
- Keeps API contract stable across execution strategies.
- Avoids hard-coupling API service to queue/worker infrastructure in phase-2.

## Consequences

Positive:
- Configurable execution semantics without route/contract changes.
- Easier progressive rollout toward worker-backed execution.

Tradeoffs:
- `ACCEPT_ONLY` requires external executor to transition operations from `PENDING`.
- Without external executor, operations may remain pending by design.

## Follow-ups

- Add worker-backed execution mode and queue adapter in future RFC-0018 slice.
- Add operational metrics/alerts for stale `PENDING` operations.
