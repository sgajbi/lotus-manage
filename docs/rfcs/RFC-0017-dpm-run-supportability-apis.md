# RFC-0017: lotus-manage Run Supportability APIs (Run, Correlation, Idempotency Lookup)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0001, RFC-0002, RFC-0016 |
| **Doc Location** | `docs/rfcs/RFC-0017-dpm-run-supportability-apis.md` |
| **Compatibility** | Non-breaking; additive read-only APIs |

## 1. Executive Summary

Introduce lotus-manage operational lookup APIs mirroring advisory supportability patterns:
- lookup run by `rebalance_run_id`
- lookup latest run by `correlation_id`
- lookup idempotency mapping by `Idempotency-Key`

These endpoints improve incident response, support triage, and audit traceability.

Implementation note (2026-02-20):
- Implemented router endpoints in `src/api/routers/dpm_runs.py`.
- Implemented support domain and repository port in `src/core/dpm_runs/`.
- Implemented in-memory adapter in `src/infrastructure/dpm_runs/in_memory.py`.
- Integrated run recording in `src/api/main.py` for `/rebalance/simulate` and `/rebalance/analyze`.
- Added API coverage in `tests/unit/dpm/api/test_api_rebalance.py`.

## 2. Problem Statement

lotus-manage now has idempotency replay semantics and correlation propagation, but lacks API retrieval surfaces for support teams. Troubleshooting currently requires log-level access instead of deterministic API-level evidence retrieval.

## 3. Goals and Non-Goals

### 3.1 Goals
- Provide read-only support APIs for run investigations.
- Reuse lotus-manage/advisory vocabulary (`request_hash`, `correlation_id`, idempotency mapping).
- Keep implementation configurable and architecture-aligned (port/adapter).

### 3.2 Non-Goals
- Full persistent database adapter in this slice.
- New business simulation behavior.
- Cross-instance durable run storage (deferred).

## 4. Proposed Design

### 4.1 Endpoints

- `GET /rebalance/runs/by-correlation/{correlation_id}`
- `GET /rebalance/runs/idempotency/{idempotency_key}`
- `GET /rebalance/runs/{rebalance_run_id}`

### 4.2 Storage model

Store run metadata and full result payload via repository port with in-memory adapter:
- run record:
  - `rebalance_run_id`
  - `correlation_id`
  - `request_hash`
  - `idempotency_key` (optional)
  - `portfolio_id`
  - `created_at`
  - `result_json`
- idempotency mapping:
  - `idempotency_key`
  - `request_hash`
  - `rebalance_run_id`
  - `created_at`

### 4.3 Configurability

- `DPM_SUPPORT_APIS_ENABLED` (default `true`)

When disabled, support endpoints return `404` with stable detail code.

## 5. Test Plan

Add API tests for:
- happy path for all three lookups
- not-found behavior
- feature toggle disabled behavior

## 6. Rollout and Compatibility

- Additive read-only endpoints; no breaking contract changes.
- In-memory adapter is MVP; persistent adapter can be introduced later behind same interface.

## 7. Status and Reason Code Conventions

No new simulation domain statuses.

Stable support API not-found details:
- `DPM_RUN_NOT_FOUND`
- `DPM_IDEMPOTENCY_KEY_NOT_FOUND`
- `DPM_SUPPORT_APIS_DISABLED`
