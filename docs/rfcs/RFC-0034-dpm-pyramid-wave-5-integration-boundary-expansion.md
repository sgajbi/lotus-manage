# RFC-0034 - DPM Pyramid Wave 5 Integration Boundary Expansion

## Problem Statement
DPM remains outside target test-pyramid ratios despite strong coverage because integration/e2e scenario breadth is still comparatively low.

## Root Cause
- Existing integration coverage emphasizes happy-path roundtrips.
- Boundary behavior for workflow/supportability/advisory lifecycle routes is not fully matrix-tested at API layer.

## Proposed Solution
Expand integration coverage with boundary matrices:
- DPM workflow lookup/action not-found and feature-flag guard matrices.
- Advisory lifecycle/support/async feature-flag guard matrices.
- Advisory post-route not-found matrices for transitions and approvals.

## Architectural Impact
No runtime behavior changes. This is integration-safety hardening for API contracts and boundary handling.

## Risks and Trade-offs
- Additional integration runtime and CI minutes.
- Requires strict test isolation for env flag toggles and in-memory stores.

## High-Level Implementation Approach
1. Add matrix-driven integration cases in existing DPM and advisory API integration suites.
2. Validate with targeted integration runs and full coverage-gated suite.
3. Merge and re-measure pyramid distribution.
