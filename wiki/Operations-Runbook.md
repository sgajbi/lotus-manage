# Operations Runbook

## Important operational checks

- verify readiness and migration posture before trusting supportability endpoints
- confirm canonical host runtime uses port `8001` and ingress identity `manage.dev.lotus`
- treat run-support or workflow lookup failures as persistence or migration issues first
- use repo-native smoke and CI commands before inventing ad hoc runtime checks

## Operational truths

- host/runtime coexistence with `lotus-advise` is part of the service contract
- supportability flows depend on truthful run persistence, lineage, and idempotency history
- capability discovery is backend-owned and should not be inferred by downstream callers
- local Docker keeps PostgreSQL internal to the Compose network by default
- Docker startup applies PostgreSQL migrations before serving traffic
- `/health/ready` validates production persistence guardrails and applied migrations in production
  profile, so container health is tied to supportability backing-store readiness instead of `/docs`

## RFC-0108 action register supportability

- `GET /api/v1/rebalance/supportability/summary` returns `supportability.state`,
  `supportability.reason`, and `supportability.freshness_bucket` for management action register
  surfaces.
- Operators should treat `empty` as no persisted run or operation evidence, `stale` as old
  supportability evidence, and `degraded` as failed async operation evidence.
- `/metrics` exposes `lotus_manage_action_register_supportability_total` with only bounded
  `surface`, `supportability_state`, `reason`, and `freshness_bucket` labels. The recorder
  allowlists label values and falls back to `unknown_surface`, `supportability_summary_error`, or
  `unknown` rather than emitting raw caller values.
- `/metrics` exposes `lotus_manage_core_resolver_total` with only bounded `operation`, `outcome`,
  `supportability_state`, and `reason` labels for future stateful core resolver calls. It must not
  include portfolio ids, source payload identifiers, request hashes, or raw upstream error text.
- Dashboard panels and alert rules are governed by
  `contracts/observability/lotus-manage-monitoring.v1.json`. Add metrics to code and tests before
  referencing them in dashboard or alert contracts; `make mesh-contract-validate` checks that the
  contract only references implemented metrics.
- Do not add portfolio ids, request hashes, idempotency keys, actor ids, client content, raw
  upstream errors, or diagnostics payloads to supportability metric labels or free-text log
  messages. Correlation, request, and trace identifiers are allowed only as structured tracing
  context fields.
- HTTP access logs use route templates such as
  `/api/v1/rebalance/runs/by-request-hash/{request_hash}` rather than raw request paths, and emit
  bounded `status_family` and `latency_bucket_ms` fields. Do not replace those with raw path values
  or precise caller identifiers.
- Service-level log messages must use bounded event text. Do not embed correlation ids,
  idempotency keys, run ids, operation ids, request hashes, portfolio ids, diagnostics payloads, or
  raw upstream error text in message strings.
- Capability consumers should gate this posture on
  `manage.observability.action_register_supportability` from `/api/v1/integration/capabilities` or
  `/api/v1/integration/capabilities`.

## Docker production readiness

- Compose waits for the internal PostgreSQL service to be healthy before starting
  `lotus-manage`.
- The application command runs `python scripts/postgres_migrate.py --target dpm` before `uvicorn`.
- The runtime image includes the migration script and the `psycopg` runtime driver required for
  Postgres-backed supportability stores.
- A healthy container should have the `schema_migrations` table plus DPM supportability,
  workflow, lineage, and policy-pack persistence tables. If `/api/v1/rebalance/supportability/summary`
  returns a Postgres connection or migration error, inspect the startup logs first for migration
  failures.
- For canonical front-office proof, `GET /api/v1/rebalance/supportability/summary` should return HTTP
  `200`. An `empty` supportability state is acceptable for a freshly seeded stack with no recorded
  management actions; HTTP `503` is not acceptable demo evidence.

## Key references

- [docs/documentation/project-overview.md](../docs/documentation/project-overview.md)
- [docs/documentation/postgres-migration-rollout-runbook.md](../docs/documentation/postgres-migration-rollout-runbook.md)
- [docs/runbooks/service-operations.md](../docs/runbooks/service-operations.md)
- [docs/standards/enterprise-readiness.md](../docs/standards/enterprise-readiness.md)
- [docs/standards/migration-contract.md](../docs/standards/migration-contract.md)
- [docs/standards/scalability-availability.md](../docs/standards/scalability-availability.md)
