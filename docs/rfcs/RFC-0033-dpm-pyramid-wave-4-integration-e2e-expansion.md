# RFC-0033 lotus-manage Pyramid Wave 4 - Integration and E2E Matrix Expansion

- Status: Implemented
- Created: 2026-02-24
- Last Reviewed: 2026-03-05
- Depends On: RFC-0032

## Executive Summary

RFC-0033 hardened Wave-3 by adding matrix-driven integration and E2E verification for feature-gate and not-found contracts across DPM supportability/workflow and advisory proposal APIs. The implementation is complete and active in the current test suite.

## Original Proposal

Wave-4 proposed focused expansion for:
1. feature-flag gate matrix coverage
2. not-found matrix coverage across lookup variants
3. advisory lifecycle/support not-found and guard behavior
4. E2E lookup/error-path assertions

## Implemented Scope and Evidence

Implemented in:
1. `tests/integration/dpm/api/test_dpm_api_workflow_integration.py`
2. `tests/integration/proposals/test_proposals_api_integration.py`
3. `tests/e2e/demo/test_demo_scenarios.py`

### DPM Integration Matrixes

1. Feature-gate matrix (`DPM_*_ENABLED` flags) for:
   1. support APIs
   2. async operations
   3. idempotency history
   4. supportability summary
   5. support bundle
   6. artifacts
   7. lineage
   8. workflow
2. Not-found matrix for:
   1. run lookups
   2. correlation lookups
   3. idempotency lookups
   4. async operation lookups
   5. support-bundle path variants
3. Workflow matrix:
   1. workflow lookup not-found matrix
   2. workflow feature-guard matrix
   3. workflow action not-found matrix
   4. workflow action feature-guard matrix

### Advisory Integration Matrixes

1. Lifecycle not-found matrix:
   1. missing proposal version
   2. missing proposal transitions/approvals
2. Async operation not-found checks:
   1. missing operation id
   2. missing operation correlation
3. Error contract checks:
   1. idempotency conflict
   2. invalid transition
   3. state conflict
   4. invalid approval state

### E2E Matrixes

1. DPM supportability lookup not-found matrix.
2. DPM feature-gate matrix in E2E context.
3. Workflow and lineage error-path assertions through demo-driven scenarios.

## Algorithmic Test Methodology

Wave-4 uses a matrix generation approach:
1. Define matrix `M = {(input_route_i, expected_error_j, feature_flag_k)}`.
2. Execute each tuple as an independent test case.
3. Assert:
   1. status code invariance per mode
   2. stable domain error vocabulary (`detail` codes)
   3. route-variant behavioral equivalence.

This enforces deterministic API error semantics under both disabled-feature and missing-entity conditions.

## What Changed vs Original and Why It Is Better

1. Original proposal requested matrixes; implementation delivered explicit parameterized tests, improving maintainability and reducing duplication.
2. Original proposal emphasized DPM supportability; implementation also strengthened advisory lifecycle failure semantics.
3. Original proposal targeted depth; implementation established repeatable matrix patterns reused in subsequent waves.

## Outdated vs Current Terminology

1. Legacy phrase "lookup variants" is now explicitly represented as:
   1. by run id
   2. by correlation id
   3. by idempotency key
   4. by async operation id/correlation
2. "Supportability internals" is now represented as explicit public API contracts and stable domain error codes.

## Remaining Delta

No material RFC-0033 delta remains for current service boundaries. Additional coverage depth continues in later wave RFCs.
