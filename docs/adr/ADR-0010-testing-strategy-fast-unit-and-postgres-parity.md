# ADR-0010: Testing Strategy - Fast Unit Feedback with PostgreSQL Parity Gates

## Status

Accepted

## Context

The platform now has two valid persistence modes by design:

- local developer flexibility (`LOCAL` profile with in-memory/SQLite allowed)
- production enforcement (`PRODUCTION` profile with Postgres-only guardrails)

As a solo-maintained codebase growing toward team onboarding, we need a test strategy that:

- keeps iteration fast day-to-day,
- still protects production parity for persistence-heavy workflows,
- and is explicit/documented for future contributors.

Running all tests on Postgres all the time improves parity but slows feedback and increases
infrastructure coupling for every code iteration.

## Decision

Adopt a layered testing model:

1. Lightweight unit tests by default:
   - use in-memory fakes/adapters for business-logic and contract-path testing.
   - remain the primary quick-iteration feedback mechanism.
   - primary suite location: `tests/unit/`.

2. Mandatory Postgres integration coverage for critical persistence flows:
   - DPM supportability repository live integration tests.
   - advisory proposal repository live integration tests.
   - DPM policy-pack Postgres repository live integration tests.
   - production-profile startup and guardrail reason-code checks in CI.
   - migration and cutover contract checks in CI.
   - integration suite location: `tests/integration/`.

3. Optional but recommended all-with-Postgres deep validation:
   - scheduled/manual nightly workflow runs integration + live API demo pack on Postgres.
   - not required for every quick local iteration.
   - end-to-end suite location: `tests/e2e/`.

## Consequences

Positive:

- Fast local feedback remains practical.
- Production parity risks are controlled by dedicated Postgres CI gates.
- New contributors get clear expectations for where each class of test belongs.

Trade-offs:

- Some local runs may still pass while Postgres-specific issues fail in integration/nightly checks.
- Requires disciplined maintenance of both test layers.

## Operational Guidance

- For quick iteration:
  - run `make check` (lint + mypy + unit tests).
- For persistence-sensitive changes:
  - run `make test-integration` locally.
- Before production changes:
  - run migrations + cutover contract checks.
  - use production-profile compose override where appropriate.

## CI Shape

- CI runs `tests/unit`, `tests/integration`, and `tests/e2e` in parallel jobs.
- Each suite emits a coverage artifact.
- CI combines artifacts and enforces a single global `99%` coverage gate.
