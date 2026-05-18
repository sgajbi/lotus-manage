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

## RFC36-S10-001: Capabilities endpoint silently ignored unsupported query parameters

- Date: 2026-05-01
- Scope: `GET /api/v1/integration/capabilities`, query-parameter guardrails, downstream
  certification evidence
- Finding: the capabilities endpoint documented canonical source-service query parameters
  `consumer_system` and `tenant_id`, but unsupported camelCase parameters were ignored and caused
  the endpoint to fall back to the default `lotus-gateway/default` posture. That is unsafe for a
  certified control-plane endpoint because a downstream caller can believe tenant or consumer
  context was applied when it was not.
- Action: centralized unsupported-query rejection in `runtime_utils`, reused it for run and
  policy-pack APIs to reduce duplicate helper code, and applied it to the capabilities endpoint.
  Added API tests for camelCase rejection and unknown consumer validation.
- Status: fixed for the capabilities endpoint.
- Wiki decision: wiki endpoint-certification source updated because the certified request contract
  and downstream remediation guidance changed.

## RFC36-S10-002: Supportability summary omitted documented backend-unavailable response

- Date: 2026-05-01
- Scope: `GET /api/v1/rebalance/supportability/summary`, OpenAPI response contract, endpoint
  certification tests
- Finding: the supportability summary endpoint can fail during repository dependency construction
  with a bounded `503` detail such as `DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED`, but the endpoint
  documentation advertised only disabled and unsupported-query error responses.
- Action: added the `503` OpenAPI response description, a direct API regression test for backend
  initialization failure on the summary endpoint, and endpoint-certification wiki evidence.
- Status: fixed for supportability summary certification.
- Wiki decision: wiki endpoint-certification source updated because the certified error contract
  changed.

## RFC36-S10-003: Endpoint certification ledger coverage was not mechanically enforced

- Date: 2026-05-02
- Scope: endpoint certification wiki, OpenAPI route inventory, documentation regression tests
- Finding: Slice 10 relied on manual comparison between OpenAPI routes and endpoint-certification
  wiki entries. The support-bundle variants were described in prose but not listed as explicit
  routes, and `/metrics` was not included in the certified infrastructure endpoint family.
- Action: added a documentation regression test that requires every OpenAPI path to appear in
  `wiki/Endpoint-Certification.md`; added explicit support-bundle variant routes and certified
  `/metrics` as an infrastructure monitoring endpoint with bounded-label requirements.
- Status: fixed for route-level coverage drift.
- Wiki decision: wiki endpoint-certification source updated because endpoint coverage truth
  changed.

## RFC36-S10-004: OpenAPI response examples were incomplete across certified routes

- Date: 2026-05-02
- Scope: OpenAPI enrichment, request/response examples, `/metrics` media type, Swagger contract
  tests
- Finding: many JSON request and response contracts had schemas and descriptions but no concrete
  Swagger examples. `/metrics` was also advertised by the generated schema as JSON even though the
  runtime contract is Prometheus text exposition.
- Action: extended `src/api/openapi_enrichment.py` to derive bounded request and response examples
  from component schemas when route-local examples are absent; documented `/metrics` as
  `text/plain; version=0.0.4`; added contract tests that fail if any JSON request/response content
  lacks examples or if `/metrics` regresses to JSON.
- Status: fixed for current OpenAPI route inventory.
- Wiki decision: wiki endpoint-certification source updated because Swagger certification
  expectations and monitoring endpoint documentation changed.

## RFC36-S10-005: OpenAPI quality gate did not enforce request/response examples

- Date: 2026-05-02
- Scope: `scripts/openapi_quality_gate.py`, Swagger example certification tests
- Finding: after request/response examples were added to the generated OpenAPI schema, the
  repo-native OpenAPI gate still only enforced endpoint summaries, descriptions, tags, response
  families, and schema field metadata. A future route could regress request/response examples and
  still pass the dedicated OpenAPI gate.
- Action: extended `scripts/openapi_quality_gate.py` to fail when JSON request or response content
  lacks `example` or `examples`; added focused unit tests for missing request examples and missing
  response examples.
- Status: fixed for the repo-native OpenAPI quality gate.
- Wiki decision: no wiki source change required; this is a validation hardening of the already
  documented Swagger certification standard.

## RFC36-S11-001: Live manage API proof did not verify deployed OpenAPI certification drift

- Date: 2026-05-02
- Scope: `scripts/validate_live_api.py`, canonical `manage.dev.lotus` API proof, stateful
  core-sourcing guardrails
- Finding: direct canonical-host API validation against `http://manage.dev.lotus` passed the
  existing live probes, but a critical artifact review showed the running service still advertised
  `/metrics` as JSON and missed 46 JSON request/response examples. The live validator was checking
  for advisory/proposal route absence, but not full deployed Swagger certification quality.
- Action: added a live `openapi_certification_contract` probe that fails on missing JSON
  request/response examples or incorrect `/metrics` media type; added a live
  `stateful_core_sourcing_guard` probe proving stateful execution remains disabled until governed
  `lotus-core` resolver proof exists; added unit tests proving stale deployed Swagger is caught.
- Status: fixed in validator and branch code; canonical runtime proof remains blocked until the
  running `lotus-manage` image is refreshed and the live validator returns 0 failures.
- Wiki decision: wiki current-state pages updated to clarify manage/core integration posture and
  live evidence standard.

## RFC36-S11-002: Refreshed manage runtime proved API surface but core stateful route remains absent

- Date: 2026-05-02
- Scope: refreshed canonical-host manage API proof, `lotus-core` DPM execution-context route probe,
  stateful promotion decision
- Finding: after refreshing only `lotus-manage` to the branch image, the strengthened live validator
  passed 10/10 probes against `http://manage.dev.lotus`. Critical review confirmed the deployed
  OpenAPI no longer had missing JSON examples and `/metrics` was Prometheus text. Direct
  `lotus-core` probes for
  `/integration/portfolios/PB_SG_GLOBAL_BAL_001/dpm-execution-context` returned `404` on both
  `core-control.dev.lotus` and `core-query.dev.lotus`, proving stateful core-sourced promotion is
  still blocked by the upstream contract gap.
- Action: recorded the refreshed evidence in RFC-0036 and retained the capability posture where
  `supported_input_modes` is only `["stateless"]` and `dpm.execution.stateful_portfolio_id=false`.
- Status: fixed for implemented stateless/manage API proof; blocked for stateful core-sourced
  execution until `sgajbi/lotus-core#330` or equivalent resolver contract is implemented.
- Wiki decision: wiki current-state pages updated to state the implemented proof posture and the
  remaining core dependency explicitly.

## RFC36-S12-001: Manual manage/core integration proof needed executable coverage

- Date: 2026-05-02
- Scope: `scripts/validate_live_api.py`, `tests/unit/test_validate_live_api.py`, manage/core live
  integration proof
- Finding: Slice 11 recorded direct `lotus-core` DPM execution-context probes manually. That was
  useful evidence, but it left a repeatability gap: future proof runs could validate
  `lotus-manage` API behavior without rechecking whether the expected upstream route posture still
  matched the RFC decision.
- Action: extended the live API validator with optional `--core-base-url` probes and an explicit
  `--expect-core-dpm-route absent|available` posture. Added unit coverage proving the current
  expected absent state passes and that an unexpected available route fails the current blocked
  proof. Ran the enhanced validator against `manage.dev.lotus`, `core-control.dev.lotus`, and
  `core-query.dev.lotus`; it passed 11/11 probes with both core hosts returning `404` and manage
  returning `409 DPM_STATEFUL_INPUT_DISABLED` for stateful simulation.
- Status: fixed for repeatable Slice 12 manage/core posture proof. Stateful promotion remains
  blocked by `sgajbi/lotus-core#330`.
- Wiki decision: wiki integration and supported-feature source updated because live proof commands
  and current manage/core posture evidence changed.

## RFC36-S12-002: Error responses lacked enforced Swagger examples

- Date: 2026-05-02
- Scope: OpenAPI enrichment, OpenAPI quality gate, deployed Swagger certification, live validator
- Finding: Swagger described many `4xx`, `5xx`, and `default` responses, but 73 error responses had
  no JSON content example. The previous local and live OpenAPI gates enforced examples only when
  JSON content was already present, so an endpoint could retain prose-only error documentation and
  still pass certification.
- Action: extended central OpenAPI enrichment to add bounded JSON error examples for every
  `4xx`, `5xx`, and `default` response, including `/metrics` default errors. Tightened
  `scripts/openapi_quality_gate.py` and `scripts/validate_live_api.py` to fail when any error
  response lacks JSON example content. Added focused gate, contract, and live-validator tests.
  Refreshed only `lotus-manage` and reran live proof; the stricter validator passed 12/12 probes
  against `manage.dev.lotus`, `core-control.dev.lotus`, and `core-query.dev.lotus`.
- Status: fixed for current public OpenAPI route inventory and deployed Swagger proof.
- Wiki decision: supported-feature source updated because Swagger certification and live proof
  evidence changed; endpoint certification source already states the error-example standard.

## RFC36-S12-003: Manage/core live proof was not repo-native

- Date: 2026-05-02
- Scope: `Makefile`, README, validation wiki, supported-features wiki, local runtime contract tests
- Finding: The enhanced live validator proved the current manage/core posture, but the command was
  still long and easy to reconstruct incorrectly. That left a final-closure risk where future proof
  could omit either `core-control`, `core-query`, or the explicit expected route posture.
- Action: added `make live-api-validate-core` as the repo-native live proof target. The target
  validates `lotus-manage`, probes both canonical `lotus-core` hosts for the DPM
  execution-context route, and defaults to the current RFC-0036 blocked posture
  `LOTUS_MANAGE_EXPECT_CORE_DPM_ROUTE=absent`. Added documentation and a runtime contract test so
  the command remains discoverable and governed. Ran the target against the local canonical hosts;
  it passed 12/12 probes with both core hosts returning `404`.
- Status: fixed for repeatable current-state manage/core proof. Rerun with
  `LOTUS_MANAGE_EXPECT_CORE_DPM_ROUTE=available` only after the certified core route is live.
- Wiki decision: validation and supported-feature wiki source updated because the repeatable proof
  command changed.

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

## BACKEND-REVIEW-20260519-001: Wave router mixed response contracts with endpoint orchestration

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, rebalance-wave API response DTOs and response mapper
- Finding: `src/api/routers/waves.py` had grown past 3,000 lines and combined endpoint routing,
  request DTOs, response DTOs, source-cohort resolution, workflow orchestration, and HTTP error
  mapping in one module. This made the wave surface harder to review and increased the risk that
  reusable response contracts or supportability serialization would drift from endpoint behavior.
- Action: extracted wave response DTOs and the shared response mapper into
  `src/api/routers/wave_response_contracts.py`. The router now keeps endpoint wiring and request
  parsing while response contract models and supportability response assembly live in a dedicated
  module that can be reused by future wave route splits.
- Status: hardened
- Evidence: `python -m ruff check src\api\routers\waves.py src\api\routers\wave_response_contracts.py`
  during implementation; full validation is recorded in the PR evidence for this slice.
- Follow-up: continue splitting `waves.py` by bounded route families only after the response-contract
  boundary stays green in OpenAPI and wave API tests.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature or operator-contract change.

## BACKEND-REVIEW-20260519-002: Campaign-definition routes repeated HTTP lookup handling

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`,
  `src/api/routers/wave_campaign_definition_http.py`
- Finding: the campaign-definition read, lifecycle projection, launch-history, readiness,
  launch-package, and durable-launch routes repeated the same repository lookup and `404`
  response construction. The duplication kept router behavior correct but made the already-large
  wave router harder to audit and increased the risk of divergent error payloads across bounded
  campaign-definition endpoints.
- Action: extracted the API-level campaign-definition lookup and shared not-found response into
  `src/api/routers/wave_campaign_definition_http.py`, then reused it across campaign-definition
  read and launch routes. The domain-level preview/create validation path remains in `waves.py`
  because it deliberately raises `DpmWaveValidationError` instead of an HTTP exception.
- Status: hardened
- Evidence: `python -m ruff check src\api\routers\waves.py src\api\routers\wave_campaign_definition_http.py tests\unit\dpm\api\test_waves_api.py`;
  `python -m pytest tests\unit\dpm\api\test_waves_api.py -q` (`110 passed`).
- Follow-up: continue route-family extraction only after each bounded helper remains covered by
  focused API tests and OpenAPI gates.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.
