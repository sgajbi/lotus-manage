# ADR-0005: DPM Derived Run Artifact Strategy

- Status: Accepted
- Date: 2026-02-20
- Owners: DPM API / Platform

## Context

DPM run supportability APIs exposed run metadata and payloads, but no deterministic artifact contract for business users, investigations, and replay validation.

## Decision

Implement a derived artifact strategy as phase 1:

1. Add endpoint:
   - `GET /rebalance/runs/{rebalance_run_id}/artifact`
2. Build artifact deterministically from persisted run record (`DpmRunRecord`) without recomputing simulation logic.
3. Publish canonical artifact hash computed over stable artifact payload (excluding self hash field only).
4. Guard endpoint with `DPM_ARTIFACTS_ENABLED` feature toggle (default `true`).

Implementation is separated into dedicated module:
- `src/core/dpm_runs/artifact.py`

Service layer remains orchestration-only:
- `src/core/dpm_runs/service.py`

## Why

- Avoids coupling artifact shape to simulation execution paths.
- Preserves reproducibility while avoiding new persistence requirements in first slice.
- Mirrors advisory architecture pattern (separate artifact builder module) with DPM-specific models and vocabulary.

## Consequences

Positive:
- Deterministic, business-consumable artifact contract now available for every persisted run.
- Repeated reads return stable artifact hash for unchanged run records.

Tradeoffs:
- Phase 1 is derived-only from run records, not independently persisted artifacts.
- Request snapshot detail is constrained by currently stored supportability metadata.

## Follow-ups

- Add persisted artifact mode and storage adapter as optional backend.
- Expand request snapshot and lineage details when persistent supportability store is introduced.
