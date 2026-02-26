# Durability and Consistency Standard (DPM)

- Standard reference: `lotus-platform/Durability and Consistency Standard.md`
- Scope: discretionary and advisory workflow simulation/lifecycle write operations.
- Change control: RFC required for policy changes; ADR required for temporary exceptions.

## Workflow Consistency Classification

- Strong consistency:
  - proposal lifecycle writes
  - run/workflow operation state transitions
  - idempotency mapping persistence
- Eventual consistency:
  - asynchronous supportability/reporting fetch paths

## Idempotency and Replay Protection

- Critical write APIs require `Idempotency-Key`.
- Idempotency mapping/history repositories prevent duplicate business effects on retries.
- Evidence:
  - `src/api/routers/dpm_simulation.py`
  - `src/api/routers/proposals_lifecycle_routes.py`
  - `src/infrastructure/dpm_runs/postgres.py`
  - `src/infrastructure/proposals/postgres.py`

## Atomicity and Transaction Boundaries

- Run/proposal persistence uses explicit transaction boundaries in repository implementations.
- Partial workflow updates must fail and surface explicit errors.
- Evidence:
  - `src/infrastructure/dpm_runs/postgres.py`
  - `src/infrastructure/proposals/postgres.py`

## As-Of and Reproducibility Semantics

- Request and response contracts preserve deterministic input scope and reproducibility metadata.
- Evidence:
  - `src/core/dpm_runs/models.py`
  - `src/core/dpm_runs/artifact.py`

## Concurrency and Conflict Policy

- Idempotency conflict behavior is explicit (same key + different payload -> conflict).
- Workflow action conflicts are exposed through deterministic API responses.
- Evidence:
  - `src/core/advisory_engine.py`
  - `src/core/dpm_runs/service.py`
  - `tests/unit/core/*`

## Integrity Constraints

- Persistent stores enforce unique key constraints for run and idempotency entities.
- Input contracts enforce schema validation at API boundary.
- Evidence:
  - `src/infrastructure/postgres_migrations/*`
  - `src/core/*/models.py`

## Release-Gate Tests

- Unit: `tests/unit/*`
- Integration: `tests/integration/*`
- E2E: `tests/e2e/*`

## Deviations

- Deviation from idempotent write semantics or durable workflow persistence requires ADR with expiry review date.


