# Service Operations Runbook

## Standard Commands

- make lint
- make typecheck
- make ci
- docker compose up --build

## Health and Readiness

- Liveness: `/health/live` returns `{"status":"live"}` and does not touch persistence dependencies.
- Readiness: `/health/ready` returns `{"status":"ready"}` after persistence guardrails pass; in
  production profile it also validates required cutover migrations.
- General health: `/health` returns `{"status":"ok"}` for lightweight service health checks.
- Versioned aliases are available under `/api/v1/health`, `/api/v1/health/live`, and
  `/api/v1/health/ready`.
- OpenAPI docs: /docs

## Incident First Checks

1. Check container logs for request failures and stack traces.
2. Verify /health/ready and metrics endpoint.
3. Run local parity check (make ci) before hotfix PR.
