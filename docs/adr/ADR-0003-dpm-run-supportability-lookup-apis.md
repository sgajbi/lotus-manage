# ADR-0003: lotus-manage Run Supportability Lookup APIs

- Status: Accepted
- Date: 2026-02-20
- Owners: lotus-manage API / Platform

## Context

lotus-manage now enforces idempotency replay semantics and propagates correlation ids. Operational teams still needed deterministic API-level lookups for run investigations without direct log or database access.

## Decision

Introduce read-only lotus-manage supportability endpoints:

1. `GET /rebalance/runs/{rebalance_run_id}`
2. `GET /rebalance/runs/by-correlation/{correlation_id}`
3. `GET /rebalance/runs/idempotency/{idempotency_key}`

Implement with repository port + in-memory adapter:
- `src/core/dpm_runs/repository.py`
- `src/infrastructure/dpm_runs/in_memory.py`

Record run metadata and result payload after simulation execution:
- run id
- correlation id
- request hash
- optional idempotency key
- portfolio id
- result payload

Guard endpoints with runtime feature toggle:
- `DPM_SUPPORT_APIS_ENABLED` (default `true`)

## Why

- Aligns lotus-manage operational supportability with advisory lifecycle patterns.
- Improves incident response and auditability with deterministic retrieval paths.
- Preserves clean separation of concerns (API router vs domain support service vs storage adapter).

## Consequences

Positive:
- Faster L1/L2 investigation and clearer client retry diagnostics.
- No impact on simulation domain outcomes.

Tradeoffs:
- In-memory storage is process-local and not durable across restarts.
- Cross-instance query consistency requires a future persistent adapter.

## Follow-ups

- Add persistent run store adapter for distributed deployment.
- Add retention and redaction policy controls for stored run payloads.
