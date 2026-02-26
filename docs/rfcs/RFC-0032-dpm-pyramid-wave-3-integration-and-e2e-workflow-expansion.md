# RFC-0032 lotus-manage Pyramid Wave 3 - Integration and E2E Workflow Expansion

## Problem Statement
lotus-manage currently passes the 99% coverage gate but remains significantly unit-heavy in test-pyramid distribution, leaving integration and E2E contract behavior underrepresented.

## Root Cause
Most API and workflow validation was implemented under `tests/unit`, while integration and E2E suites expanded slower than feature delivery.

## Proposed Solution
Add a focused wave of integration and E2E tests for high-risk lotus-manage and Advisory workflows:
1. lotus-manage supportability and async guardrails.
2. lotus-manage lineage and workflow decision APIs.
3. Proposal async create/version workflow contracts.
4. E2E workflow paths for support-bundle optional sections, lineage filters, workflow decision listing, and proposal async flows.

## Architectural Impact
No runtime behavior or API contract changes. This is a verification-depth increment to strengthen cross-boundary confidence.

## Risks and Trade-offs
- CI runtime increases modestly.
- Additional maintenance as workflow contracts evolve.

## High-Level Implementation Approach
1. Extend integration suites under `tests/integration/dpm/api` and `tests/integration/advisory/api`.
2. Extend E2E workflow coverage under `tests/e2e/demo`.
3. Validate with targeted suites plus full lotus-manage coverage gate.
