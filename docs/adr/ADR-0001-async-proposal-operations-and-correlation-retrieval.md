# ADR-0001: Async Proposal Operations and Correlation Retrieval

- Status: Accepted
- Date: 2026-02-20
- Owners: Advisory API / Engine

## Context

Advisory lifecycle endpoints now include simulation, artifact generation, persistence, workflow transitions, approvals, and supportability reads. Some workflows can be slow (simulation + artifact + persistence), and operations teams need clean, deterministic retrieval for investigation.

## Decision

Introduce an operation-resource pattern for asynchronous lifecycle workflows:

1. Async submission endpoints:
- `POST /rebalance/proposals/async`
- `POST /rebalance/proposals/{proposal_id}/versions/async`

2. Async retrieval endpoints:
- `GET /rebalance/proposals/operations/{operation_id}`
- `GET /rebalance/proposals/operations/by-correlation/{correlation_id}`

3. Operation statuses:
- `PENDING`
- `RUNNING`
- `SUCCEEDED`
- `FAILED`

4. Keep transitions and approvals synchronous:
- `POST /rebalance/proposals/{proposal_id}/transitions`
- `POST /rebalance/proposals/{proposal_id}/approvals`

5. Configuration flag:
- `PROPOSAL_ASYNC_OPERATIONS_ENABLED` (default `true`)

## Why

- Creates a stable contract for long-running business operations without polluting synchronous APIs.
- Preserves deterministic investigation workflows by supporting both `operation_id` and `correlation_id`.
- Keeps concerns separated:
  - lifecycle business logic in `ProposalWorkflowService`
  - operation persistence behind repository adapter
  - API orchestration in router layer

## Operation Suitability Matrix

- Run async now:
  - proposal create (simulate + artifact + persist)
  - proposal version create (re-simulate + artifact + persist)
- Keep sync now:
  - workflow transitions (must fail fast on state conflicts)
  - approvals/consent recording (state-sensitive and audit-critical)
  - read endpoints (already lightweight and deterministic)
- Deferred:
  - async lotus-manage batch analyze and async advisory simulate/artifact (can reuse same pattern later)

## Consequences

Positive:
- Better UX for front-office and middle-office systems under heavier requests.
- Clear supportability path for incident investigation.

Tradeoffs:
- Current implementation uses in-process background tasks and in-memory operation storage.
- Async operation state is not durable across process restarts until database-backed adapter is introduced.

## Follow-ups

- Add persistent operation store (PostgreSQL adapter) with retention policies.
- Add optional callback/webhook completion pattern for external orchestrators.
- Extend same operation pattern to selected lotus-manage workflows where latency justifies async behavior.
