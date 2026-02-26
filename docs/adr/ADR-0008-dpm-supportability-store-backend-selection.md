# ADR-0008: DPM Supportability Store Backend Selection

## Status

Accepted

## Context

RFC-0023 requires durable supportability storage while preserving current in-memory behavior for local development and backward compatibility. The DPM supportability domain now includes run records, idempotency mappings, async operation records, and workflow decision records.

## Decision

Introduce backend selection for DPM supportability repository:

- `DPM_SUPPORTABILITY_STORE_BACKEND`
  - `IN_MEMORY` (default)
  - `SQL` (SQLite-backed in current implementation)
  - `SQLITE` (backward-compatible alias of `SQL`)
  - `POSTGRES` (reserved rollout profile; requires explicit DSN)
- `DPM_SUPPORTABILITY_SQL_PATH`
  - file path used when backend is `SQL` (preferred)
- `DPM_SUPPORTABILITY_SQLITE_PATH`
  - backward-compatible file path alias
- `DPM_SUPPORTABILITY_POSTGRES_DSN`
  - DSN used when backend is `POSTGRES`
  - empty/missing DSN is rejected
  - `psycopg` driver must be installed for `POSTGRES` backend initialization

Repository interface remains unchanged so services and API contracts are storage-agnostic.

## Consequences

- Production-style durability can be enabled without API changes.
- Local default remains fast and compatible with existing tests.
- Backend parity is protected with repository contract tests across in-memory and SQLite adapters.
