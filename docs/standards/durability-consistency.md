# Durability and Consistency Standard (lotus-manage)

- Standard reference: `lotus-platform/Durability and Consistency Standard.md`
- Scope: discretionary mandate workflow simulation, lifecycle review, and supportability writes.
- Change control: RFC required for policy changes; ADR required for temporary exceptions.

## Workflow Consistency Classification

- Strong consistency:
  - run/workflow operation state transitions
  - idempotency mapping persistence
- Eventual consistency:
  - asynchronous supportability/reporting fetch paths

## Idempotency and Replay Protection

- Critical write APIs require `Idempotency-Key`.
- Idempotency mapping/history repositories prevent duplicate business effects on retries.
- Evidence:
  - `src/api/routers/rebalance_simulation.py`
  - `src/infrastructure/rebalance_runs/postgres.py`

## Atomicity and Transaction Boundaries

- Run and workflow persistence uses explicit transaction boundaries in repository implementations.
- Partial workflow updates must fail and surface explicit errors.
- Evidence:
  - `src/infrastructure/rebalance_runs/postgres.py`

## As-Of and Reproducibility Semantics

- Request and response contracts preserve deterministic input scope and reproducibility metadata.
- Evidence:
  - `src/core/rebalance_runs/models.py`
  - `src/core/rebalance_runs/artifact.py`

## Concurrency and Conflict Policy

- Idempotency conflict behavior is explicit (same key + different payload -> conflict).
- Workflow action conflicts are exposed through deterministic API responses.
- Evidence:
  - `src/core/rebalance_runs/service.py`
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


