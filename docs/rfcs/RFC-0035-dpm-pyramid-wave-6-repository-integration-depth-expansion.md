# RFC-0035: lotus-manage Pyramid Wave 6 - Repository Integration Depth Expansion

## Problem Statement
lotus-manage test coverage is at `99%`, but the integration slice remains below target pyramid guidance (`<15%`). Existing integration tests validate API workflows well, but repository boundary cases still have partial parity versus unit scaffolds.

## Proposed Change
Add meaningful PostgreSQL repository-integration tests for:
- lotus-manage supportability repository (`dpm_runs`): cursor edge cases, filter combinations, workflow-decision paging, summary aggregation semantics, and retention guardrails.
- Advisory proposal repository (`proposals`): simulation idempotency persistence, list pagination/cursor semantics, workflow event/approval ordering, transition without approval, and version retrieval paths.
- lotus-manage policy-pack repository: empty-state behavior, rich policy definition roundtrip, deterministic ordering, and delete semantics.

## Architectural Impact
No runtime behavior changes. This RFC increases confidence at service-boundary persistence contracts and improves pyramid balance with integration-heavy validation.

## Risks and Trade-offs
- Slightly longer integration test runtime.
- More fixtures/data setup to maintain.

Mitigations:
- Keep tests deterministic and scoped to repository contracts.
- Reuse existing fake-or-live DSN fixture strategy.

## Implementation Plan
1. Add integration tests in three repository integration modules.
2. Run ruff + targeted integration suites.
3. Run full pytest with coverage gate (`--cov-fail-under=99`).
4. Open PR and merge after CI green.

## Success Criteria
- New tests pass in fake and live-Postgres modes.
- Coverage gate remains at or above 99%.
- Integration test count increases enough to move lotus-manage closer to target pyramid distribution.
