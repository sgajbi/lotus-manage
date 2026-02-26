# ADR-0004: lotus-manage Async Operation Selection and Correlation Contract

- Status: Accepted
- Date: 2026-02-20
- Owners: lotus-manage API / Platform

## Context

Supportability and orchestration needs differ by endpoint latency profile. lotus-manage required a clear policy for which operations should expose asynchronous contracts and how business/support users should retrieve operation state deterministically.

## Decision

Use an explicit async-operation resource pattern for long-running or orchestration-heavy endpoints, with mandatory operation-id retrieval and correlation-id lookup.

Current async operations:

1. `POST /rebalance/analyze/async`
   - Retrieve by:
     - `GET /rebalance/operations/{operation_id}`
     - `GET /rebalance/operations/by-correlation/{correlation_id}`

Not selected for async (currently):

1. `POST /rebalance/simulate`
   - Kept synchronous due short-lived deterministic execution and existing idempotency replay support.
2. Support lookup endpoints
   - Already read-only, low-latency retrieval paths.

Correlation contract:

1. Accept `X-Correlation-Id` when supplied.
2. Generate one when omitted.
3. Persist correlation id on operation record.
4. Support deterministic lookup by correlation id for support workflows.

## Why

- Improves enterprise orchestration without forcing async complexity on all endpoints.
- Aligns lotus-manage with advisory operation-vocabulary patterns while preserving lotus-manage business semantics.
- Keeps API separation clean:
  - submission endpoint
  - operation status endpoint
  - correlation-based support endpoint

## Consequences

Positive:
- Better control for clients that cannot wait on long-running orchestration calls.
- Operational teams can troubleshoot with either operation id or correlation id.

Tradeoffs:
- Current in-memory operation index stores latest operation per correlation id.
- Full correlation history and durable operation backends remain future slices.

## Follow-ups

- Expand async support to additional endpoints only when latency and workflow needs justify.
- Add persistent operation store adapter and retention policy controls.
