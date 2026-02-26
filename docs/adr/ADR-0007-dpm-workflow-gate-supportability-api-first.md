# ADR-0007: lotus-manage Workflow Gate Supportability Is API-First

## Status

Accepted

## Context

lotus-manage support/investigation workflows need workflow gate visibility and operator actions without requiring direct database access. RFC-0020 introduces run workflow state and decisions (`APPROVE`, `REJECT`, `REQUEST_CHANGES`) with audit metadata.

## Decision

Expose workflow gate supportability via explicit APIs:

- `GET /rebalance/runs/{run_id}/workflow`
- `POST /rebalance/runs/{run_id}/workflow/actions`
- `GET /rebalance/runs/{run_id}/workflow/history`

Feature flags control rollout and policy:

- `DPM_WORKFLOW_ENABLED` (default `false`)
- `DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES` (CSV list, default `PENDING_REVIEW`)

The workflow model is independent from business run status (`READY`, `PENDING_REVIEW`, `BLOCKED`) and preserves append-only decision history with actor/correlation metadata.

## Consequences

- Operations and support teams can investigate and act through documented APIs rather than querying storage directly.
- Auditability improves through structured decision records and deterministic transition rules.
- Persistence backends can evolve (in-memory to database) without changing API contracts.
