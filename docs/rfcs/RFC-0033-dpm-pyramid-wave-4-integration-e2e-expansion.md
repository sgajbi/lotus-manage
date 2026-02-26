# RFC-0033 - DPM Pyramid Wave 4 Integration/E2E Expansion

## Problem Statement
DPM currently meets 99% coverage but still fails platform test-pyramid ratio targets because integration/e2e scenario depth is too low relative to unit tests.

## Root Cause
- Prior quality waves concentrated on unit-level correctness and supportability internals.
- Integration/e2e suites do not yet cover enough API matrix behavior (feature-flag gates, not-found paths, and supportability variant combinations).

## Proposed Solution
Add a dedicated integration/e2e expansion wave focused on:
- DPM supportability API feature-flag gate matrix.
- DPM supportability API not-found matrix across lookup variants.
- Advisory proposal lifecycle/support API gate and not-found matrix.
- E2E supportability and workflow lookup/error-path assertions.

## Architectural Impact
No production behavior changes. This improves confidence at service boundaries and lifts pyramid distribution toward target bands.

## Risks and Trade-offs
- Increased test runtime for integration/e2e jobs.
- Broader feature-flag matrix can increase flakiness if test isolation is weak.

## High-Level Implementation Approach
1. Add integration matrix tests in existing DPM and advisory API integration suites.
2. Add focused e2e matrix tests for lookup and not-found behavior.
3. Run `make test-integration`, `make test-e2e`, and `make test-all-fast`.
4. Monitor CI and merge once green.
