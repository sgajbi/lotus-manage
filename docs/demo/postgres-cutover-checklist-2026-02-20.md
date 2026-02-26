# PostgreSQL Cutover Checklist - 2026-02-20

## Scope

Production-style readiness checklist for RFC-0024 cutover controls.

## Checklist

- [x] Forward-only migration runner implemented (`src/infrastructure/postgres_migrations.py`)
- [x] Versioned baseline migrations committed for:
  - [x] `dpm` namespace
  - [x] `proposals` namespace
- [x] Checksum mismatch guardrail implemented and tested
- [x] Migration advisory lock strategy implemented and tested
- [x] Migration CLI implemented (`scripts/postgres_migrate.py`)
- [x] CI Postgres migration smoke job added (`.github/workflows/ci.yml`)
- [x] CI production profile startup smoke job added (`.github/workflows/ci.yml`)
- [x] CI production profile guardrail negative checks added (`.github/workflows/ci.yml`)
- [x] Live Postgres integration contracts present for:
  - [x] DPM repository
  - [x] advisory repository
- [x] Production cutover contract CLI added (`scripts/production_cutover_check.py`)
- [x] Production compose override published (`docker-compose.production.yml`)
- [x] Demo pack validated on uvicorn runtime with Postgres configuration
- [x] Demo pack validated on Docker runtime with Postgres configuration
- [x] Rollout runbook published (`docs/documentation/postgres-migration-rollout-runbook.md`)

## Result

RFC-0024 acceptance criteria are satisfied for unified PostgreSQL persistence rollout controls.
