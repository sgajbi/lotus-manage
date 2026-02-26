# RFC-0030 - DPM Integration Pyramid Rebalance Wave 1

## Problem Statement

DPM currently has strong overall coverage but an underweighted integration bucket in the test pyramid.

## Root Cause

Most API workflow verification lives under `tests/unit` with mocked seams, while only a small set of true integration tests exist under `tests/integration`.

## Proposed Solution

Add integration API workflow tests that exercise router + service + in-memory persistence boundaries without heavy mocking:

- DPM rebalance simulation lifecycle with supportability lookups.
- Advisory proposal lifecycle creation/version/workflow timeline retrieval.

## Architectural Impact

No production code changes. Improves confidence in real service wiring and endpoint orchestration.

## Risks and Trade-offs

- Slightly longer integration suite runtime.
- Requires explicit test-state reset for singleton services and idempotency caches.

## High-Level Implementation

1. Add integration fixture to reset DPM runtime singletons between tests.
2. Add DPM run supportability integration workflow tests.
3. Add advisory proposal lifecycle integration workflow tests.
