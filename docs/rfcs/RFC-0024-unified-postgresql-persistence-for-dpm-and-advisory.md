# RFC-0024: Unified PostgreSQL Persistence for DPM and Advisory

| Metadata | Details |
| --- | --- |
| **Status** | COMPLETED (SLICE 19) |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0014G, RFC-0017, RFC-0018, RFC-0019, RFC-0020, RFC-0023 |
| **Doc Location** | `docs/rfcs/RFC-0024-unified-postgresql-persistence-for-dpm-and-advisory.md` |

## 1. Executive Summary

Adopt PostgreSQL as the shared durable persistence backend for both DPM and advisory supportability/workflow lifecycles, using a common schema vocabulary and repository contracts while preserving existing API behavior.

## 2. Problem Statement

Current state is split between in-memory adapters (advisory and default DPM) and SQLite (optional DPM backend). This is useful for incremental delivery but not sufficient for enterprise scale, concurrency, audit retention, and operational consistency across both businesses.

## 3. Goals and Non-Goals

### 3.1 Goals

- Standardize on PostgreSQL for durable production persistence in both engines.
- Reuse common naming and storage patterns across DPM and advisory where domain concepts overlap.
- Preserve backward-compatible API contracts and feature-flagged rollout controls.
- Introduce migration discipline for schema evolution.

### 3.2 Non-Goals

- Build BI/reporting warehouse models in this RFC.
- Replace all local-development in-memory flows.
- Introduce breaking API contract changes.

## 4. Proposed Design

### 4.1 Backend Targets

- DPM supportability repository:
  - runs
  - idempotency mappings
  - async operations
  - workflow decisions
  - lineage edges (from RFC-0023 continuation)
- Advisory proposal lifecycle repository:
  - proposal aggregates
  - immutable versions
  - workflow events
  - approvals
  - idempotency mappings
  - async operations

### 4.2 Unified Vocabulary and Modeling Rules

- Shared technical concepts:
  - `correlation_id`
  - `idempotency_key`
  - `request_hash`
  - `created_at`, `updated_at`
  - append-only event/decision records
- Domain-specific states stay separated:
  - DPM run workflow states and actions
  - advisory proposal workflow states and events
- Persist canonical JSON snapshots for deterministic replay and artifact rebuilding.

### 4.3 Migration and Tooling

- Introduce schema migration tooling and versioned migration files.
- Enforce forward-only migrations for production paths.
- Add repository contract tests runnable against:
  - in-memory adapters
  - SQLite adapters (optional local profile)
  - PostgreSQL adapters (CI integration profile)

### 4.4 Configurability

- DPM:
  - extend `DPM_SUPPORTABILITY_STORE_BACKEND` to include `POSTGRES`
  - connection config via `DPM_SUPPORTABILITY_POSTGRES_DSN`
- Advisory:
  - add `PROPOSAL_STORE_BACKEND` (`IN_MEMORY` | `POSTGRES`)
  - connection config via `PROPOSAL_POSTGRES_DSN`

### 4.5 Rollout Phases

1. Schema baseline and Postgres adapters behind flags.
2. Dual-run verification (in-memory/SQLite vs Postgres parity checks).
3. Enable Postgres in non-prod, then prod.
4. Keep in-memory fallback for local/dev tests.

## 5. Test Plan

- Contract tests for repository parity across backends.
- API regression suite with Postgres backend enabled for DPM and advisory.
- Migration smoke tests on empty and pre-seeded databases.
- Determinism tests for artifact and replay-related payloads after persistence.

## 6. Rollout/Compatibility

- Feature-flagged and additive.
- Existing APIs remain unchanged.
- Existing default local behavior remains available.
- Postgres becomes recommended production backend for both domains.

## 7. Status and Reason Code Conventions

- No change to business status vocabularies:
  - DPM run status: `READY`, `PENDING_REVIEW`, `BLOCKED`
  - DPM workflow status: `NOT_REQUIRED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`
  - advisory workflow states remain as defined in RFC-0014G
- Reason code naming remains uppercase snake case.

## 8. Implementation Status

- Implemented (slice 1):
  - DPM supportability backend contract now recognizes `POSTGRES` in configuration.
  - Added DSN setting:
    - `DPM_SUPPORTABILITY_POSTGRES_DSN`
  - Guardrail behavior for early rollout:
    - missing DSN raises `DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED`
    - placeholder backend mode currently raises `DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED`
  - Existing default behavior remains unchanged (`IN_MEMORY` by default, `SQL`/`SQLITE` path unchanged).
- Implemented (slice 2):
  - Added `PostgresDpmRunRepository` backend scaffold and factory wiring for DPM supportability.
  - Initialization guardrails:
    - missing DSN raises `DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED`
    - missing `psycopg` dependency raises `DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING`
  - Unimplemented operations currently fail explicitly with:
    - `DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED`
  - API guardrail:
    - supportability endpoints map backend initialization errors to HTTP `503` with explicit
      detail codes (for example DSN/driver issues).
- Implemented (slice 3):
  - Added pinned runtime dependency:
    - `psycopg[binary]==3.3.3`
  - Added Docker Compose Postgres runtime profile:
    - `docker-compose --profile postgres up -d --build`
    - `postgres:17.6` with healthcheck and persistent named volume.
  - Added deployment documentation for:
    - `DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES`
    - `DPM_SUPPORTABILITY_POSTGRES_DSN=...`
- Implemented (slice 4):
  - Added concrete Postgres supportability repository subset:
    - `save_run`
    - `get_run`
    - `save_run_artifact`
    - `get_run_artifact`
  - Added table bootstrap for:
    - `dpm_runs`
    - `dpm_run_artifacts`
  - Added repository unit coverage using fake Postgres connection semantics to validate
    deterministic SQL adapter behavior without external DB dependency.
- Implemented (slice 5):
  - Added concrete Postgres supportability repository operations for:
    - idempotency mapping CRUD
    - idempotency history append/list
    - async operation create/update/get/list
    - async operation TTL purge
  - Added table bootstrap for:
    - `dpm_run_idempotency`
    - `dpm_run_idempotency_history`
    - `dpm_async_operations`
  - Added deterministic unit coverage for filters, cursor behavior, and purge semantics.
- Implemented (slice 6):
  - Added concrete Postgres supportability repository operations for:
    - workflow decisions append/list/list-filtered
    - lineage edges append/list
    - supportability summary aggregation
    - run retention purge with related-entity cleanup
  - Added table bootstrap for:
    - `dpm_workflow_decisions`
    - `dpm_lineage_edges`
  - Added unit coverage for:
    - workflow filtering and cursor behavior
    - lineage retrieval by source/target entity
    - summary counters and status distributions
    - retention purge cascade behavior
- Implemented (slice 7):
  - Added concrete Postgres run lookup/list parity helpers:
    - `get_run_by_correlation`
    - `get_run_by_request_hash`
    - `list_runs`
  - Added unit coverage for:
    - run listing filters (`from`, `to`, `status`, `request_hash`, `portfolio_id`)
    - run listing cursor paging and invalid cursor behavior
    - correlation/request-hash lookup semantics
- Implemented (slice 8):
  - Added live Postgres repository integration contract tests (docker-gated) covering:
    - run persistence, lookups, filters, cursor pagination, and artifact retrieval
    - idempotency mapping/history, workflow decisions, lineage edges, and summary aggregation
    - async operation pagination/TTL purge and run retention cascade purge semantics
  - Test runtime guard:
    - tests run only when `DPM_POSTGRES_INTEGRATION_DSN` is set.
  - Manual runtime validation completed on `2026-02-20`:
    - uvicorn with `POSTGRES` backend
    - Docker container runtime with `POSTGRES` backend
    - simulate -> run lookup by correlation -> supportability summary flow validated.
- Implemented (slice 9):
  - Added advisory repository backend configuration contract:
    - `PROPOSAL_STORE_BACKEND` supports `IN_MEMORY` and `POSTGRES`.
    - `PROPOSAL_POSTGRES_DSN` added for Postgres backend wiring.
  - Added advisory router lazy repository initialization with explicit `503` mapping for backend
    initialization errors.
  - Added advisory Postgres backend scaffold with explicit guardrail error:
    - `PROPOSAL_POSTGRES_NOT_IMPLEMENTED`
  - Added unit and API tests for advisory backend config and `503` guardrail behavior.
- Implemented (slice 10):
  - Added advisory backend init error normalization for stable operational contracts:
    - passthrough of known runtime guardrails (`PROPOSAL_POSTGRES_DSN_REQUIRED`,
      `PROPOSAL_POSTGRES_DRIVER_MISSING`, `PROPOSAL_POSTGRES_NOT_IMPLEMENTED`)
    - unexpected initialization failures mapped to `PROPOSAL_POSTGRES_CONNECTION_FAILED`
  - Added advisory Postgres scaffold driver guard:
    - missing `psycopg` dependency raises `PROPOSAL_POSTGRES_DRIVER_MISSING`
  - Added deterministic tests for advisory config and API error mapping behavior.
  - Added Docker/runtime env passthrough for advisory Postgres backend:
    - `PROPOSAL_STORE_BACKEND`
    - `PROPOSAL_POSTGRES_DSN`
- Implemented (slice 11):
  - Added advisory supportability/config diagnostics endpoint:
    - `GET /rebalance/proposals/supportability/config`
  - Endpoint provides stable operational diagnostics without direct DB access:
    - configured backend
    - backend readiness
    - backend initialization error code (when not ready)
    - lifecycle/support/async and behavior toggles
  - Added API coverage for default and backend-error diagnostic responses.
- Implemented (slice 12):
  - Added first advisory Postgres repository parity subset:
    - idempotency mapping
      - `get_idempotency`
      - `save_idempotency`
    - async operation persistence and lookups
      - `create_operation`
      - `update_operation`
      - `get_operation`
      - `get_operation_by_correlation`
  - Added advisory Postgres table bootstrap for:
    - `proposal_idempotency`
    - `proposal_async_operations`
  - Added repository unit coverage for roundtrips, updates, correlation lookup, and stable
    unimplemented-method guardrail behavior.
- Implemented (slice 13):
  - Added advisory Postgres repository parity for proposal aggregate and version persistence:
    - proposal aggregate:
      - `create_proposal`
      - `update_proposal`
      - `get_proposal`
      - `list_proposals` (filters + deterministic cursor paging)
    - immutable versions:
      - `create_version`
      - `get_version`
      - `get_current_version`
  - Added advisory Postgres table bootstrap for:
    - `proposal_records`
    - `proposal_versions`
  - Added repository unit coverage for:
    - proposal create/update/get/list behavior
    - version create/get/current behavior
    - cursor paging and invalid-cursor semantics
- Implemented (slice 14):
  - Added advisory Postgres repository lifecycle parity for workflow and approvals:
    - workflow events:
      - `append_event`
      - `list_events`
    - approvals:
      - `create_approval`
      - `list_approvals`
    - transactional lifecycle transition:
      - `transition_proposal` (proposal upsert + event append + optional approval write)
  - Added advisory Postgres table bootstrap for:
    - `proposal_workflow_events`
    - `proposal_approvals`
  - Added repository unit coverage for:
    - workflow event roundtrip and ordering behavior
    - approval roundtrip behavior
    - transition persistence semantics across proposal/event/approval records
- Implemented (slice 15):
  - Added advisory Postgres live integration contract tests (docker-gated):
    - test runtime guard:
      - tests run only when `PROPOSAL_POSTGRES_INTEGRATION_DSN` is set.
    - covered repository parity contracts:
      - idempotency
      - async operations
      - proposal aggregate/version persistence
      - workflow events
      - approvals
      - transactional `transition_proposal`
  - Manual runtime validation completed on `2026-02-20`:
    - uvicorn with advisory Postgres backend enabled
    - Docker Compose with advisory + DPM Postgres backends enabled
    - full demo pack validation succeeded in both runtime modes.
- Implemented (slice 16):
  - Added shared forward-only PostgreSQL migration runner:
    - `src/infrastructure/postgres_migrations.py`
    - migration history table:
      - `schema_migrations(version, namespace, checksum, applied_at)`
    - checksum guardrail:
      - raises `POSTGRES_MIGRATION_CHECKSUM_MISMATCH:{namespace}:{version}` when applied
        migration content diverges from checked-in SQL.
  - Added versioned baseline SQL migration files:
    - `src/infrastructure/postgres_migrations/dpm/0001_baseline.sql`
    - `src/infrastructure/postgres_migrations/proposals/0001_baseline.sql`
  - Updated repository initialization to run migrations instead of inline table bootstrap:
    - `PostgresDpmRunRepository._init_db`
    - `PostgresProposalRepository._init_db`
  - Added migration tooling script:
    - `scripts/postgres_migrate.py`
    - supports `--target dpm|proposals|all` and DSN injection via args/env.
  - Added migration unit coverage:
    - idempotent/forward-only apply behavior
    - checksum mismatch guardrail
    - compatibility with existing Postgres repository scaffold tests.
- Implemented (slice 17):
  - Added CI Postgres migration smoke job:
    - starts live Postgres service (`postgres:17.6`)
    - applies migrations via `python scripts/postgres_migrate.py --target all`
    - runs live Postgres integration contracts for:
      - DPM repository
      - advisory repository
  - Added production rollout runbook:
    - `docs/documentation/postgres-migration-rollout-runbook.md`
    - covers startup sequencing, checksum guardrails, CI smoke checks, and forward-only
      rollback strategy.
  - Updated project documentation to reflect current Postgres maturity and migration-first
    startup contract.
- Implemented (slice 18):
  - Added namespace-scoped migration lock strategy:
    - `apply_postgres_migrations` now acquires/releases PostgreSQL advisory locks during
      migration execution.
    - lock key is deterministic per namespace (`dpm`, `proposals`) and stable across processes.
  - Added migration lock coverage:
    - lock and unlock executed for successful migration apply
    - lock and unlock executed even when checksum mismatch raises
    - lock key stability and namespace isolation assertions
  - Updated migration rollout runbook with concurrency/race safety guidance.
- Implemented (slice 19):
  - Added explicit production cutover checklist evidence:
    - `docs/demo/postgres-cutover-checklist-2026-02-20.md`
  - Confirmed completion criteria across:
    - migrations
    - locking
    - CI smoke checks
    - live integration coverage
    - manual runtime validation
- Next slice:
  - none (RFC-0024 complete).
