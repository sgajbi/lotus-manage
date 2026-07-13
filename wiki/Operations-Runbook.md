# Operations Runbook

This page is the current operator runbook for `lotus-manage` runtime support, supportability
diagnostics, campaign workflow recovery, outcome-review support, and container readiness. Its
evidence posture is implementation-backed by the named API routes, bounded metrics, repository
tests, OpenAPI/observability validators, and wiki publication checks referenced below; unsupported
external workflow, OMS/order, fill/settlement, and client-contact behavior remains out of Manage
scope unless a future source-owning service publishes and certifies that capability.

## Reader Map

| Reader need | Use this section | Evidence source |
| --- | --- | --- |
| First response and runtime checks | Important operational checks | `/health/ready`, `/metrics`, repo-native smoke checks |
| Action-register observability | RFC-0108 action register supportability | `lotus_manage_action_register_supportability_total` and related supportability metrics |
| Campaign workflow triage | Campaign workflow telemetry | `lotus_manage_campaign_workflow_total` and monitoring contract alerts |
| Campaign recovery and replay | Campaign workflow operations | Campaign definition routes, launch history, workflow board, assignment tasks, and maker-checker pages |
| Outcome-review supportability | RFC-0042 outcome review supportability | Outcome-review supportability API and bounded metrics |
| Container readiness | Docker production readiness | Compose health, migrations, and readiness logs |

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
- `/health/ready` validates production persistence guardrails, trusted write authorization posture,
  bounded Postgres access policy, and applied migrations in production profile, so container
  health is tied to supportability backing-store and authz readiness instead of `/docs`

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
- `/metrics` exposes `lotus_manage_postgres_access_total` with bounded `operation`, `outcome`,
  `reason`, and `classification` labels for runtime Postgres connection acquisition and driver
  failures. Do not add DSNs, portfolio ids, request hashes, query text, table names, or payload
  content to these labels or related log fields.
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

## Campaign workflow telemetry

- `/metrics` exposes `lotus_manage_campaign_workflow_total` with bounded `surface`, `outcome`,
  and `reason` labels for campaign workflow mutation, preview readiness, launch package, launch,
  and launch-history surfaces.
- Surfaces are route-family values such as `approval_decision`, `assignment_action`,
  `assignment_task_open`, `assignment_task_transition`, `maker_checker_control`,
  `preview_readiness`, `launch_package`, `launch`, and `launch_history`. Do not use campaign ids,
  portfolio ids, actor ids, request hashes, idempotency keys, correlation ids, or trace ids as
  metric labels.
- Outcomes distinguish `success`, `replay`, `conflict`, `validation_failed`,
  `entitlement_failed`, `not_found`, `blocked`, and `error`. Reasons are low-cardinality codes
  such as `reference_conflict`, `entitlement_denied`, `definition_not_found`, `task_not_found`,
  `launch_blocked`, `validation_error`, and `unexpected_error`.
- First response should separate operator action by outcome: investigate `entitlement_failed` as a
  campaign governance or actor-allow-list defect, `conflict` as a duplicate reference or
  idempotency mismatch, `not_found` as stale workflow references, `blocked` as readiness failure,
  and `error` as an implementation or infrastructure fault.
- Campaign launch is intentionally recoverable across the durable wave write and the campaign
  launch-history write. If `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch`
  returns HTTP 409 with `BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE` after wave creation, inspect
  the deterministic launch idempotency key and retry the same request. The retry must replay the
  existing wave, append the missing launch-history record idempotently, and avoid creating a second
  wave. If launch history is already present, replay must leave the page total unchanged.
- Dashboard panels and alert rules are governed by
  `contracts/observability/lotus-manage-monitoring.v1.json`. Run
  `python scripts/validate_observability_contracts.py` after changing campaign workflow metric code
  or monitoring contracts.

## Campaign workflow operations

Campaign workflow evidence is Manage-owned audit and supportability state. Operators should use the
public campaign routes, bounded metrics, and repo-native tests as the normal support path; manual
database edits are not the normal recovery mechanism.

First checks:

| Check | Route or command | Operator decision |
| --- | --- | --- |
| Service readiness | `GET /health/ready` | Stop if migrations or persistence guardrails are not ready. |
| Current campaign definition | `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}` | Confirm lifecycle status, content hash, governance, and source-backed candidate posture. |
| Workflow overview | `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview` | Compare readiness, lifecycle, launch-history, and optional launch-package posture in one read model. |
| Product queue posture | `GET /api/v1/rebalance/waves/campaign-operating-queue`, `GET /api/v1/rebalance/waves/campaign-approval-inbox`, `GET /api/v1/rebalance/waves/campaign-workflow-board` | Decide whether the issue is launch readiness, approval posture, actor routing, or closed/inactive state. |
| Assignment posture | `GET /api/v1/rebalance/waves/campaign-assignment-plan`, `GET /api/v1/rebalance/waves/campaign-workflow-automation` | Distinguish read-only assignment readiness from actual task mutation. |
| Metrics | `/metrics`, `lotus_manage_campaign_workflow_total` | Classify failures by bounded `surface`, `outcome`, and `reason`; never add campaign ids, actor ids, portfolio ids, idempotency keys, or correlation ids as labels. |

Evidence-family triage:

| Symptom | Diagnosis endpoint | Safe action |
| --- | --- | --- |
| Missing or stale launch history after a launch response | `GET .../launch-history` and `GET .../lifecycle-events` | Retry the same launch request with the same requested as-of date, actor, and correlation/idempotency context. The deterministic launch idempotency key must replay the existing wave and append the missing launch audit without creating another wave. |
| Approval-decision conflict | `GET .../approval-decisions` | Treat duplicate `decision_ref` with changed payload as a 409 conflict. Do not rewrite stored approval evidence; issue a new decision ref or escalate to engineering if the original evidence is wrong. |
| Assignment-action conflict or stale posture | `GET .../assignment-actions`, `GET .../campaign-assignment-plan` | Use the latest action page and assignment plan. Duplicate changed action refs are conflicts; record a new action ref for a new assignment decision. |
| Assignment-task transition conflict | `GET .../assignment-tasks?status=<state>` | Confirm current task status and transition refs. Replay identical transition refs only when payload matches; otherwise use a new transition ref or escalate for incorrect stored evidence. |
| Maker-checker exception or invalid completion posture | `GET .../maker-checker-controls` | Confirm a compatible submission/reviewer cycle and open exception exists before completion/resolution. Invalid shortcuts must fail closed; do not infer approval state from free text. |
| Workflow board or automation page is empty/stale | `GET .../campaign-workflow-board`, `GET .../campaign-workflow-automation`, then `GET .../workflow-overview` | Confirm active lifecycle, approval/expiry/entitlement posture, assignment-plan posture, and existing task state. Empty may be correct for closed, ineligible, unsupported, or not-ready campaigns. |
| External workflow, OMS, or client-contact assumption appears in an incident | Supported-feature page and route payload boundaries | Escalate as a non-claim. Manage does not orchestrate external workflow systems, contact clients, approve trades, generate orders, route orders, claim OMS execution, ingest fills, or settle trades. |

Recovery and replay posture:

- Approval decisions, assignment actions, assignment tasks/transitions, maker-checker controls, and
  launch audit writes use stable refs or deterministic launch idempotency. Identical replay is
  safe; same-ref changed payloads must fail as conflicts.
- Campaign workflow appends use optimistic content-hash protection. A stale append returns
  `BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE`/HTTP 409 rather than overwriting newer evidence.
- Campaign launch is recoverable after partial wave creation as described above. This is the only
  current cross-aggregate campaign recovery path; other workflow evidence families remain
  single-aggregate appends guarded by refs and content hashes.
- Campaign workflow telemetry from #580, stale-write protection from #582, launch-audit retry
  proof from #583, and the #586 PostgreSQL workflow projection are implemented on this branch.
  The projection is derived from `dpm_bulk_review_campaign_definitions.payload_json` and
  `content_hash`, refreshed after successful writes, and queryable for default board/assignment
  filters. Treat it as a rebuildable operator read model, not the durable evidence source.
- Keep incident notes source-safe. Do not paste raw campaign payloads, portfolio ids, client data,
  actor ids, idempotency keys, correlation ids, request hashes, source hashes, or diagnostics
  payloads into screenshots, logs, metric labels, or public incident summaries.

Escalation:

- Escalate Manage-owned state issues when campaign definition lifecycle, launch history, assignment
  tasks, maker-checker controls, or workflow read models contradict their persisted evidence pages.
- Escalate source-owner issues to the owning service when candidate membership, source refs,
  mandate binding, PM-book, risk-event, tactical house-view, risk, performance, market-data, or
  portfolio facts are unavailable, incomplete, degraded, or stale.
- Escalate Gateway/Workbench issues when Manage responses are correct but downstream BFF/UI
  rendering, pagination, empty-state, or boundary presentation is wrong.
- Escalate external workflow, OMS, order, fill, settlement, and client-communication requests as
  unsupported owner-scope gaps unless a future source-owning service publishes and certifies the
  required source product.

Validation after supportability changes:

```powershell
python -m pytest tests/unit/dpm/api/test_waves_api.py tests/unit/dpm/waves/test_campaign_definition_repository.py -q
python scripts/validate_observability_contracts.py
python scripts/openapi_quality_gate.py
```

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
- Runtime Postgres adapters share the bounded access policy controlled by
  `DPM_POSTGRES_MAX_CONNECTIONS`, `DPM_POSTGRES_CONNECT_TIMEOUT_SECONDS`,
  `DPM_POSTGRES_STATEMENT_TIMEOUT_MS`, `DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS`, and
  `DPM_POSTGRES_ACQUIRE_TIMEOUT_SECONDS`. Invalid production values fail readiness with
  `POSTGRES_ACCESS_POLICY_INVALID:*` or `POSTGRES_ACCESS_POLICY_OUT_OF_RANGE:*`.
- `POSTGRES_CONNECTION_ACQUIRE_TIMEOUT` indicates the process-local connection budget is exhausted
  for longer than the configured acquisition timeout. `POSTGRES_CONNECTION_UNAVAILABLE` indicates
  the driver could not connect within policy or the database rejected the connection. Treat both as
  infrastructure/capacity incidents; do not add blind write retries in repositories.
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
