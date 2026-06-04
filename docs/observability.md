# Lotus Manage Observability

## Contracted surfaces

- Health:
  - `/health`
  - `/health/live`
  - `/health/ready`
- OpenAPI/spec surfaces via `/docs` and managed OpenAPI contracts.
- Service and domain logs should include stable request identifiers and `correlation_id`.

## Metrics and telemetry

- HTTP request latency and outcome summaries are emitted by the application runtime and surfaced through
  service telemetry integrations.
- Structured logs should avoid raw payload leakage and retain bounded operational fields (route, outcome,
  request family, correlation).

## Traceability

- Correlation IDs should remain stable across async request paths.
- Persisted artifacts (runs, alternatives, operations, proof packs) should preserve deterministic ref IDs and
  lineage fields for downstream audit and troubleshooting.

## Contracts and validation

- Mesh and observability contracts are validated through:
  - `scripts/validate_observability_contracts.py`
  - `make mesh-contract-validate`
- Quality baseline logs are collected by `.github/workflows/quality-baseline.yml`.
