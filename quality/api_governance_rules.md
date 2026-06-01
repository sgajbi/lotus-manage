# lotus-manage API Governance Rules

These rules define the report-only API-governance baseline for the enterprise-readiness refactor.

## OpenAPI Contract

1. Every endpoint should have a summary, description, tags, stable operation ID, request/response model, examples, and standard errors.
2. Error responses should use consistent platform problem-details semantics where applicable.
3. Public and internal endpoints should remain clearly separated.
4. Health, readiness, liveness, metrics, internal, and public endpoints should be documented as distinct operational surfaces.

## API Behavior

1. Pagination, filtering, sorting, versioning, and deprecation should be consistent across list/read APIs.
2. Correlation IDs should be accepted or generated and propagated to downstream calls.
3. Idempotent mutations should document idempotency key behavior, replay behavior, and conflict behavior.
4. Downstream unavailable/degraded states should be exposed as bounded supportability posture rather than hidden behind generic success.

## Current Gate Phase

OpenAPI and API vocabulary checks are active repo-native gates. The broader rule set is phase
1/report-only until each detector has a stable baseline and agreed thresholds.
