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

### Enterprise refusal coverage

Request observability is the outer application middleware envelope. Enterprise authorization and
write-body guards run inside it, so application-produced `400 invalid_content_length`,
`403 authorization_policy_denied`, and `413 payload_too_large` responses receive the same stable
correlation, request, trace, hardened-security, and enterprise-policy headers as routed responses.
Their Problem Details bodies carry `correlationId` and the request-path `instance`.

Each request contributes exactly one completion log and one HTTP count/latency observation. A
request refused before routing uses the bounded `unmatched` endpoint label; raw paths and identities
are never metric labels. Authorization denials retain their asserted-identity audit event, while
body-framing/size refusals do not invent an authorization audit. These controls prove local
instrumentation and propagation only, not collector export, durable retention, alert evaluation,
or production capacity.

### Ordinary JSON log field policy

`JsonFormatter` does not serialize arbitrary `LogRecord` attributes or arbitrary ordinary
`extra_fields`. The admitted ordinary field inventory is intentionally scalar and currently covers:

- HTTP completion: `http_method`, `endpoint`, `status_code`, `status_family`,
  `latency_bucket_ms`;
- PostgreSQL access: `operation`, `reason`, `classification`, `application_name`,
  `connection_budget`, `max_connections`, `acquire_timeout_seconds`,
  `connect_timeout_seconds`;
- bounded supportability summaries: `wave_state`, `supportability_state`, `outcome_state`,
  `reason`, `issue_count`, `dimension_count`, `blocked_dimension_count`,
  `degraded_dimension_count`, `unsupported_dimension_count`, `source_ref_count`.

Keys outside that inventory and dictionaries/lists supplied as ordinary values are discarded.
Credential-like keys (`password`, `secret`, `token`, `authorization`, and governed siblings) and
identity keys (`portfolio_id`, `account_id`, `client_id`, run/request/correlation identifiers, and
governed siblings) are normalized case-insensitively and emitted only as `[REDACTED]`. The
producer-inventory test fails when a new literal field is added without updating this policy.

The formatter's top-level correlation/request/trace context is a separate approved request context,
and the enterprise `audit` envelope has its own explicit serializer and recursive metadata
redaction. These local controls do not prove durable log delivery, retention, exported traces,
evaluated alerts, or a production-safe external sink.

## Traceability

- Correlation IDs should remain stable across async request paths.
- Persisted artifacts (runs, alternatives, operations, proof packs) should preserve deterministic ref IDs and
  lineage fields for downstream audit and troubleshooting.

## Contracts and validation

- Mesh and observability contracts are validated through:
  - `scripts/validate_observability_contracts.py`
  - `make mesh-contract-validate`
- Quality baseline logs are collected by `.github/workflows/quality-baseline.yml`.
- Formatter and producer-inventory regressions live in
  `tests/unit/dpm/api/test_observability_api.py`; enterprise audit-envelope regressions remain in
  `tests/unit/api/test_enterprise_audit_json.py`.
- The composed-application seven-control refusal and authorized-request reconciliation lives in
  `tests/unit/api/test_enterprise_refusal_observability.py`.
