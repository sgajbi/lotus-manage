# Lotus Manage Security

## Threat and trust boundaries

- `lotus-manage` is a controlled backend API for managed workflow operations and does not own advisory
  client communication or order execution.
- Upstream and downstream calls should remain explicit, bounded, and auditable through service contracts.
- Security-sensitive methods should fail closed when required source/identity signals are missing.

## Operational controls

- Runtime configuration should use environment-based secret injection (no repository-checked credentials).
- Downstream failures are handled through bounded supportability states and explicit error contracts.
- Idempotency-sensitive mutation routes should not execute duplicate irreversible side effects.
- Authentication/authorization posture follows the runtime environment policy and upstream gateway requirements.

## Security checks in lanes

- `make security-audit`
- `pip-audit` and dependency checks in CI/quality slices
- `bandit` profile is included in report-only baseline

## Data handling

- Structured logging should avoid PII and secrets.
- Persisted supportability artifacts should retain only bounded review evidence and no claim to prohibited
  ownership (OMS execution, client approvals, communication artifacts, settlement truth).
