# RFC-0019: lotus-manage Deterministic Run Artifact Contract

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0003, RFC-0013, RFC-0017 |
| **Doc Location** | `docs/rfcs/RFC-0019-dpm-deterministic-run-artifact-contract.md` |

## 1. Executive Summary

Introduce a deterministic run artifact contract for lotus-manage so every run can be retrieved as a stable business payload for support, replay validation, and lineage use cases.

## 2. Problem Statement

Current supportability APIs expose run metadata, but there is no single normalized artifact payload equivalent to advisory artifact practices. This makes downstream integration, investigation, and comparison harder.

## 3. Goals and Non-Goals

### 3.1 Goals

- Define a versioned lotus-manage run artifact schema.
- Keep artifact generation deterministic for the same stored run.
- Reuse vocabulary where advisory and lotus-manage overlap.
- Preserve existing endpoints and behavior.

### 3.2 Non-Goals

- Introduce report rendering formats (PDF, XLSX) in this slice.
- Recompute portfolio logic at artifact read time.

## 4. Proposed Design

### 4.1 API Surface

- `GET /rebalance/runs/{run_id}/artifact`
  - Returns a normalized artifact with:
    - request snapshot
    - rule outcomes
    - diagnostics
    - order intents
    - before/after holdings summaries
    - reproducibility metadata (`run_id`, `correlation_id`, `idempotency_key`, `engine_version`)

### 4.2 Contract Rules

- Artifact response is immutable for a persisted run.
- Artifact model is versioned (`artifact_version`) for forward-compatible evolution.
- If artifact persistence is disabled, API can synthesize from run payload using a deterministic adapter.

### 4.3 Configurability

- `DPM_ARTIFACTS_ENABLED` (default `true`)
- `DPM_ARTIFACT_STORE_MODE` (`DERIVED` | `PERSISTED`, default `DERIVED`)

### 4.4 Implementation Scope (2026-02-20)

Implemented in current codebase:
- `GET /rebalance/runs/{rebalance_run_id}/artifact`
- Deterministic artifact builder module:
  - `src/core/dpm_runs/artifact.py`
- Artifact hash from canonical payload for repeatable retrieval.
- Feature flag:
  - `DPM_ARTIFACTS_ENABLED`
- Artifact store mode:
  - `DPM_ARTIFACT_STORE_MODE=DERIVED` (default): artifact is deterministically generated from run payload at read time.
  - `DPM_ARTIFACT_STORE_MODE=PERSISTED`: artifact is persisted with run supportability record and read from repository.
  - Invalid mode values fall back to `DERIVED`.

Deferred:
- Expanded request snapshot persistence beyond current supportability record fields.

## 5. Test Plan

- Artifact retrieval happy path.
- Not found behavior.
- Deterministic equality for repeated reads.
- Feature flag disabled path.

## 6. Rollout/Compatibility

Additive endpoint only. Existing run and simulation APIs remain unchanged.

## 7. Status and Reason Code Conventions

- Artifact retrieval does not introduce new business statuses.
- Existing lotus-manage run status vocabulary remains: `READY`, `PENDING_REVIEW`, `BLOCKED`.
