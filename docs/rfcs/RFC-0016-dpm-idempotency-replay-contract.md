# RFC-0016: lotus-manage Idempotency Replay Contract for `/rebalance/simulate`

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0001, RFC-0002, RFC-0007A |
| **Doc Location** | `docs/rfcs/RFC-0016-dpm-idempotency-replay-contract.md` |
| **Compatibility** | Non-breaking; strengthens existing required `Idempotency-Key` semantics |

## 1. Executive Summary

This RFC defines and implements explicit idempotency semantics for `POST /rebalance/simulate`:
- same `Idempotency-Key` + same canonical request payload -> return cached result
- same `Idempotency-Key` + different canonical request payload -> return `409 Conflict`

This aligns lotus-manage behavior with advisory simulation behavior and improves enterprise-grade retry safety.

Implementation note (2026-02-20):
- Implemented in `src/api/main.py` with canonical request hashing and bounded in-memory replay cache.
- API tests added in `tests/unit/dpm/api/test_api_rebalance.py`.
- Runtime controls delivered:
  - `DPM_IDEMPOTENCY_REPLAY_ENABLED`
  - `DPM_IDEMPOTENCY_CACHE_MAX_SIZE`

## 2. Problem Statement

`/rebalance/simulate` currently requires `Idempotency-Key` but does not enforce replay/conflict semantics. This creates ambiguity and increases operational risk for:
- client retry handling
- replayability and reconciliation investigations
- API consistency between lotus-manage and advisory

## 3. Goals and Non-Goals

### 3.1 Goals
- Make idempotency behavior explicit, deterministic, and testable.
- Keep domain response contract unchanged (`READY | PENDING_REVIEW | BLOCKED` in body).
- Reuse existing canonical hash utility.
- Add bounded in-memory cache with configurable controls.

### 3.2 Non-Goals
- Persistent idempotency storage in this slice.
- New API endpoints for idempotency lookup (can be follow-up).
- Changing core lotus-manage simulation logic.

## 4. Proposed Design

### 4.1 Idempotency flow

For each `POST /rebalance/simulate` request:
1. Build canonical request payload hash via `hash_canonical_payload`.
2. Lookup by `Idempotency-Key` in an in-memory LRU cache.
3. If existing entry:
   - hash matches -> return cached `RebalanceResult`
   - hash differs -> return `409` with `IDEMPOTENCY_KEY_CONFLICT: request hash mismatch`
4. If no entry:
   - run simulation
   - store `{request_hash, response_json}`
   - enforce max cache size with LRU eviction

### 4.2 Configuration

Add environment-driven controls:
- `DPM_IDEMPOTENCY_REPLAY_ENABLED` (default `true`)
- `DPM_IDEMPOTENCY_CACHE_MAX_SIZE` (default `1000`)

When replay is disabled, endpoint behaves as pre-RFC (always computes response).

### 4.3 API Contract

- Endpoint remains `POST /rebalance/simulate`.
- `Idempotency-Key` remains required.
- `409 Conflict` now used for key/hash mismatch conflict.

## 5. Test Plan

Add API tests for:
1. same key + same payload returns same result payload.
2. same key + changed payload returns `409` + stable conflict message.
3. replay toggle disabled path computes fresh responses.
4. LRU capacity bound path is exercised.

## 6. Rollout and Compatibility

- Default behavior improves safely without breaking request/response shapes.
- Existing clients benefit immediately from deterministic replay semantics.
- Cache is in-memory and process-local in current architecture.

## 7. Status and Reason Code Conventions

No new domain statuses introduced.

New API-level conflict detail string:
- `IDEMPOTENCY_KEY_CONFLICT: request hash mismatch`
