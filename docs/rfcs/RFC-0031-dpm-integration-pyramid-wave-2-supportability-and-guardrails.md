# RFC-0031 DPM Integration Pyramid Wave 2 - Supportability and Guardrails

## Problem Statement
DPM backend coverage meets threshold, but integration-test proportion remains below the target pyramid range. Critical supportability and feature-guardrail API behaviors need stronger integration-level validation.

## Root Cause
Existing integration tests focused on main happy paths and did not sufficiently validate:
- support-bundle lookup variants
- idempotency history endpoints
- feature-flag guardrails (disabled API surfaces)
- supportability config backend error signaling

## Proposed Solution
Add integration workflow tests for:
1. DPM support-bundle lookups (by correlation/idempotency/operation).
2. DPM idempotency history endpoint behavior under feature flags.
3. DPM supportability summary guardrail when disabled.
4. Proposal supportability config backend readiness/error branch.
5. Proposal support/idempotency endpoints and disabled-support guardrail.

## Architectural Impact
No runtime logic changes. Validation depth increases for existing API contracts and guardrail behavior.

## Risks and Trade-offs
- Low runtime risk (tests only).
- Slight CI runtime increase due to expanded integration suite.

## High-Level Implementation Approach
1. Extend existing integration API workflow test files under `tests/integration/dpm/api` and `tests/integration/advisory/api`.
2. Validate with integration suite execution and lint checks.
3. Merge increment and re-measure pyramid distribution.
