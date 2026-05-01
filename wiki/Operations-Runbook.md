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

- `GET /rebalance/supportability/summary` returns `supportability.state`,
  `supportability.reason`, and `supportability.freshness_bucket` for management action register
  surfaces.
- Operators should treat `empty` as no persisted run or operation evidence, `stale` as old
  supportability evidence, and `degraded` as failed async operation evidence.
- `/metrics` exposes `lotus_manage_action_register_supportability_total` with only bounded
  `surface`, `supportability_state`, `reason`, and `freshness_bucket` labels. The recorder
  allowlists label values and falls back to `unknown_surface`, `supportability_summary_error`, or
  `unknown` rather than emitting raw caller values.
- Do not add portfolio ids, request hashes, idempotency keys, correlation ids, actor ids, or client
  content to supportability metric labels or log dimensions.
- Capability consumers should gate this posture on
  `manage.observability.action_register_supportability` from `/integration/capabilities` or
  `/platform/capabilities`.

## Docker production readiness

- Compose waits for the internal PostgreSQL service to be healthy before starting
  `lotus-manage`.
- The application command runs `python scripts/postgres_migrate.py --target all` before `uvicorn`.
- The runtime image includes the migration script and the `psycopg` runtime driver required for
  Postgres-backed supportability stores.
- A healthy container should have the `schema_migrations` table plus DPM and proposal persistence
  tables. If `/rebalance/supportability/summary` returns a Postgres connection or migration error,
  inspect the startup logs first for migration failures.
- For canonical front-office proof, `GET /rebalance/supportability/summary` should return HTTP
  `200`. An `empty` supportability state is acceptable for a freshly seeded stack with no recorded
  management actions; HTTP `503` is not acceptable demo evidence.

## Key references

- [docs/documentation/project-overview.md](../docs/documentation/project-overview.md)
- [docs/documentation/postgres-migration-rollout-runbook.md](../docs/documentation/postgres-migration-rollout-runbook.md)
- [docs/runbooks/service-operations.md](../docs/runbooks/service-operations.md)
- [docs/standards/enterprise-readiness.md](../docs/standards/enterprise-readiness.md)
- [docs/standards/migration-contract.md](../docs/standards/migration-contract.md)
- [docs/standards/scalability-availability.md](../docs/standards/scalability-availability.md)
