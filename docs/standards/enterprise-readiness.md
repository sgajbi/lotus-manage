# Enterprise Readiness Baseline (lotus-manage)

- Standard reference: `lotus-platform/Enterprise Readiness Standard.md`
- Scope: discretionary mandate decision workflows, policy enforcement, and run supportability APIs.
- Change control: RFC for platform-level changes, ADR for temporary exceptions.

## Security and IAM Baseline

- Enterprise audit middleware emits a structured JSON envelope for write responses and enterprise-policy denials. It records the asserted actor, tenant, role, correlation, action, policy version, timestamp, and status or denial reason; exact replays and conflicts remain distinguishable by status.
- Business metadata is redacted before serialization. The audit identity headers are caller assertions unless verified by a trusted ingress; JSON logger output is not proof of a durable audit sink, retention, or delivery.
- Ordinary logger `extra_fields` use a distinct allowlisted scalar contract. Credential and identity
  keys are redacted case-insensitively; unknown and structured values are discarded rather than
  copied into the JSON payload.

Evidence:
- `src/api/enterprise_readiness.py`
- `src/api/main.py`
- `src/api/observability.py`
- `tests/unit/api/test_enterprise_audit_json.py`
- `tests/unit/api/test_enterprise_readiness.py`
- `tests/unit/dpm/api/test_observability_api.py`

## API Governance Baseline

- API contracts are versioned and documented through OpenAPI.
- Backward compatibility and deprecation are governed by RFC process.

Evidence:
- `src/api/main.py`
- `tests/unit/dpm/contracts`
- `tests/integration`

## Configuration and Feature Management Baseline

- Feature controls are configured via `ENTERPRISE_FEATURE_FLAGS_JSON`.
- Tenant/role fallback resolution is deterministic and deny-by-default.

Evidence:
- `src/api/enterprise_readiness.py`
- `tests/unit/api/test_enterprise_readiness.py`

## Data Quality and Reconciliation Baseline

- Portfolio/input validation and decision constraints are enforced in domain services.
- Reconciliation and durability rules are documented under dedicated standards.

Evidence:
- `docs/standards/durability-consistency.md`
- `tests/unit/dpm/engine`

## Reliability and Operations Baseline

- Health/readiness, retry/timeout controls, migration gating, and supportability runbooks are enforced.

Evidence:
- `src/api/main.py`
- `docs/standards/scalability-availability.md`
- `docs/standards/migration-contract.md`

## Privacy and Compliance Baseline

- The serialized audit envelope preserves actor context and redacted metadata. Deployment still needs independently verified ingress identity and durable audit collection before claiming end-to-end audit-trail integrity.
- Ordinary operational logs preserve the documented HTTP/PostgreSQL/supportability scalar fields
  while rejecting arbitrary payload expansion. This is a serialization boundary, not evidence of
  production sink security or retention.

Evidence:
- `src/api/enterprise_readiness.py`
- `src/api/observability.py`
- `tests/unit/api/test_enterprise_audit_json.py`

## Deviations

- Deviations require ADR with mitigation and expiry review date.

