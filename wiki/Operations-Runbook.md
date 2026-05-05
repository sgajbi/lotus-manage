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
- `/metrics` exposes `lotus_manage_execution_total` with bounded `operation`, `input_mode`,
  `outcome`, and `result_status` labels for simulate, analyze, and async-analyze execution
  surfaces. Use it to monitor blocked, replayed, accepted, partial-failure, and error posture
  without inspecting request payloads.
- `/metrics` exposes `lotus_manage_async_operation_total` with bounded `event`, `execution_mode`,
  and `outcome` labels for async submit and execute lifecycle events.
- `/metrics` exposes `lotus_manage_policy_pack_resolution_total` with bounded `surface`,
  `enabled`, `source`, and `selected` labels for simulate, analyze, async analyze, and policy API
  lookups.
- `/metrics` exposes `lotus_manage_workflow_decision_total` with bounded `surface`, `action`, and
  `outcome` labels for mandate workflow actions. `surface` uses route-family values such as `run`,
  `trace`, and `retry`; it must not use raw correlation, idempotency, request, actor, run, or
  portfolio identifiers.
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

## RFC-0042 outcome review supportability

- `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability` returns
  operator-safe review diagnostics for RFC-0042 post-trade outcome reviews. The response includes
  review state, bounded reason codes, source-owner families, source-ref counts, dimension-state
  counts, freshness-state counts, and remediation routes.
- Treat `BLOCKED` dimensions as missing, conflicting, or invalid mandatory source evidence. Treat
  `DEGRADED` dimensions as partial, stale, unavailable, or non-critical evidence gaps. Treat
  `NOT_SUPPORTED` dimensions as explicitly unsupported until a source-owning app exposes and
  certifies the required post-trade contract.
- Remediation routes are operator hints by owner family, such as
  `lotus-risk:refresh-post-trade-risk-source`,
  `lotus-performance:refresh-post-trade-performance-source`,
  `execution-owner:certify-fill-and-order-evidence`, or
  `source-owner:refresh-realized-outcome-source`. They are not raw upstream URLs and must not
  include portfolio, client, actor, run, proof-pack, wave, source-payload, request-hash, or
  correlation identifiers.
- `/metrics` exposes `lotus_manage_outcome_review_supportability_total` with only bounded
  `surface`, `supportability_state`, and `reason` labels. `surface` is limited to route-family
  values for create, source refresh, and supportability. `supportability_state` and `reason` are
  allowlisted by code and contract.
- The metric is intended for create, source-refresh, supportability-read, not-found, blocked, and
  error posture. It must not include source hashes, raw source refs, review ids, portfolio ids,
  actor ids, proof-pack ids, wave ids, request hashes, idempotency keys, or raw upstream errors.
- Service logs for supportability inspection use the bounded
  `outcome_review.supportability.inspected` event and numeric counts only. Keep raw review ids,
  source refs, and source payload content out of message strings and free-text log fields.
- Report and AI endpoints are handoff contracts only:
  `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/report-input` and
  `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/ai-evidence-input` do not render
  reports, archive artifacts, create AI prompts, generate PM memos, or issue recommendations.
- Dashboard panels and alert rules are governed by
  `contracts/observability/lotus-manage-monitoring.v1.json`. Run
  `python scripts/validate_observability_contracts.py` after changing metric code or monitoring
  contracts.

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
