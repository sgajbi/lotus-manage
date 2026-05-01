# Codebase Review Ledger

This ledger records cleanup and structural review evidence for RFC-0036.

## RFC36-S2-001: Review control docs were missing

- Date: 2026-05-01
- Scope: `docs/architecture`, RFC-0036 cleanup slice
- Finding: the repository had RFC execution text and current-state docs, but no durable local ledger
  for pattern-based cleanup findings.
- Action: added `docs/architecture/README.md`,
  `docs/architecture/CODEBASE-REVIEW-PLAYBOOK.md`, and this ledger.
- Status: fixed
- Wiki decision: no wiki source change required; these are engineering control documents, not
  product/operator truth.

## RFC36-S2-002: Retired advisory/proposal package directories existed as generated remnants

- Date: 2026-05-01
- Scope: retired advisory and proposal package namespaces
- Finding: active Python modules had already been removed, but ignored `__pycache__` directories kept
  retired package namespaces present on disk.
- Action: removed the generated directories and tightened the current-state documentation test to
  guard both retired package namespaces.
- Status: fixed
- Wiki decision: no wiki source change required; the existing wiki already states that advisory
  proposal workflows belong to `lotus-advise`.

## RFC36-S2-003: Duplicate unversioned domain API mounts remain

- Date: 2026-05-01
- Scope: `src/api/main.py`
- Finding: unversioned product routers are still mounted alongside `/api/v1` routers.
- Action: deferred to RFC-0036 Slice 3 because it changes runtime endpoint behavior and must be
  implemented with route inventory, OpenAPI, vocabulary, docs, tests, and live evidence together.
- Status: deferred to Slice 3
- Wiki decision: no wiki source change in Slice 2.

## RFC36-S3-001: Duplicate product endpoint surface removed

- Date: 2026-05-01
- Scope: `src/api/main.py`, `src/api/routers/integration_capabilities.py`, OpenAPI inventory
- Finding: product routers were mounted both unversioned and under `/api/v1`, and capability
  discovery was exposed under both integration and platform namespaces.
- Action: removed unversioned product router mounts, removed the platform capability alias, kept
  health and metrics as unversioned infrastructure probes, and regenerated the API vocabulary
  inventory.
- Status: fixed
- Wiki decision: wiki source updated because endpoint and demo-facing product truth changed.

## RFC36-S4-001: Advisory-era client-consent workflow vocabulary removed

- Date: 2026-05-01
- Scope: DPM engine options, workflow gates, policy-pack contracts, tests, OpenAPI vocabulary, docs
- Finding: discretionary mandate workflow gates still exposed advisory-style client-consent fields
  and gate states. That wording is not domain-correct for DPM execution control.
- Action: replaced client-consent API vocabulary with mandate-approval vocabulary:
  `workflow_requires_mandate_approval`, `mandate_approval_already_obtained`,
  `MANDATE_APPROVAL_REQUIRED`, and `REQUEST_MANDATE_APPROVAL`.
- Status: fixed
- Wiki decision: wiki supported-features source updated to keep advisory client-consent ownership
  with `lotus-advise`.

## RFC36-S4-002: Retired proposal infrastructure remnants removed

- Date: 2026-05-01
- Scope: retired proposal infrastructure package and migration namespaces
- Finding: tracked proposal infrastructure code was already gone, but ignored generated remnants kept
  retired proposal directories present on disk.
- Action: removed generated remnants and expanded current-state tests so retired proposal
  infrastructure and migration namespaces stay absent.
- Status: fixed
- Wiki decision: no wiki source change required for generated local remnants.

## RFC36-S5-001: Stateless request envelope made explicit

- Date: 2026-05-01
- Scope: simulate, sync analyze, async analyze request contracts, demo payloads, OpenAPI inventory
- Finding: product endpoints still accepted direct inline bundles, which made it harder to add
  stateful `portfolio_id` mode without ambiguous request shapes.
- Action: added `StatelessRebalanceRequestEnvelope` and
  `StatelessBatchRebalanceRequestEnvelope`, moved demo/API request payloads under
  `stateless_input`, and added a regression test proving direct stateless bodies are rejected.
- Status: fixed
- Wiki decision: wiki endpoint certification and supported-features source updated because request
  contract truth changed.

## RFC36-S6-001: Stateful resolver seam added behind feature gate

- Date: 2026-05-01
- Scope: stateful request models, `lotus-core` resolver client, source-context transformation,
  lineage fields, API feature gate, OpenAPI vocabulary
- Finding: RFC-0036 required stateful `portfolio_id` execution, but the codebase had no typed
  selector model, no outbound resolver seam, and no deterministic way to tie core source lineage
  into run results.
- Action: added `DpmStatefulInput`, `DpmCoreExecutionContext`, source-lineage/supportability
  models, a bounded `DpmCoreResolverClient`, transformation helpers for simulate and batch
  analysis, optional stateful lineage fields on `LineageData`, and API routing that accepts
  `input_mode=stateful` but returns `DPM_STATEFUL_INPUT_DISABLED` unless
  `DPM_STATEFUL_CORE_SOURCING_ENABLED=true`.
- Status: fixed for modeled disabled state; live promotion remains deferred to Slice 7 pending
  governed `lotus-core` resolver evidence.
- Wiki decision: wiki endpoint certification and supported-features source updated because modeled
  stateful API and lineage truth changed.

## RFC36-S7-001: Stateful capability publication required stronger readiness gating

- Date: 2026-05-01
- Scope: integration capabilities, stateful simulate/analyze certification
- Finding: capability discovery could advertise `dpm.execution.stateful_portfolio_id` when
  `DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED=true` even if stateful core sourcing was disabled or no
  `DPM_CORE_BASE_URL` was configured.
- Action: changed capability publication so `stateful` appears in `supported_input_modes` only when
  the capability flag, `DPM_STATEFUL_CORE_SOURCING_ENABLED`, and `DPM_CORE_BASE_URL` are all present.
  Added API tests for no-false-publish behavior and local stateful simulate, sync analyze, and async
  analyze source-lineage proof with a mocked core resolver.
- Status: fixed for publication safety and local executable proof; live stateful promotion remains
  blocked by `sgajbi/lotus-core#330`.
- Wiki decision: wiki endpoint certification and supported-features source updated because
  capability publication and stateful proof posture changed.

## RFC36-S8-001: Mesh declaration referenced stale route and missed telemetry gate

- Date: 2026-05-01
- Scope: domain-data-product declaration, trust telemetry, mesh validation automation
- Finding: `PortfolioActionRegister:v1` still declared stale `/manage/portfolio-actions/{portfolio_id}`
  as its current route, even though the implemented management evidence surfaces are the rebalance
  supportability, artifact, and workflow route families. Repo-native trust telemetry existed, but no
  local wrapper or Make target validated it alongside domain-product declarations.
- Action: updated the product declaration to point at implemented supportability/artifact/workflow
  routes, set the serving plane to `query_control_plane_service`, added
  `scripts/validate_trust_telemetry_contracts.py`, added `make trust-telemetry-validate` and
  `make mesh-contract-validate`, and added tests for telemetry/declaration alignment plus the
  no-stateful-source-dependency promotion guard.
- Status: fixed for repo-native mesh truth; platform-wide catalog regeneration remains deferred to
  the platform aggregation flow.
- Wiki decision: wiki mesh product source updated because client/demo-facing mesh product truth
  changed.

## RFC36-S9-001: Access logs emitted raw supportability paths

- Date: 2026-05-01
- Scope: HTTP access logging, structured log formatter, observability tests
- Finding: request completion logs emitted `request.url.path` as `endpoint`, which can include
  supportability identifiers such as request hashes, correlation ids, idempotency keys, portfolio ids,
  or run ids. The formatter also accepted arbitrary `extra_fields` without redacting sensitive key
  names.
- Action: changed HTTP access logs to emit route templates, bounded `status_family`, and bounded
  `latency_bucket_ms`; added redaction for sensitive extra-field names; added tests proving
  request-hash path values are not logged and sensitive formatter fields are redacted.
- Status: fixed for HTTP access logs and formatter-owned extra fields.
- Wiki decision: wiki operations and supported-features source updated because operator-facing
  logging behavior changed.

## RFC36-S9-002: Stateful core resolver had no bounded metric

- Date: 2026-05-01
- Scope: stateful resolver seam, metrics, observability tests
- Finding: the modeled `lotus-core` resolver seam returned source-safe API errors, but emitted no
  bounded metric for future stateful resolver success, unavailability, invalid response, or
  incomplete context outcomes.
- Action: added `lotus_manage_core_resolver_total` with allowlisted `operation`, `outcome`,
  `supportability_state`, and `reason` labels; instrumented resolver success and failure branches;
  added tests proving untrusted label values are bounded and stateful API paths remain green.
- Status: fixed for the modeled resolver seam.
- Wiki decision: wiki operations and supported-features source updated because operator-facing
  metric behavior changed.

## RFC36-S9-003: Dashboard and alert posture was prose-only

- Date: 2026-05-01
- Scope: monitoring contracts, Make validation, observability governance tests
- Finding: RFC-0036 required dashboard and alert contracts for implemented metrics, but the
  repository had no governed source artifact tying dashboard panels and alert rules to the concrete
  Prometheus metrics implemented by `src.api.observability`.
- Action: added `contracts/observability/lotus-manage-monitoring.v1.json`, a repo-native validator,
  Make integration through `mesh-contract-validate`, and tests proving dashboard and alert
  references use only implemented metrics with bounded, non-sensitive labels.
- Status: fixed for currently implemented custom metrics.
- Wiki decision: wiki operations and supported-features source updated because operator-facing
  monitoring contract behavior changed.

## RFC36-S9-004: Application logs embedded support identifiers in message text

- Date: 2026-05-01
- Scope: service log messages, blocked-run diagnostics, no-sensitive logging tests
- Finding: live Docker evidence showed service-level log messages embedding correlation ids,
  idempotency keys, batch ids, operation ids, and blocked-run diagnostics in free-text messages.
  Route-template access logs were safe, but application messages could still leak sensitive
  supportability identifiers or payload-derived diagnostics.
- Action: changed simulate, batch-analysis, supportability-persistence, blocked-run, scenario-error,
  and async-error log messages to bounded event text without raw identifiers or diagnostics payloads;
  added API tests proving simulate logs do not embed request identifiers and blocked-run warnings do
  not include diagnostics.
- Status: fixed for current service-owned log messages.
- Wiki decision: wiki operations and supported-features source updated because operator-facing
  logging behavior changed.

## RFC36-S9-005: Execution and workflow metrics were incomplete

- Date: 2026-05-01
- Scope: DPM execution APIs, async operation lifecycle, policy-pack resolution, workflow decisions,
  monitoring contracts, observability tests
- Finding: the service had bounded supportability and stateful resolver metrics, but no governed
  metric families for execution outcomes, async lifecycle transitions, policy-pack resolution
  posture, or mandate-workflow decisions. Operators could not distinguish accepted, replayed,
  blocked, partial-failure, policy-disabled, or workflow-action outcomes without inspecting API
  payloads or persistence state.
- Action: added bounded Prometheus counters for execution, async operations, policy-pack
  resolution, and workflow decisions; instrumented simulate, analyze, async submit/execute,
  policy-pack lookup, and workflow action routes; expanded the monitoring contract, dashboards,
  alerts, validator, and tests to keep labels bounded and non-sensitive.
- Status: fixed for current DPM execution and supportability workflow surfaces.
- Wiki decision: wiki operations and supported-features source updated because operator-facing
  monitoring behavior changed.

## RFC36-S2-004: Advisory vocabulary remains in historical rationale and boundary docs

- Date: 2026-05-01
- Scope: `docs/rfcs`, `docs/adr`, `docs/documentation`, `wiki`
- Finding: advisory/proposal terms appear in historical RFCs and explicit ownership-boundary docs.
  Current-state tests already block removed proposal route names, proposal persistence, and proposal
  repository language in active docs.
- Action: retained historical rationale and boundary statements; deferred active vocabulary cleanup
  to RFC-0036 Slice 4.
- Status: deliberately retained until Slice 4 review
- Wiki decision: no wiki source change in Slice 2.
