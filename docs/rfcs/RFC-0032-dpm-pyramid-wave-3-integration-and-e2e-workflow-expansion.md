# RFC-0032 lotus-manage Pyramid Wave 3 - Integration and E2E Workflow Expansion

- Status: Implemented
- Created: 2026-02-24
- Last Reviewed: 2026-03-05
- Depends On: RFC-0031

## Executive Summary

RFC-0032 expanded contract-level validation depth across integration and E2E layers for DPM/advisory workflow APIs. The wave is implemented and provides broad boundary validation for supportability lookups, async operations, lineage filtering, workflow actions, and proposal lifecycle flows.

## Original Proposal

Wave-3 originally proposed integration/E2E expansion for:
1. supportability and async guardrails
2. lineage and workflow decision APIs
3. proposal async create/version contracts
4. E2E workflow paths for support-bundle options and lookup/decision behavior

No runtime behavior change was proposed; only verification depth.

## Implemented Test Architecture

Primary implementation artifacts:
1. `tests/integration/dpm/api/test_dpm_api_workflow_integration.py`
2. `tests/integration/proposals/test_proposals_api_integration.py`
3. `tests/e2e/demo/test_demo_scenarios.py`

### Integration Coverage Added

1. DPM supportability endpoint roundtrips:
   1. by run id
   2. by correlation id
   3. by idempotency key
2. Async operations lookup and list contracts.
3. Supportability summary behavior under status filter and flag conditions.
4. Support bundle optional section suppression semantics.
5. Lineage filtering by `edge_type`.
6. Workflow actions and decision-list contract behavior.
7. Proposal lifecycle, transitions, approvals, lineage, idempotency, supportability configuration.
8. Proposal async create/version and operation lookups.

### E2E Coverage Added

1. Demo-driven API flows for:
   1. supportability artifact flow
   2. idempotency history
   3. supportability summary metrics
   4. lineage filtering
   5. workflow decision listing
   6. advisory async create/version workflows
2. Lookup and feature-guard error matrix checks in E2E mode.

## Verification Design Patterns

1. Contract roundtrip pattern:
   1. perform write/action
   2. verify all lookup paths return the same entity id
2. Guard matrix pattern:
   1. toggle env feature flag
   2. assert stable domain error code in response body
3. Not-found matrix pattern:
   1. issue missing-entity requests across route variants
   2. assert consistent domain `detail` code
4. Scenario pack E2E pattern:
   1. load demo JSON input
   2. execute API workflow
   3. validate deterministic response shape and key business assertions

## Test-Pyramid Framing

Wave-3 is aligned to pyramid balancing:
1. unit tests prove local logic correctness
2. integration tests prove boundary contracts and persistence/routing semantics
3. E2E tests prove representative user workflows

For governance, ratio metrics should be tracked as:
1. `integration_ratio = integration_test_count / total_test_count`
2. `e2e_ratio = e2e_test_count / total_test_count`

## What Changed vs Original and Why It Is Better

1. Original scope listed categories; implementation delivered explicit matrix-style assertions across route variants and feature flags.
2. Original E2E scope was directional; implementation grounded it in executable demo scenarios with deterministic assertions.
3. Original proposal focused on DPM; implemented wave also hardened advisory proposal workflows in the same quality pass.

This provides stronger regression resistance and better defect localization than basic happy-path expansion.

## Remaining Delta

No material RFC-0032 functional delta remains. Later waves (RFC-0033+) extend depth further.
