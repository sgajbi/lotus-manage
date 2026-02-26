# ADR-0002: lotus-manage Simulate Idempotency Replay Contract

- Status: Accepted
- Date: 2026-02-20
- Owners: lotus-manage API / Platform

## Context

`POST /rebalance/simulate` requires `Idempotency-Key` but previously did not enforce replay or conflict semantics. This created inconsistency with advisory APIs and made client retry behavior ambiguous.

## Decision

Adopt explicit replay semantics for `POST /rebalance/simulate`:

1. same `Idempotency-Key` + same canonical request payload -> return cached result.
2. same `Idempotency-Key` + different canonical request payload -> return `409 Conflict` with:
   - `IDEMPOTENCY_KEY_CONFLICT: request hash mismatch`
3. use bounded in-memory LRU cache for current architecture.
4. keep behavior configurable:
   - `DPM_IDEMPOTENCY_REPLAY_ENABLED` (default `true`)
   - `DPM_IDEMPOTENCY_CACHE_MAX_SIZE` (default `1000`)

## Why

- Aligns lotus-manage and advisory API contracts.
- Reduces duplicate execution risk under network retries.
- Improves operational reproducibility and incident analysis.

## Consequences

Positive:
- Enterprise-safe retry semantics for front-office and integration clients.
- Deterministic API behavior under duplicate requests.

Tradeoffs:
- Replay cache is process-local and non-durable in current in-memory architecture.
- Cross-instance idempotency requires future persistent shared store.

## Follow-ups

- Add durable idempotency persistence for distributed deployment.
- Add supportability lookup endpoint(s) for lotus-manage idempotency keys if needed by operations.
