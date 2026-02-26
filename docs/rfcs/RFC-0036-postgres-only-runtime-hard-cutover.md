# RFC-0036: PostgreSQL-Only Runtime Hard Cutover

## Problem Statement
`lotus-advise` still contains legacy runtime backend support paths (`IN_MEMORY`, `SQL`, `SQLITE`, `ENV_JSON`) even though platform direction is strict PostgreSQL-owned persistence for runtime services.

## Root Cause
- Prior RFCs transitioned production mode first, but retained legacy runtime backends for transitional compatibility.
- Runtime config helpers still default/fallback to legacy backends and expose alias environment variables.

## Proposed Solution
Perform a hard cutover to PostgreSQL-only runtime persistence:
- `DPM_SUPPORTABILITY_STORE_BACKEND` must resolve to `POSTGRES` only.
- `PROPOSAL_STORE_BACKEND` must resolve to `POSTGRES` only.
- `DPM_POLICY_PACK_CATALOG_BACKEND` must resolve to `POSTGRES` only.
- Remove runtime fallback behavior to `IN_MEMORY`/`SQL`/`SQLITE`/`ENV_JSON`.
- Remove SQLite path alias handling in runtime config.
- Update tests, docs, and examples to reflect strict runtime contract.

## Architectural Impact
- Strengthens service boundaries and runtime determinism.
- Eliminates hidden divergence between local and production persistence behavior.
- Aligns DPM runtime with platform governance: no legacy runtime backend support.

## Risks and Trade-offs
- Local bootstrap now requires PostgreSQL DSNs and setup.
- Older scripts/env files that relied on legacy backends will fail fast.

Mitigations:
- Clear startup/runtime error messages.
- Runbook updates with canonical environment examples.

## High-Level Implementation Approach
1. Update runtime backend config functions to accept only `POSTGRES`.
2. Remove legacy repository instantiation paths.
3. Update unit/integration tests for strict behavior.
4. Update docs and examples to remove legacy runtime backend guidance.
5. Validate with lint/type/test gates and merge.

## Success Criteria
- Runtime backend selection no longer supports legacy values.
- Test suites validate strict POSTGRES-only configuration.
- Documentation consistently describes PostgreSQL-only runtime behavior.

