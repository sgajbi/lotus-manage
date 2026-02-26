# RFC-0025: PostgreSQL-Only Production Mode Cutover

| Metadata | Details |
| --- | --- |
| **Status** | COMPLETED |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0023, RFC-0024 |
| **Doc Location** | `docs/rfcs/RFC-0025-postgres-only-production-mode-cutover.md` |

## 1. Executive Summary

Define a staged production cutover plan where lotus-manage/advisory persistence uses PostgreSQL-only
backends in non-dev environments, while preserving in-memory/SQLite paths for local workflows.

## 2. Problem Statement

Multiple persistence modes remain available in all environments. This increases operational
variance and incident complexity in production.

## 3. Goals and Non-Goals

### 3.1 Goals

- Enforce Postgres-only persistence in production profiles.
- Preserve local development ergonomics with in-memory/SQLite.
- Provide explicit, reversible rollout gates.

### 3.2 Non-Goals

- Remove in-memory/SQLite codepaths from repository layer immediately.
- Change public API contracts.

## 4. Proposed Design

### 4.1 Environment Policy

- Add runtime mode switch:
  - `APP_PERSISTENCE_PROFILE` (`LOCAL` | `PRODUCTION`)
- In `PRODUCTION`:
  - `DPM_SUPPORTABILITY_STORE_BACKEND` must be `POSTGRES`
  - `PROPOSAL_STORE_BACKEND` must be `POSTGRES`
  - policy-pack catalog backend (when enabled) must be `POSTGRES`

### 4.2 Guardrails

- Startup validation fails fast with explicit reason codes when policy is violated.
- Existing migration checks and advisory lock controls from RFC-0024 remain mandatory.

### 4.3 Rollout Strategy

1. Shadow validation in CI and non-prod.
2. Enable `APP_PERSISTENCE_PROFILE=PRODUCTION` in non-prod.
3. Cut over production once error budgets remain healthy.
4. Keep `LOCAL` profile as default in local/dev docs.

## 5. Test Plan

- Unit tests for persistence-profile guardrails.
- API startup tests for explicit failure reason codes.
- CI profile running with production mode + Postgres migration smoke.

## 6. Rollout/Compatibility

- Additive and feature-flagged.
- No external API behavior changes.
- Local dev profile remains unchanged.

## 7. Status and Reason Code Conventions

- Proposed startup reason codes:
  - `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES`
  - `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN`
  - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES`
  - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN`
  - `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES`
  - `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN`

## 8. Implementation Progress

- Slice 1 completed (2026-02-21):
  - Added `APP_PERSISTENCE_PROFILE` guardrails (`LOCAL` | `PRODUCTION`).
  - Added startup fail-fast validation in app lifespan.
  - Enforced in `PRODUCTION`:
    - lotus-manage supportability backend must be `POSTGRES`.
    - advisory proposal store backend must be `POSTGRES`.
    - policy-pack catalog backend must be `POSTGRES` when policy packs/admin APIs are enabled.
  - Added unit tests and startup tests for all guardrail reason codes.
- Slice 2 completed (2026-02-21):
  - Added CI production-profile startup smoke job with Postgres services and migration pre-step.
  - Added startup guardrail tests for advisory and policy-pack production misconfiguration paths.
  - Updated deployment docs and runbook with explicit `LOCAL` vs `PRODUCTION` profile behavior.
- Slice 3 completed (2026-02-21):
  - Added CI negative guardrail job asserting startup fails with explicit reason codes for:
    - lotus-manage backend misconfiguration in `PRODUCTION`
    - advisory backend misconfiguration in `PRODUCTION`
    - policy-pack backend misconfiguration in `PRODUCTION` when policy packs are enabled
- Slice 4 completed (2026-02-21):
  - Added production cutover contract validation CLI (`scripts/production_cutover_check.py`)
    for profile/env + migration readiness checks.
  - Added CI execution of cutover contract validation in production-profile smoke flow.
  - Added production compose override (`docker-compose.production.yml`).
  - Updated rollout runbook/checklist to include cutover contract command and closure controls.
- Slice 5 completed (2026-02-21):
  - Expanded CI negative startup validation to cover all DSN guardrail reason codes:
    - `PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN`
    - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN`
    - `PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN`
- Slice 6 completed (2026-02-21):
  - Switched local container defaults to Postgres-backed runtime in `docker-compose.yml`.
  - Marked legacy runtime backends as deprecated via `DeprecationWarning`:
    - lotus-manage supportability: `IN_MEMORY`/`SQL`/`SQLITE`
    - advisory store: `IN_MEMORY`
    - policy-pack catalog: `ENV_JSON`
  - Captured rationale and transition policy in ADR-0011.
