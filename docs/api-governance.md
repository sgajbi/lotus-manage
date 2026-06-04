# Lotus Manage API Governance

This document is the API-governance baseline for `lotus-manage` surfaces.

## Public contract expectations

- All API operations should declare:
  - `summary`
  - `description`
  - one or more `tags`
  - stable `operationId`
  - request/response models
- Operations should document at least one standard 4xx/5xx response contract.
- OpenAPI and API vocabulary checks are required in repository lanes.
- Endpoint naming and parameter style should remain compatible with existing contract families in
  `src/api`.

## Surfaces and conventions

- Public operational surfaces should remain explicit in routing and documentation:
  - `/api/v1/...` portfolio/rebalance and management surfaces
  - `/health`, `/health/live`, `/health/ready` public health surfaces
  - internal metrics/logging surfaces as implemented by observability contracts
- Pagination, filtering, sorting, and cursor continuity should be consistent within each list family.
- Idempotency-sensitive mutations must carry stable behavior under retries.
- Correlation identifiers should be accepted when provided and propagated through downstream calls.

## Error handling

- Service and transport failures should map to consistent problem-details or standardized supportability posture.
- Unsupported capabilities should be represented with explicit boundary evidence rather than inferred ownership.
- Retryable upstream failures should surface bounded supportability states where current code paths already use
  fail-closed contracts.

## Governance gates

- `make openapi-gate`
- `make api-vocabulary-gate`
- `make no-alias-gate`
- `make lint`, `make typecheck`
- Quality evidence is reported by `quality-baseline.yml` and `quality/*.md` artifacts.
