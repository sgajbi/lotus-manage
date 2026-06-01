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

## BACKEND-REVIEW-20260519-003: Wave workflow routes repeated HTTP error mapping

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_http_errors.py`
- Finding: durable wave read and workflow routes repeated identical `DpmWaveLookupError` and
  `DpmWaveValidationError` HTTP response mapping. Some routes had route-specific conflict
  semantics (`WAVE_CREATE_CONFLICT` versus optimistic `DPM_WAVE_VERSION_CONFLICT`), so the repeated
  code was easy to keep mostly correct but harder to audit as the router grew.
- Action: extracted reusable wave lookup and validation HTTP exception builders into
  `src/api/routers/wave_http_errors.py`, including explicit route-level conflict-code selection.
  The endpoint methods now preserve their existing status-code behavior while keeping HTTP mapping
  outside the route orchestration body.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_http_errors.py`; focused wave API
  regression `python -m pytest tests\unit\api\test_wave_http_errors.py tests\unit\dpm\api\test_waves_api.py -q`.
- Follow-up: continue moving bounded route-family plumbing out of `waves.py` only when the helper
  has direct tests and the route family stays green under OpenAPI and wave API regression tests.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-004: Campaign-definition routes repeated lifecycle error mapping

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_campaign_definition_http.py`
- Finding: campaign-definition create, retire, supersede, discovery, and launch routes repeated
  HTTP exception construction for conflict, lifecycle, validation, not-found, launch-blocked, and
  invalid-date cases. The route bodies remained behaviorally correct, but the repeated mappings made
  status-code posture harder to review and increased the chance of future drift across the same
  bounded API family.
- Action: moved campaign-definition HTTP exception builders into
  `src/api/routers/wave_campaign_definition_http.py`, including the explicit supersession lifecycle
  status mapping and launch-readiness payload preservation. The router now delegates error
  translation while keeping endpoint orchestration and request parsing local.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_campaign_definition_http.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: continue shrinking `waves.py` by cohesive route families only after each extracted
  boundary has focused unit tests and route-level regression coverage.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-005: Source-cohort wave routes repeated as-of-date validation

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_date_validation.py`
- Finding: source-cohort wave resolution paths repeated identical ISO `as_of_date` parsing and
  `INVALID_AS_OF_DATE` domain-validation error construction. The repeated code was small, but it sat
  in the same high-risk router area as source-owner cohort calls and campaign membership, making
  future route-family splits easier to drift.
- Action: extracted the shared wave `as_of_date` parser into
  `src/api/routers/wave_date_validation.py` and reused it across PM-book, CIO model-change,
  tactical house-view, risk-event, and bulk-review campaign resolution paths.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_date_validation.py`; full validation
  is recorded in the PR evidence for this slice.
- Follow-up: keep extracting cohesive source-cohort helper boundaries only when behavior-preserving
  tests cover the shared domain error semantics.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-006: Source-cohort routes repeated dependency HTTP mapping

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_source_dependency_http.py`
- Finding: source-owner cohort resolution paths repeated `503` unavailable and `424` dependency
  failure response construction for Core PM-book membership, Core CIO model-change cohorts,
  Advise tactical house-view cohorts, and Risk risk-event cohorts. The behavior was correct, but
  source-specific status-code rules were embedded in route orchestration.
- Action: extracted reusable source-dependency HTTP exception builders into
  `src/api/routers/wave_source_dependency_http.py` and reused them across the source-cohort routes
  while preserving rejected-source `424`, unavailable-source `503`, not-ready, empty, and
  reason-code payload behavior.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_source_dependency_http.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: continue separating source-cohort orchestration from router concerns before adding
  broader campaign workflow surfaces.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-007: Source-cohort routes built lineage refs inline

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_source_refs.py`
- Finding: source-cohort wave resolution paths built PM-book, CIO model-change, tactical
  house-view, risk-event, and bulk-review campaign source-reference dictionaries inline in route
  orchestration. The repeated lineage construction made it harder to review whether source-owner
  product names, fallback identities, supportability state casing, and content hashes stayed
  consistent across source families.
- Action: extracted pure source-reference builders into
  `src/api/routers/wave_source_refs.py` and reused them across the source-cohort route helpers
  without changing API response shape. Focused tests now cover fallback identities, content-hash
  preservation, supportability state propagation, and member-level refs that intentionally omit
  `content_hash`.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_source_refs.py`; full validation is
  recorded in the PR evidence for this slice.
- Follow-up: continue separating source-cohort payload preparation and route orchestration in small
  behavior-preserving slices only when focused tests pin the source-owner boundary.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-008: Source-cohort routes repeated source-ref serialization

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_source_refs.py`
- Finding: source-cohort route helpers repeated `DpmWaveSourceRef` JSON serialization in tactical
  house-view, risk-event, bulk-review campaign, and campaign-governance payload assembly. The
  duplication was mechanically simple but easy to drift from the source-reference helper boundary
  added for lineage dictionary construction.
- Action: added `source_refs_payload()` to `src/api/routers/wave_source_refs.py` and reused it for
  source-ref list serialization across source-cohort payload assembly. Focused tests pin JSON-mode
  serialization and preserve the existing route-level regression coverage.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_source_refs.py`; full validation is
  recorded in the PR evidence for this slice.
- Follow-up: source-cohort payload preparation can continue moving out of `waves.py` once the
  request DTO ownership boundary is split cleanly enough to avoid router-helper cycles.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-009: Campaign membership hashing lived in router orchestration

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_campaign_hashing.py`
- Finding: deterministic hash construction for `BulkReviewCampaignMembership:v1` and
  `BulkReviewCampaignGovernance:v1` lived inside the wave router. The code was pure and correct,
  but keeping canonical payload construction beside route orchestration made campaign lineage
  behavior harder to test directly and forced the router to own low-level JSON/hash mechanics.
- Action: extracted campaign governance and membership hash builders into
  `src/api/routers/wave_campaign_hashing.py` and reused them from the bulk-review campaign
  resolution helpers. Focused tests now pin stable canonical hashing, actor sensitivity, and
  membership-change sensitivity.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_campaign_hashing.py`; full validation
  is recorded in the PR evidence for this slice.
- Follow-up: continue moving pure campaign membership helpers out of `waves.py` only when tests can
  pin lineage, supportability, and failure semantics without broad route coupling.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-010: Source-cohort routes repeated portfolio-type normalization

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_portfolio_type_validation.py`
- Finding: PM-book, tactical house-view, and bulk-review campaign route helpers repeated
  portfolio-type trimming, upper-casing, and required-list validation with route-specific error
  codes. The duplication was small but sat in source-cohort orchestration, where future route
  splits could drift on accepted portfolio-type casing or missing-input semantics.
- Action: extracted `normalize_required_portfolio_types()` into
  `src/api/routers/wave_portfolio_type_validation.py` and reused it across the source-cohort paths
  while preserving each route's existing validation code and message.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_portfolio_type_validation.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: continue moving source-cohort request normalization into focused helpers only where the
  helpers can preserve route-specific validation semantics.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-011: Source-cohort routes repeated required identifier validation

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_required_text_validation.py`
- Finding: PM-book, CIO model-change, and risk-event route helpers repeated the same trim and
  required-value validation for source-cohort identifiers while embedding route-specific error
  codes and messages in the router body. The behavior was correct, but the repeated pattern made
  source-cohort normalization harder to review as route orchestration continued to shrink.
- Action: extracted `normalize_required_text()` into
  `src/api/routers/wave_required_text_validation.py` and reused it for `portfolio_manager_id`,
  `model_portfolio_id`, and `risk_event_id` validation while preserving each route's existing
  validation code and message.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_required_text_validation.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: continue extracting source-cohort request normalization only when route-specific
  validation semantics remain explicit at the call site.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-012: Candidate portfolio-type normalization drift risk

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_portfolio_type_validation.py`
- Finding: tactical house-view and bulk-review campaign route helpers still repeated single
  candidate portfolio-type trimming, upper-casing, and required-value validation even after the
  eligible portfolio-type list normalizer was centralized. The duplicated single-value path could
  drift from list normalization and route-specific error handling as source-cohort routes continue
  to be decomposed.
- Action: added `normalize_required_portfolio_type()` next to the existing required-list helper
  and reused it for tactical house-view and bulk-review campaign candidate validation while keeping
  each route's validation code and message explicit.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_portfolio_type_validation.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: continue consolidating source-cohort candidate validation where shared helpers can
  preserve private-banking semantics and fail-closed route-specific error codes.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-013: Risk-event exposure-weight validation embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_risk_event_validation.py`
- Finding: risk-event source-cohort resolution normalized source-supplied exposure bucket names and
  enforced missing/negative exposure-weight validation inline inside `waves.py`. The behavior was
  correct, but it kept risk-event candidate validation coupled to route orchestration and made the
  source-owned exposure contract harder to test directly.
- Action: extracted `normalize_risk_event_exposure_weights()` into
  `src/api/routers/wave_risk_event_validation.py` and reused it from the risk-event resolver while
  preserving the existing fail-closed validation codes and messages.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_risk_event_validation.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: continue moving pure request-normalization logic out of `waves.py` when the helper can
  retain source-owner boundaries and route-specific failure semantics.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-014: Campaign governance validation embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_campaign_governance_validation.py`
- Finding: bulk-review campaign governance approval completeness, expiry-date posture, and
  actor-entitlement checks were embedded directly in `waves.py`. The behavior was correct, but the
  validation rules are private-banking governance semantics and deserve focused tests separate from
  route orchestration and source-ref assembly.
- Action: extracted `campaign_approval_status()`, `campaign_expiry_state()`, and
  `campaign_actor_entitlement_state()` into
  `src/api/routers/wave_campaign_governance_validation.py`, then reused them from the bulk-review
  campaign governance resolver while preserving existing validation codes and messages.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_campaign_governance_validation.py`;
  full validation is recorded in the PR evidence for this slice.
- Follow-up: keep source-ref and diagnostic assembly near the route request context unless a stable
  campaign-governance domain object emerges.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-015: Bulk-review candidate selection embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_campaign_candidate_selection.py`
- Finding: bulk-review campaign candidate filtering, excluded-candidate counting, portfolio-type
  validation, and required source-ref validation were still embedded directly in `waves.py`. The
  behavior was correct, but the loop is pure source-backed candidate selection logic and made the
  route resolver harder to scan beside membership hashing, governance diagnostics, and source-ref
  assembly.
- Action: extracted `select_bulk_review_campaign_candidates()` into
  `src/api/routers/wave_campaign_candidate_selection.py` and reused it from the campaign resolver
  while preserving existing validation codes, messages, and excluded-candidate diagnostics.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_campaign_candidate_selection.py`;
  full validation is recorded in the PR evidence for this slice.
- Follow-up: keep membership source-ref assembly in the route until a stable campaign-membership
  response projection object is introduced.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-016: Tactical house-view candidate payload assembly embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_tactical_candidate_selection.py`
- Finding: tactical house-view source-backed candidate validation and payload assembly lived inside
  the router resolver beside lotus-advise source-authority calls and response source-ref assembly.
  The behavior was correct, but the candidate payload builder is pure Manage-side source-evidence
  normalization and was harder to test directly while embedded in the route.
- Action: extracted `build_tactical_house_view_candidate_payloads()` into
  `src/api/routers/wave_tactical_candidate_selection.py` and reused it from the tactical
  house-view resolver while preserving existing fail-closed validation codes, messages, source-ref
  payload shape, exposure-weight string conversion, and reason-code semantics.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_tactical_candidate_selection.py`;
  full validation is recorded in the PR evidence for this slice.
- Follow-up: keep lotus-advise authority invocation and affected-portfolio response projection in
  the route until a stable tactical house-view workflow projection object is introduced.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-017: Risk-event candidate payload assembly embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_risk_event_validation.py`
- Finding: risk-event candidate exposure normalization and lotus-risk request payload assembly
  were still embedded in the router resolver. The logic was correct, but it mixed pure
  source-candidate preparation with source-authority invocation and affected-portfolio projection,
  making the risk-event cohort boundary harder to test directly.
- Action: added `build_risk_event_candidate_payloads()` and
  `RiskEventCandidatePayloads` to `src/api/routers/wave_risk_event_validation.py`, then reused the
  helper from the risk-event resolver while preserving exposure-bucket normalization, validation
  codes, duplicate portfolio-id mapping behavior, and request payload shape.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_risk_event_validation.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: keep lotus-risk authority invocation and affected-portfolio response source-ref
  projection in the route until a stable risk-event workflow projection object is introduced.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-018: PM-book membership projection embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_pm_book_projection.py`
- Finding: PM-book source membership projection was embedded in the route resolver after the
  lotus-core call. The projection was correct, but it mixed source-authority failure handling with
  deterministic wave portfolio/source-ref materialization, making PM-book lineage fallback behavior
  harder to test directly.
- Action: extracted `build_pm_book_resolved_portfolios()` into
  `src/api/routers/wave_pm_book_projection.py` and reused it from the PM-book resolver while
  preserving snapshot-id, batch-fingerprint, deterministic book-id, and member source-record
  fallback behavior.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_pm_book_projection.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: keep lotus-core resolver invocation and source dependency error mapping in the route
  until a stable PM-book workflow projection object is introduced.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-019: CIO model-change cohort projection embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_cio_model_change_projection.py`
- Finding: CIO model-change affected-cohort projection was embedded in the route resolver after
  the lotus-core call. The projection was correct, but it mixed upstream source dependency handling
  with deterministic wave portfolio/source-ref materialization, making lineage fallback behavior
  harder to test directly.
- Action: extracted `build_cio_model_change_resolved_portfolios()` into
  `src/api/routers/wave_cio_model_change_projection.py` and reused it from the CIO model-change
  resolver while preserving snapshot-id, batch-fingerprint, model-change-event id, event source-ref,
  and affected-mandate source-record fallback behavior.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_cio_model_change_projection.py`;
  full validation is recorded in the PR evidence for this slice.
- Follow-up: keep lotus-core resolver invocation and source dependency error mapping in the route
  until a stable CIO model-change workflow projection object is introduced.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-020: Risk-event cohort projection embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_risk_event_validation.py`
- Finding: risk-event affected-cohort projection was still embedded in the route resolver after the
  lotus-risk source-authority call. The behavior was correct, but it mixed source dependency error
  handling with deterministic wave portfolio/source-ref materialization, making lineage fallback
  behavior harder to test directly.
- Action: added `build_risk_event_resolved_portfolios()` to
  `src/api/routers/wave_risk_event_validation.py` and reused it from the risk-event resolver while
  preserving cohort-id, request-fingerprint, requested-event fallback, event source-ref,
  affected-portfolio source-ref, candidate source-ref, and supportability-state behavior.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_risk_event_validation.py`; full
  validation is recorded in the PR evidence for this slice.
- Follow-up: keep lotus-risk resolver invocation and source dependency error mapping in the route
  until a stable risk-event workflow projection object is introduced.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260519-021: Tactical house-view cohort projection embedded in router

- Date: 2026-05-19
- Scope: `src/api/routers/waves.py`, `src/api/routers/wave_tactical_candidate_selection.py`
- Finding: tactical house-view affected-cohort projection was still embedded in the route resolver
  after the lotus-advise source-authority call. The behavior was correct, but it mixed source
  dependency error handling with deterministic wave portfolio/source-ref and diagnostics
  materialization, making the tactical house-view lineage contract harder to test directly.
- Action: added `build_tactical_house_view_resolved_portfolios()` to
  `src/api/routers/wave_tactical_candidate_selection.py` and reused it from the tactical
  house-view resolver while preserving cohort, house-view, affected-portfolio, source-owned
  candidate lineage, supportability, and diagnostics behavior.
- Status: hardened
- Evidence: focused helper tests in `tests/unit/api/test_wave_tactical_candidate_selection.py`;
  full validation is recorded in the PR evidence for this slice.
- Follow-up: keep lotus-advise resolver invocation and source dependency error mapping in the route
  until a stable tactical house-view workflow projection object is introduced.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260531-001: Portfolio-memory governance and state mapping lived in service orchestration

- Date: 2026-05-31
- Scope: `src/core/portfolio_memory/service.py`, portfolio-memory governance posture, unsupported
  external execution/client-communication boundary evidence, supportability-state mapping
- Finding: portfolio-memory read-model orchestration mixed repository fan-out and event projection
  with static governance policy, source-event family posture, unsupported-boundary evidence, and
  state-mapping helpers. The behavior was correct, but the service file had grown past 2,200 lines
  and made portfolio-memory source boundaries harder to review independently from aggregation
  orchestration.
- Action: extracted governance and boundary evidence into
  `src/core/portfolio_memory/governance.py`, extracted supportability-state mapping into
  `src/core/portfolio_memory/supportability.py`, preserved existing service helper aliases for
  compatibility with focused tests, and added direct unit coverage for no-raw-payload governance,
  unsupported external execution/client-communication claims, supported/deferred source-event
  family posture, and fail-closed state mapping.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_governance_supportability.py`;
  existing portfolio-memory API tests remain the behavior-preserving regression scope for the
  service facade.
- Follow-up: continue decomposing `portfolio_memory/service.py` by source-event family only when
  each extraction can preserve lineage, content-hash, and no-unsupported-claim behavior with
  focused tests.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260531-002: Portfolio-memory source-reference projection lived in service orchestration

- Date: 2026-05-31
- Scope: `src/core/portfolio_memory/service.py`, proof-pack, wave, campaign, outcome-review, and
  mandate source-reference projection helpers
- Finding: portfolio-memory source-reference projection helpers were embedded in the read-model
  service next to repository fan-out and event aggregation. These mappers preserve source-owned
  identity, supportability state, content hashes, and fallback identity behavior, so keeping them
  inside service orchestration made lineage behavior harder to test directly and contributed to
  monolithic service growth.
- Action: extracted the pure source-reference projection helpers into
  `src/core/portfolio_memory/source_refs.py`, kept service-level aliases for behavior-preserving
  compatibility, and added direct tests for proof-pack, wave, outcome, mandate lineage, fallback
  source identity, and proof-pack source-ref dedupe/sort behavior.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_source_refs.py`; existing
  portfolio-memory, proof-pack, and wave API tests remain the downstream regression scope for
  event projection behavior.
- Follow-up: continue decomposing event-family builders only when source lineage, artifact refs,
  and content-hash semantics can be pinned independently.
- Wiki decision: no wiki source change required; this is an internal modularity refactor with no
  supported-feature, API shape, or operator-contract change.

## BACKEND-REVIEW-20260531-003: Portfolio-memory API tests depended on private service helper aliases

- Date: 2026-05-31
- Scope: `tests/unit/dpm/api/test_portfolio_memory_api.py`, portfolio-memory source-ref and
  supportability helper assertions
- Finding: helper-edge coverage in the API test suite asserted source-ref and supportability
  behavior through private `portfolio_memory.service` aliases. After extracting these helpers into
  focused modules, leaving the tests coupled to the service facade would obscure module ownership
  and make future service decomposition harder.
- Action: updated helper-edge assertions to import source-reference projection from
  `src/core/portfolio_memory/source_refs.py` and supportability mapping from
  `src/core/portfolio_memory/supportability.py`, while leaving the remaining
  service-orchestration helper assertion in the service namespace.
- Status: hardened
- Evidence: focused portfolio-memory API tests plus the new module-level source-ref and
  supportability tests.
- Follow-up: extract the remaining PM-book membership inclusion helper only if a stable PM-quality
  portfolio-memory projection module emerges.
- Wiki decision: no wiki source change required; this is test ownership cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-004: Portfolio-memory search and facet helpers lived in service orchestration

- Date: 2026-05-31
- Scope: `src/core/portfolio_memory/service.py`, search filter normalization, event matching,
  source-system/source-type facet extraction, deterministic counts, and event dedupe/sort helpers
- Finding: portfolio-memory search orchestration mixed repository scanning and page construction
  with pure helper behavior for filter normalization, event source facets, matching, counts, and
  event ordering. These helpers are part of the search contract and should be testable without
  constructing repository fixtures or invoking the full read-model service.
- Action: extracted the pure search/facet helpers into
  `src/core/portfolio_memory/search_filters.py`, kept service-level aliases for behavior-preserving
  orchestration, and added direct tests for blank-filter normalization, source/artifact facet
  inclusion, filter matching, count aggregation, and deterministic dedupe/sort behavior.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_search_filters.py`; existing
  portfolio-memory API search tests remain the endpoint/read-model regression scope.
- Follow-up: keep candidate repository scanning inside service orchestration until a stable
  search-index service boundary emerges.
- Wiki decision: no wiki source change required; this is internal modularity/testability cleanup
  with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-005: PM-quality portfolio membership projection lived in portfolio-memory service

- Date: 2026-05-31
- Scope: PM operating-quality score-run membership projection inside
  `src/core/portfolio_memory/service.py`
- Finding: the service embedded the rule that links a PM operating-quality score run to a portfolio
  through Core PM-book evidence. That rule is private-banking domain projection logic, not
  repository orchestration, and it is reused by score-run, review-action, and summary-invocation
  event projection.
- Action: extracted the rule into `src/core/portfolio_memory/pm_quality_projection.py`, updated the
  service to consume the focused helper, updated API helper-edge tests to assert against the new
  module boundary, and added direct unit coverage for member portfolio ids, PM-book member source
  refs, and missing book-scope evidence.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_pm_quality_projection.py` plus
  existing portfolio-memory API tests.
- Follow-up: keep PM-quality event builders in the service until a coherent source-event-family
  projection module can be extracted without weakening content-hash or no-unsupported-claim
  evidence.
- Wiki decision: no wiki source change required; this is internal domain projection cleanup with no
  API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-006: Construction memory event projection lived in portfolio-memory service

- Date: 2026-05-31
- Scope: construction alternative set and selected-alternative portfolio-memory event projection
- Finding: construction event projection was embedded in `src/core/portfolio_memory/service.py`
  beside repository scanning. The event builders own source-safe projection details such as request
  hash reuse, method counts, selected-method metadata, artifact refs, and explicit no-raw-payload
  flags, so they are a domain projection boundary rather than service orchestration.
- Action: extracted construction alternative set, construction selection, and alternative-set
  content-hash projection into `src/core/portfolio_memory/construction_projection.py`, leaving
  repository retrieval in the service. Added direct unit coverage for request-hash preservation,
  method counts, selected-alternative metadata, artifact refs, fallback content hashing, and
  no-raw-payload projection flags.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_construction_projection.py`
  plus existing portfolio-memory API tests.
- Follow-up: continue extracting source-event-family projection modules only where repository
  scanning can remain separated from pure event construction.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-007: Proof-pack memory event projection lived in portfolio-memory service

- Date: 2026-05-31
- Scope: proof-pack created and decision-timeline portfolio-memory event projection
- Finding: proof-pack event projection was embedded in `src/core/portfolio_memory/service.py`
  beside repository scanning. The event builders own source-safe projection details such as
  source refs, report/AI artifact refs, content hashes, status mapping, and bounded metadata, so
  they are a source-event-family projection boundary rather than service orchestration.
- Action: extracted proof-pack created and decision-timeline event projection into
  `src/core/portfolio_memory/proof_pack_projection.py`, leaving proof-pack repository retrieval in
  the service. Added direct unit coverage for created-event source/artifact references and
  timeline-event evidence artifact projection.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_proof_pack_projection.py` plus
  existing portfolio-memory API tests.
- Follow-up: continue extracting source-event-family projection modules only when source lineage
  and artifact-ref semantics can be covered independently.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-008: Wave memory event projection lived in portfolio-memory service

- Date: 2026-05-31
- Scope: wave created, state-transition, and internal handoff portfolio-memory event projection
- Finding: wave event projection was embedded in `src/core/portfolio_memory/service.py` beside
  wave repository discovery. The event builders own handoff-boundary semantics, source refs,
  transition metadata, and no-external-execution evidence, so they are a source-event-family
  projection boundary rather than service orchestration.
- Action: extracted wave created, state-transition, handoff, and event-metadata projection into
  `src/core/portfolio_memory/wave_projection.py`, leaving wave selection in the service. Added
  direct unit coverage for matching item context, source refs, transition metadata, handoff
  artifact refs, and unrelated handoff filtering.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_wave_projection.py` plus
  existing portfolio-memory API tests.
- Follow-up: keep campaign workflow projection in the service until it can be split without
  weakening campaign-version identity or maker-checker boundary evidence.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-009: Outcome-review memory event projection lived in portfolio-memory service

- Date: 2026-05-31
- Scope: post-trade outcome-review created and append-only event projection
- Finding: outcome-review event projection was embedded in `src/core/portfolio_memory/service.py`
  beside repository scanning. The event builders own source lineage mapping, persisted-event
  dedupe semantics, content-hash preservation, and handoff-reference metadata, so they are a
  source-event-family projection boundary rather than service orchestration.
- Action: extracted outcome-review created and append-only event projection into
  `src/core/portfolio_memory/outcome_projection.py`, leaving outcome-review repository traversal
  in the service. Added direct unit coverage for review lineage/handoff metadata and duplicate
  persisted-event precedence.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_outcome_projection.py` plus
  existing portfolio-memory API tests.
- Follow-up: keep PM-quality event projection as the next likely extraction once the score-run,
  review-action, and summary-invocation boundaries can be pinned without weakening no-raw-score
  and no-summary-text evidence.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-010: PM-quality memory event projection lived in portfolio-memory service

- Date: 2026-05-31
- Scope: PM operating-quality score-run, review-action, and summary-invocation memory events
- Finding: PM-quality event builders were embedded in `src/core/portfolio_memory/service.py`
  beside repository filtering. The builders own private-banking PM-quality boundary semantics,
  including no numeric score projection, no raw review reason projection, no summary text
  projection, source refs, and artifact refs, so they are a domain projection boundary rather
  than service orchestration.
- Action: moved score-run, review-action, and summary-invocation event builders into
  `src/core/portfolio_memory/pm_quality_projection.py`, leaving repository filtering and
  portfolio membership selection in the service. Added direct tests for no-raw-score,
  no-review-reason, and no-summary-text projection boundaries.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_pm_quality_projection.py`
  plus existing portfolio-memory API tests.
- Follow-up: review campaign workflow projection separately because campaign definition,
  assignment, transition, and maker-checker evidence is a larger source-event-family boundary.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-011: Campaign workflow memory event projection lived in portfolio-memory service

- Date: 2026-05-31
- Scope: bulk-review campaign definition, approval decision, assignment action, assignment task,
  task transition, and maker-checker control memory events
- Finding: campaign workflow event builders were embedded in
  `src/core/portfolio_memory/service.py` beside repository filtering. The builders own
  campaign-version identity, candidate source lineage, no-global-discovery flags, assignment SLA
  state, task-transition boundary flags, and maker-checker no-external-approval/no-execution
  evidence, so they are a domain projection boundary rather than service orchestration.
- Action: moved campaign workflow event builders into
  `src/core/portfolio_memory/campaign_projection.py`, leaving repository filtering in the
  service. Added direct tests for source-lineage/no-global-discovery, assignment transition
  boundary flags, and maker-checker no-external-approval/no-execution evidence.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_campaign_projection.py` plus
  existing portfolio-memory API tests.
- Follow-up: revisit the remaining mandate-health projection after campaign extraction because it
  is now the largest domain-event builder still resident in the service.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-012: Mandate memory event projection lived in portfolio-memory service

- Date: 2026-05-31
- Scope: mandate health snapshot and monitoring exception memory events
- Finding: mandate event builders were embedded in `src/core/portfolio_memory/service.py` beside
  mandate repository lookup. The builders own source-lineage projection, canonical content hashing,
  supportability state mapping, evidence refs, and monitoring threshold metadata, so they are a
  domain projection boundary rather than service orchestration.
- Action: moved mandate health and monitoring exception event builders into
  `src/core/portfolio_memory/mandate_projection.py`, leaving repository retrieval in the service.
  Added direct tests for source lineage, content hash preservation, supportability mapping,
  monitoring-run artifact refs, and measured/threshold metadata.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_mandate_projection.py` plus
  existing portfolio-memory API tests.
- Follow-up: review remaining service responsibilities for candidate scanning and repository
  orchestration now that all major event-family projection builders have dedicated modules.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-013: Portfolio-memory candidate discovery lived in service search orchestration

- Date: 2026-05-31
- Scope: candidate portfolio discovery for portfolio-memory search
- Finding: portfolio-memory search kept cross-repository candidate discovery inside
  `src/core/portfolio_memory/service.py`, mixing search page orchestration with reusable source
  universe assembly. This made it harder to test explicit portfolio id normalization, optional
  source repositories, and PM-book member evidence without invoking full search pagination.
- Action: extracted candidate discovery to `src/core/portfolio_memory/candidate_portfolios.py` and
  kept search result assembly in the service. Added direct tests for explicit id trimming,
  source-backed portfolio merging, PM-quality book-scope membership, and optional repository
  support.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_candidate_portfolios.py` plus
  existing portfolio-memory API search tests.
- Follow-up: continue keeping repository scans narrow; introduce batching/indexing only with
  repository-native evidence if search volume or latency requires it.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no API,
  supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-014: Portfolio-memory content-hash envelope rules lived in service orchestration

- Date: 2026-05-31
- Scope: deterministic content-hash finalization for memory, search pages, and event lookups
- Finding: `src/core/portfolio_memory/service.py` repeated replay-stable content-hash envelope
  construction for the memory aggregate, search page, and event lookup surfaces. Those rules are
  audit and lineage contract behavior, not repository orchestration, and should be testable without
  building full repository-backed memory pages.
- Action: extracted deterministic envelope finalization to
  `src/core/portfolio_memory/envelopes.py` and updated the service to delegate memory, search page,
  and event lookup content-hash finalization. Added direct tests proving `generated_at` and existing
  `content_hash` are excluded while model validation is still applied.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_envelopes.py` plus existing
  portfolio-memory API hash-determinism tests.
- Follow-up: keep remaining service orchestration focused on repository traversal and page
  composition; avoid reintroducing ad hoc content-hash construction in endpoint code.
- Wiki decision: no wiki source change required; this is internal hash-governance cleanup with no
  API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-015: Portfolio-memory search page assembly lived in service orchestration

- Date: 2026-05-31
- Scope: portfolio-memory search row matching, facet counts, pagination, and support-boundary page
  payload assembly
- Finding: `src/core/portfolio_memory/service.py` still mixed repository traversal with search row
  matching, latest matching event metadata, matching-event facet counts, pagination, and search
  support-boundary construction. Those are search-page projection rules and should be tested
  directly without repository-backed memory construction.
- Action: extracted search row and page assembly to `src/core/portfolio_memory/search_page.py`,
  leaving candidate discovery and memory construction in the service. Added direct tests for latest
  matching event metadata, explicit empty-portfolio handling, facet counts, deterministic ordering,
  and pagination.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_search_page.py` plus existing
  portfolio-memory API search tests.
- Follow-up: review whether remaining service orchestration should be split into a lightweight
  assembler class only if repository dependency flow becomes harder to reason about.
- Wiki decision: no wiki source change required; this is internal search-page modularity cleanup
  with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-016: Portfolio-memory aggregate assembly lived in service orchestration

- Date: 2026-05-31
- Scope: portfolio-memory aggregate event bounding, supportability state, event-type counts,
  source-system facets, governance posture, and final memory envelope assembly
- Finding: `src/core/portfolio_memory/service.py` still mixed repository fan-out with pure
  read-model aggregate rules after event projection. Dedupe/sort/limit behavior, aggregate
  supportability, source-system facets, governance evidence, and final memory hash construction are
  memory-envelope rules and should be directly testable without source repositories.
- Action: extracted aggregate assembly to `src/core/portfolio_memory/aggregate.py`, leaving the
  service to collect source events and delegate deterministic memory construction. Added direct
  aggregate tests for dedupe/sort/limit behavior, source facet projection, governance/boundary
  evidence, and explicit empty-memory state.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_aggregate.py` plus existing
  portfolio-memory API tests.
- Follow-up: continue reviewing repository event collection helpers only where a source-family
  collector can be split without weakening projection tests or introducing circular dependencies.
- Wiki decision: no wiki source change required; this is internal aggregate modularity cleanup with
  no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-017: Portfolio-memory event lookup assembly lived in service orchestration

- Date: 2026-05-31
- Scope: exact portfolio-memory event lookup envelope assembly
- Finding: `src/core/portfolio_memory/service.py` still owned exact event selection and replay-stable
  lookup envelope construction even though it no longer needed repository access. That kept
  audit/read-model lookup behavior coupled to memory/search orchestration and made the exact-event
  surface depend on service internals in API code and tests.
- Action: extracted exact event lookup assembly to `src/core/portfolio_memory/event_lookup.py`,
  updated the portfolio-memory API route and tests to import the dedicated lookup module, and added
  direct lookup tests for exact-event envelope projection and missing-event behavior.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_event_lookup.py` plus existing
  portfolio-memory API lookup tests.
- Follow-up: keep exact-event lookup behavior in the lookup module; future route work should only
  handle HTTP status mapping and repository dependency wiring.
- Wiki decision: no wiki source change required; this is internal lookup modularity cleanup with no
  API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-018: PM-quality memory collection repeated score-run scans

- Date: 2026-05-31
- Scope: PM operating-quality score-run, review-action, and summary-invocation repository collection
  for portfolio-memory events
- Finding: `src/core/portfolio_memory/service.py` collected PM-quality score-run, review-action,
  and summary-invocation memory events through three separate helpers, each scanning
  `list_score_runs(limit=...)` to rebuild the same PM-book scoped score-run map. That duplicated
  repository work on the portfolio-memory hot path and kept PM-quality collection flow embedded in
  the service.
- Action: extracted PM-quality collection to `src/core/portfolio_memory/pm_quality_collection.py`.
  The collector materializes the portfolio-scoped score-run map once, reuses it for downstream
  review-action and summary-invocation projection, and avoids downstream scans when no score run is
  in scope for the portfolio.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_pm_quality_collection.py` prove
  one score-run scan feeds all PM-quality memory events and that downstream scans are skipped when
  the portfolio is out of PM-book scope; existing portfolio-memory API tests remain the endpoint
  regression scope.
- Follow-up: review remaining repository event collection helpers for similar repeated scans before
  introducing broader collector abstractions.
- Wiki decision: no wiki source change required; this is internal memory-collection performance and
  modularity cleanup with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-019: Mandate memory collection lived in service orchestration

- Date: 2026-05-31
- Scope: mandate-health and mandate-monitoring repository collection for portfolio-memory events
- Finding: `src/core/portfolio_memory/service.py` still owned mandate twin lookup, latest health
  snapshot lookup, monitoring exception paging, and mandate memory event projection. That coupled
  mandate repository flow to the top-level memory service and left an important edge case
  under-characterized: portfolio-level monitoring exceptions should still project when no latest
  mandate twin is available.
- Action: extracted mandate collection to `src/core/portfolio_memory/mandate_collection.py` and
  updated the service to delegate mandate event collection. Added focused tests proving latest
  health plus monitoring exception projection and preserving portfolio-level exception projection
  when the mandate twin is absent.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_mandate_collection.py` plus
  existing portfolio-memory API tests.
- Follow-up: continue extracting remaining repository-family collectors only where the module can
  own a clear source-family dependency flow and direct tests.
- Wiki decision: no wiki source change required; this is internal memory-collection modularity
  cleanup with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-020: Construction memory collection lived in service orchestration

- Date: 2026-05-31
- Scope: construction alternative-set and selection repository collection for portfolio-memory
  events
- Finding: `src/core/portfolio_memory/service.py` still owned construction alternative-set listing,
  selection lookup, and construction memory event projection. That kept construction repository flow
  in the top-level memory service rather than in a source-family collector with direct tests for
  alternative-set-only and selected-alternative cases.
- Action: extracted construction collection to
  `src/core/portfolio_memory/construction_collection.py` and updated the service to delegate
  construction event collection. Added focused tests proving alternative-set plus selection
  projection and preserving alternative-set projection when no selection exists.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_construction_collection.py` plus
  existing portfolio-memory API tests.
- Follow-up: continue extracting remaining campaign and wave repository-family collectors with
  source-family tests before considering a broader service orchestration abstraction.
- Wiki decision: no wiki source change required; this is internal memory-collection modularity
  cleanup with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-021: Campaign memory collection lived in service orchestration

- Date: 2026-05-31
- Scope: bulk-review campaign definition repository collection for portfolio-memory events
- Finding: `src/core/portfolio_memory/service.py` still owned campaign definition listing,
  candidate membership filtering, and campaign memory event projection. That kept campaign workflow
  source-family collection in the top-level memory service instead of beside campaign projection,
  and left the non-matching candidate filter without direct source-family tests.
- Action: extracted campaign collection to `src/core/portfolio_memory/campaign_collection.py` and
  updated the service to delegate campaign workflow memory collection. Added focused tests proving
  matching campaign workflow event projection and skipping definitions whose candidates do not
  contain the requested portfolio.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_campaign_collection.py` plus
  existing portfolio-memory API tests.
- Follow-up: extract the remaining wave repository-family collector, then review whether
  `service.py` should keep direct proof-pack/outcome repository traversal or move to explicit
  source collectors.
- Wiki decision: no wiki source change required; this is internal memory-collection modularity
  cleanup with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-022: Wave memory collection lived in service orchestration

- Date: 2026-05-31
- Scope: rebalance-wave repository collection for portfolio-memory events
- Finding: `src/core/portfolio_memory/service.py` still owned wave listing, portfolio-item
  membership filtering, and wave memory event projection. That kept the rebalance-wave source-family
  dependency flow in the top-level memory service and left the non-matching portfolio filter without
  direct source-family tests.
- Action: extracted wave collection to `src/core/portfolio_memory/wave_collection.py` and updated
  the service to delegate wave memory event collection. Added focused tests proving matching wave
  event projection and skipping waves whose items do not include the requested portfolio.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_wave_collection.py` plus existing
  portfolio-memory API tests.
- Follow-up: review remaining direct proof-pack and outcome-review traversal in `service.py` for the
  same source-family collector pattern before introducing any broader orchestration abstraction.
- Wiki decision: no wiki source change required; this is internal memory-collection modularity
  cleanup with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-023: Proof-pack memory collection lived in service orchestration

- Date: 2026-05-31
- Scope: proof-pack repository collection for portfolio-memory events
- Finding: `src/core/portfolio_memory/service.py` still owned proof-pack listing and proof-pack
  memory event fan-out. That kept proof-pack source-family collection in the top-level memory
  service instead of beside proof-pack projection, and left portfolio filtering plus timeline
  fan-out without direct source-family collector tests.
- Action: extracted proof-pack collection to `src/core/portfolio_memory/proof_pack_collection.py`
  and updated the service to delegate proof-pack memory event collection. Added focused tests
  proving portfolio-filtered proof-pack collection and fan-out to created plus all decision-timeline
  memory events.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_proof_pack_collection.py` plus
  existing portfolio-memory API tests.
- Follow-up: review remaining direct outcome-review traversal in `service.py` for the same
  source-family collector pattern before introducing any broader orchestration abstraction.
- Wiki decision: no wiki source change required; this is internal memory-collection modularity
  cleanup with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-024: Outcome-review memory collection lived in service orchestration

- Date: 2026-05-31
- Scope: post-trade outcome-review repository collection for portfolio-memory events
- Finding: `src/core/portfolio_memory/service.py` still owned outcome-review listing, append-only
  persisted event lookup, and outcome memory event fan-out. That kept the outcome-review
  source-family dependency flow in the top-level memory service and left repository-level persisted
  event fan-out without direct source-family collector tests.
- Action: extracted outcome-review collection to
  `src/core/portfolio_memory/outcome_collection.py` and updated the service to delegate
  outcome-review memory event collection. Added focused tests proving portfolio-filtered collection
  and projection of both review-created and persisted append-only outcome events.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_outcome_collection.py` plus
  existing portfolio-memory API tests.
- Follow-up: with source-family collectors extracted, review whether `service.py` should introduce a
  lightweight repository-bundle orchestration object only if dependency passing becomes harder to
  reason about.
- Wiki decision: no wiki source change required; this is internal memory-collection modularity
  cleanup with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-025: Portfolio-memory source collection orchestration lived in service

- Date: 2026-05-31
- Scope: source-family event collection orchestration for portfolio-memory aggregates
- Finding: `src/core/portfolio_memory/service.py` still coordinated every source-family collector
  directly after the individual source-family collectors had been extracted. That kept repository
  bundle wiring and collection ordering mixed with memory aggregate assembly and made
  required-versus-optional source-family behavior harder to test without building full memory
  aggregates.
- Action: extracted source-family collection orchestration to
  `src/core/portfolio_memory/source_collection.py` with a typed
  `PortfolioMemorySourceRepositories` bundle. Updated the service to delegate event collection
  while keeping the public API stable. Added focused tests proving required source-family
  collection, optional source-family inclusion, and optional empty-repository behavior.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_source_collection.py` plus
  existing portfolio-memory API tests.
- Follow-up: review whether `search_portfolio_memory` should receive the same repository bundle
  helper if parameter passing becomes harder to reason about; avoid broader abstraction until it
  removes real duplication.
- Wiki decision: no wiki source change required; this is internal orchestration modularity cleanup
  with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-026: Portfolio-memory source repositories were duplicated across search paths

- Date: 2026-05-31
- Scope: portfolio-memory source repository dependency flow for aggregate build and search
- Finding: portfolio-memory candidate discovery, source event collection, and search aggregation
  carried the same source repository family as separate parameter lists. That preserved public
  compatibility but kept repeated wiring in the search path and made it easier for candidate
  discovery and event collection to drift when new source families are added.
- Action: moved `PortfolioMemorySourceRepositories` into a dedicated
  `src/core/portfolio_memory/source_repositories.py` dependency module, added a bundle-based
  candidate discovery entrypoint, and updated search to reuse one source repository bundle for
  candidate discovery and per-portfolio memory assembly while keeping existing public service and
  candidate-discovery signatures stable.
- Status: hardened
- Evidence: focused candidate-discovery and source-collection tests plus existing portfolio-memory
  API tests.
- Follow-up: keep future source-family additions on the shared source repository bundle first,
  then adapt public compatibility facades only where existing callers require them.
- Wiki decision: no wiki source change required; this is internal dependency-flow modularity cleanup
  with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-027: Portfolio-memory search request normalization lived in service

- Date: 2026-05-31
- Scope: portfolio-memory search filter normalization and explicit candidate-id shaping
- Finding: `src/core/portfolio_memory/service.py` still normalized search text filters, cast
  supportability-state filters, and built the explicit candidate-id set inline. That kept request
  validation and query shaping mixed with repository orchestration, making search behavior harder to
  test without walking the full source repository scan path.
- Action: extracted search query normalization to
  `src/core/portfolio_memory/search_request.py` with a typed `PortfolioMemorySearchQuery`. Updated
  the service to consume the normalized query object while preserving the public search API and
  existing response semantics. Added focused tests for trimmed filters, blank-filter handling, and
  explicit candidate-id normalization.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_search_request.py` plus existing
  portfolio-memory API tests.
- Follow-up: keep new portfolio-memory search parameters normalized in the search-request module
  before they reach repository orchestration or page assembly.
- Wiki decision: no wiki source change required; this is internal search-query modularity cleanup
  with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-028: Portfolio-memory search pagination relied on API-only bounds

- Date: 2026-05-31
- Scope: portfolio-memory search pagination and source scan bounds
- Finding: the portfolio-memory API route constrained `limit`, `offset`, and `source_scan_limit`,
  but the core search service accepted those values directly. Internal callers could therefore
  bypass API query validation and pass negative offsets, zero limits, or unbounded source scan
  limits into repository orchestration and page assembly.
- Action: extended `src/core/portfolio_memory/search_request.py` so normalized search queries also
  validate and carry pagination bounds. Updated the service to use the normalized query limits for
  candidate discovery, per-portfolio memory assembly, and search page construction. Added focused
  tests that prove valid bounds are preserved and unsafe direct-call pagination is rejected before
  repository scans run.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_search_request.py` plus existing
  portfolio-memory API tests.
- Follow-up: keep API and core service pagination bounds synchronized when new portfolio-memory
  search limits or continuation semantics are introduced.
- Wiki decision: no wiki source change required; this is internal defensive validation hardening
  with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-029: Portfolio-memory search bounds were duplicated between API and core

- Date: 2026-05-31
- Scope: portfolio-memory search pagination contract constants
- Finding: after direct-call pagination validation was added, the API route still carried hard-coded
  `limit`, `offset`, and `source_scan_limit` defaults and bounds that duplicated the core search
  request validation. That created a future drift risk where Swagger/OpenAPI could advertise one
  search contract while internal service validation enforced another.
- Action: promoted the search defaults and bounds to named constants in
  `src/core/portfolio_memory/search_request.py`, updated the FastAPI route and service defaults to
  consume those constants, and added tests proving both the named constants and OpenAPI parameter
  constraints remain synchronized with the core search query contract.
- Status: hardened
- Evidence: focused search-request tests plus the existing portfolio-memory API/OpenAPI tests.
- Follow-up: if portfolio-memory search adds cursor-based continuation or changes maximum scan
  posture, update the shared constants first and let API/service callers consume them.
- Wiki decision: no wiki source change required; this is internal API/core contract synchronization
  with no product-facing capability change.

## BACKEND-REVIEW-20260531-030: Portfolio-memory source repository factory lived in service facade

- Date: 2026-05-31
- Scope: portfolio-memory source repository bundle construction
- Finding: `src/core/portfolio_memory/service.py` still owned the helper that converted public
  service repository parameters into `PortfolioMemorySourceRepositories`. That kept dependency
  bundle construction in the facade instead of the dedicated source-repository boundary module,
  even after search and collection code had moved to bundle-based orchestration.
- Action: moved source repository bundle construction to
  `src/core/portfolio_memory/source_repositories.py` as
  `build_portfolio_memory_source_repositories`, updated the service facade to delegate to it, and
  added focused tests proving required and optional repositories are preserved exactly.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_source_repositories.py` plus
  existing portfolio-memory API tests.
- Follow-up: keep new source-family repository dependencies on the bundle and factory module first;
  public service signatures should remain compatibility facades only.
- Wiki decision: no wiki source change required; this is internal dependency-flow modularity cleanup
  with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-031: Candidate portfolio helper bypassed source repository factory

- Date: 2026-05-31
- Scope: portfolio-memory candidate discovery dependency construction
- Finding: the legacy `candidate_portfolio_ids` helper still constructed
  `PortfolioMemorySourceRepositories` directly and required callers to pass explicit `None` values
  for optional source families. That left a second dependency-bundle construction path after the
  factory moved to the source-repository boundary module.
- Action: updated candidate discovery to use `build_portfolio_memory_source_repositories`, gave the
  optional source repositories default `None` values, and added a focused test proving required-only
  direct calls resolve to the same candidate set.
- Status: hardened
- Evidence: focused candidate-discovery tests in
  `tests/unit/dpm/portfolio_memory/test_candidate_portfolios.py` plus the portfolio-memory API test
  lane.
- Follow-up: keep direct helper compatibility paths thin; new source-family dependencies should be
  introduced through the source-repository factory first.
- Wiki decision: no wiki source change required; this is internal dependency-construction cleanup
  with no API, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-032: Portfolio-memory API repeated source repository dependency blocks

- Date: 2026-05-31
- Scope: portfolio-memory API dependency wiring and source-bundle service entry point
- Finding: the detail, event lookup, and search endpoints each carried the same repository
  dependency list and then passed individual repositories into service facades. That duplicated
  API wiring across routes and made every new source-family repository a multi-endpoint route edit.
- Action: added a shared FastAPI dependency that resolves
  `PortfolioMemorySourceRepositories`, added `search_portfolio_memory_from_sources` for bundle-based
  search orchestration, and updated all portfolio-memory API routes to consume the explicit source
  bundle.
- Status: hardened
- Evidence: focused service test in `tests/unit/dpm/portfolio_memory/test_service.py` plus existing
  portfolio-memory API tests that cover detail, event lookup, search, OpenAPI, and error behavior.
- Follow-up: route-level source-family additions should update only the shared API dependency and
  the source repository factory unless the public query contract changes.
- Wiki decision: no wiki source change required; this is internal API wiring modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-033: Portfolio-memory detail reads relied on route-local scan limits

- Date: 2026-05-31
- Scope: portfolio-memory detail and exact-event read limits
- Finding: portfolio-memory search pagination had shared core/API constants, but detail timelines
  and exact-event lookup still carried route-local `limit` bounds while the core assembler accepted
  unsafe direct-call limits. That created a drift risk between Swagger, service callers, and the
  bounded source scan posture expected for demo and audit workflows.
- Action: added shared portfolio-memory read-limit constants and core validation, wired the API
  detail and event-lookup routes to those constants, added focused tests for direct-call rejection
  and OpenAPI synchronization, and documented the bounded portfolio-memory API flow in the wiki.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_read_request.py`,
  `tests/unit/dpm/portfolio_memory/test_service.py`,
  `tests/unit/dpm/api/test_portfolio_memory_api.py`, and
  `tests/unit/test_documentation_current_state.py`.
- Follow-up: keep future portfolio-memory read or drilldown continuation semantics in the shared
  request-limit module before changing route-level OpenAPI bounds.
- Wiki decision: updated `wiki/API-Surface.md` because the API bounds and implementation-backed
  portfolio-memory flow are operator- and demo-facing product truth.

## BACKEND-REVIEW-20260531-034: Report-safe portfolio-memory context bypassed source bundles

- Date: 2026-05-31
- Scope: portfolio-memory report/AI/archive handoff context assembly
- Finding: `src/api/services/portfolio_memory_context_service.py` still built report-safe memory
  context through the individual-repository service facade even after API and core search paths
  moved to explicit `PortfolioMemorySourceRepositories` bundles. That left one handoff path outside
  the source-bundle dependency boundary used by timeline, search, and event lookup.
- Action: added `build_report_portfolio_memory_context_from_sources`, updated the legacy facade to
  build a source bundle first, and added a focused equivalence test proving the source-bundle entry
  point preserves the report-safe context envelope.
- Status: hardened
- Evidence: focused test in `tests/unit/api/test_portfolio_memory_context_service.py` plus existing
  portfolio-memory handoff and API tests.
- Follow-up: future report/AI/archive portfolio-memory context additions should accept
  `PortfolioMemorySourceRepositories` first and keep individual-repository facades as compatibility
  wrappers.
- Wiki decision: no wiki source change required; this is internal dependency-boundary cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-035: Candidate discovery scan bounds were service-local only

- Date: 2026-05-31
- Scope: portfolio-memory candidate discovery source scan bounds
- Finding: portfolio-memory search request normalization validated `source_scan_limit`, but the
  lower-level `candidate_portfolio_ids_from_sources` helper still accepted direct unsafe scan
  bounds. Direct callers could therefore bypass the service-level guardrail and ask repositories
  for zero, negative, or oversized source scans.
- Action: promoted source-scan validation to a reusable search-request helper, reused it from both
  search request normalization and candidate discovery, and added focused tests for direct
  candidate-discovery rejection.
- Status: hardened
- Evidence: focused tests in `tests/unit/dpm/portfolio_memory/test_candidate_portfolios.py` and
  `tests/unit/dpm/portfolio_memory/test_search_request.py`.
- Follow-up: any future repository-scan continuation or cursor semantics should reuse the shared
  source-scan validation boundary before reaching source repositories.
- Wiki decision: no wiki source change required; this is internal defensive validation hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-036: Portfolio-memory path parameters lacked Swagger guidance

- Date: 2026-05-31
- Scope: portfolio-memory detail and event-lookup OpenAPI path parameter documentation
- Finding: portfolio-memory detail and exact-event lookup routes carried rich endpoint
  descriptions, but their `portfolio_id` and `event_id` path parameters were plain strings. Swagger
  therefore lacked parameter-level usage guidance and examples for the audit/demo drilldown path.
- Action: added FastAPI `Path` descriptions and examples for portfolio-memory `portfolio_id` and
  `event_id`, and extended the OpenAPI regression test to pin those parameter docs.
- Status: hardened
- Evidence: OpenAPI assertions in `tests/unit/dpm/api/test_portfolio_memory_api.py`.
- Follow-up: keep new portfolio-memory route parameters annotated at the API boundary when adding
  continuation, source-family, or drilldown routes.
- Wiki decision: no wiki source change required; this improves generated Swagger/OpenAPI guidance
  without changing route behavior, payloads, or operator-facing wiki truth.

## BACKEND-REVIEW-20260531-037: Search-page assembly owned facet aggregation

- Date: 2026-05-31
- Scope: portfolio-memory search facet aggregation
- Finding: `src/core/portfolio_memory/search_page.py` still mixed pagination/envelope assembly with
  matching-event facet aggregation. That made search-page construction harder to review and left
  facet counting without a direct unit boundary even though source-system and source-type facets
  are an audit/demo-facing search contract.
- Action: extracted facet counting into `src/core/portfolio_memory/search_facets.py`, kept
  `build_search_page` focused on sorting, pagination, and envelope finalization, and added a
  focused facet test covering matching events plus portfolio-level source-system coverage.
- Status: hardened
- Evidence: focused test in `tests/unit/dpm/portfolio_memory/test_search_facets.py` plus existing
  search-page and portfolio-memory API tests.
- Follow-up: add future portfolio-memory facets through the facet module before threading them into
  the API envelope.
- Wiki decision: no wiki source change required; this is internal modularity cleanup with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-038: Portfolio-memory module boundaries were not visible in architecture wiki

- Date: 2026-05-31
- Scope: portfolio-memory architecture wiki and implementation-backed module map
- Finding: the wiki API and current-state pages described the portfolio-memory capability, but the
  architecture page did not explain the implemented module boundaries now used by the refactor:
  source repository bundles, candidate discovery, source-family collectors, search request/filter,
  search facet/page modules, and report-safe handoff context.
- Action: added an implementation-backed portfolio-memory module-boundary diagram and reader
  guidance to `wiki/Architecture.md`, and pinned it with the documentation current-state test pack.
- Status: hardened
- Evidence: docs regression test in `tests/unit/test_documentation_current_state.py`.
- Follow-up: keep architecture wiki module maps current when portfolio-memory source families,
  search facets, or handoff consumers change.
- Wiki decision: updated `wiki/Architecture.md` because implementation-backed module boundaries are
  developer, operations, demo, and client-pitch product truth.

## BACKEND-REVIEW-20260531-039: Source-family collection trusted caller read limits

- Date: 2026-05-31
- Scope: portfolio-memory source-family event collection guardrails
- Finding: `build_portfolio_memory_from_sources` validated read limits before collecting source
  events, but `collect_portfolio_memory_events` still accepted direct unsafe limits. Direct
  internal callers could therefore bypass the shared portfolio-memory read-limit policy before
  source-family repositories were queried.
- Action: moved the shared read-limit validation into the source-family collection boundary while
  keeping the service-level validation as a public facade guardrail.
- Status: hardened
- Evidence: focused rejection tests in `tests/unit/dpm/portfolio_memory/test_source_collection.py`.
- Follow-up: keep future continuation or per-family source scan controls validated before any
  repository fan-out.
- Wiki decision: no wiki source change required; this is internal defensive validation with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-040: API routes used deprecated 422 status constants

- Date: 2026-05-31
- Scope: portfolio-memory and proof-pack API validation responses
- Finding: portfolio-memory and proof-pack routes still raised validation errors with
  `HTTP_422_UNPROCESSABLE_ENTITY`, which now emits framework deprecation warnings while other
  manage routes already use `HTTP_422_UNPROCESSABLE_CONTENT`.
- Action: replaced the deprecated route-level status constants with the current FastAPI/Starlette
  422 constant while preserving the public HTTP status code and error payloads.
- Status: hardened
- Evidence: focused portfolio-memory and proof-pack API tests plus the portfolio-memory lane.
- Follow-up: keep new validation routes on `HTTP_422_UNPROCESSABLE_CONTENT` and treat deprecation
  warnings in focused tests as cleanup candidates rather than tolerated noise.
- Wiki decision: no wiki source change required; this is route implementation hygiene with no API
  status-code, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-041: Event deduplication depended on source iteration order

- Date: 2026-05-31
- Scope: portfolio-memory aggregate event deduplication
- Finding: portfolio-memory event deduplication used dictionary overwrite semantics, so duplicate
  event ids were resolved by whichever source-family projection was iterated last. That made the
  aggregate sensitive to source-family ordering instead of event identity and event time.
- Action: changed duplicate resolution to keep the latest event by event time with stable
  source/hash tie-breakers before applying the existing descending timeline sort.
- Status: hardened
- Evidence: focused search-filter test proving duplicate resolution is independent of input order.
- Follow-up: if duplicate ids become a source-quality signal, add explicit duplicate diagnostics
  rather than reintroducing order-sensitive overwrite behavior.
- Wiki decision: no wiki source change required; this is deterministic aggregate hygiene with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-042: Search vocabulary validation was router-local

- Date: 2026-05-31
- Scope: portfolio-memory search request vocabulary validation
- Finding: unsupported portfolio-memory event types were rejected at the API router, but direct core
  search callers could still pass unsupported event-type strings and receive empty results. Search
  supportability-state normalization had the same direct-call drift risk despite API-level pattern
  validation.
- Action: moved event-type and supportability-state vocabulary normalization into
  `src/core/portfolio_memory/search_request.py`, kept the API route translating those validation
  errors into 422 responses, and added focused request-normalization tests.
- Status: hardened
- Evidence: focused search-request tests plus the portfolio-memory API/search lane.
- Follow-up: add future portfolio-memory search vocabularies through the request-normalization
  module before exposing them in routers or service facades.
- Wiki decision: no wiki source change required; this is internal validation-boundary hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-043: Search Swagger did not list supported filter vocabularies

- Date: 2026-05-31
- Scope: portfolio-memory search OpenAPI parameter guidance
- Finding: the search API rejected unsupported event-type and supportability-state filters, but
  Swagger only said unsupported event types are rejected and did not list the implementation-backed
  accepted vocabularies for client developers, demo operators, or Gateway consumers.
- Action: wired the search route parameter descriptions to the shared request-normalization
  vocabulary constants and pinned representative event/supportability values in the OpenAPI test.
- Status: hardened
- Evidence: OpenAPI assertions in `tests/unit/dpm/api/test_portfolio_memory_api.py`.
- Follow-up: keep Swagger parameter guidance generated from shared vocabulary constants when new
  portfolio-memory search filters are added.
- Wiki decision: no wiki source change required; this improves generated OpenAPI guidance without
  changing routes, payloads, supported features, or operator wiki truth.

## BACKEND-REVIEW-20260531-044: Supportability query regex duplicated request vocabulary

- Date: 2026-05-31
- Scope: portfolio-memory search OpenAPI supportability-state query constraint
- Finding: the search route still carried a hard-coded supportability-state regex even after the
  request-normalization layer exposed shared supported-state constants. That created another drift
  point between FastAPI parameter validation, Swagger, and core request validation.
- Action: generated the FastAPI query regex from the shared supportability-state constants and
  pinned the OpenAPI pattern in the API test.
- Status: hardened
- Evidence: OpenAPI assertion in `tests/unit/dpm/api/test_portfolio_memory_api.py`.
- Follow-up: keep route-level query constraints generated from shared vocabulary constants instead
  of duplicating allowed values in controller code.
- Wiki decision: no wiki source change required; this is API contract implementation hygiene with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-045: Search timestamp ties sorted portfolio ids descending

- Date: 2026-05-31
- Scope: portfolio-memory search-page ordering
- Finding: search pages sorted by `(latest_event_time, portfolio_id)` with `reverse=True`, so
  equal-timestamp rows were deterministic but ordered by portfolio id descending. That is a weak
  UX and audit posture for tie cases because portfolio identifiers should use ascending stable
  order when event recency is equal.
- Action: changed search-page sorting to apply portfolio id as the stable ascending tie-breaker
  after ordering latest event timestamps descending.
- Status: hardened
- Evidence: focused search-page test proving equal timestamp rows return in ascending portfolio-id
  order.
- Follow-up: keep future search sort additions explicit about descending versus ascending fields
  instead of relying on whole-tuple reverse sorting.
- Wiki decision: no wiki source change required; this is deterministic response-order hygiene with
  no route, payload-shape, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-046: Explicit search portfolio ids were unbounded

- Date: 2026-05-31
- Scope: portfolio-memory search request candidate bounds
- Finding: repository source scans were bounded by `source_scan_limit`, but caller-supplied
  `portfolio_ids` were only normalized and deduplicated. A request with many explicit identifiers
  could force unbounded portfolio-memory assembly even when repository fan-out was constrained.
- Action: added explicit portfolio-id normalization that rejects unique caller-supplied candidate
  counts above `source_scan_limit`, and translated the validation error to a 422 API response.
- Status: hardened
- Evidence: focused search-request and API tests for duplicate/blank normalization and over-limit
  rejection.
- Follow-up: keep future caller-supplied candidate selectors tied to scan bounds before invoking
  per-portfolio memory assembly.
- Wiki decision: no wiki source change required; this is defensive request-boundary hardening with
  no route, payload-shape, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-047: Search route duplicated validation-error translation

- Date: 2026-05-31
- Scope: portfolio-memory search API error handling
- Finding: after moving search validation into the request-normalization layer, the API route had
  repeated `ValueError` to HTTP 422 translation blocks for vocabulary checks and service request
  normalization.
- Action: extracted a small route-local helper for portfolio-memory search validation errors so the
  controller has one consistent mapping for request-boundary failures.
- Status: hardened
- Evidence: focused portfolio-memory API tests covering unsupported event type and excessive
  explicit portfolio ids.
- Follow-up: keep route-local validation translation centralized when additional search request
  validators are added.
- Wiki decision: no wiki source change required; this is controller maintainability cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-048: Portfolio-memory search candidate bound was not in API wiki

- Date: 2026-05-31
- Scope: portfolio-memory API wiki bounds documentation
- Finding: explicit `portfolio_ids` are now bounded by `source_scan_limit`, but the API wiki still
  described only the query parameters and detail/event lookup event caps. Operators and client
  developers would not know why an over-limit explicit candidate request returns HTTP 422.
- Action: documented the explicit candidate-id bound in `wiki/API-Surface.md` and pinned the
  wording in the documentation current-state test.
- Status: hardened
- Evidence: docs regression test in `tests/unit/test_documentation_current_state.py`.
- Follow-up: keep wiki API bounds aligned with request-normalization behavior whenever search
  pagination, source scan, or explicit candidate semantics change.
- Wiki decision: updated `wiki/API-Surface.md` because this is implementation-backed API behavior
  visible to developers, operators, Gateway consumers, and demo preparation.

## BACKEND-REVIEW-20260531-049: Current-state wiki omitted candidate-bound posture

- Date: 2026-05-31
- Scope: portfolio-memory current-state product truth
- Finding: the current-state wiki said portfolio-memory search is bounded to Manage-local evidence
  and explicit caller-supplied identifiers, but it did not mention the new `source_scan_limit`
  bound for deduplicated explicit identifiers. That left demo and client-facing product posture
  less precise than the API contract.
- Action: updated `wiki/Current-State.md` to state the explicit-candidate bound in both the
  functional matrix and non-claim boundary, and pinned the current-state page test.
- Status: hardened
- Evidence: docs regression test in `tests/unit/test_documentation_current_state.py`.
- Follow-up: keep current-state product claims aligned with API behavior when bounded search
  controls change.
- Wiki decision: updated `wiki/Current-State.md` because this is implementation-backed
  product-current-state and demo/client-pitch truth.

## BACKEND-REVIEW-20260531-050: Wave campaign read-model query flow was duplicated in the router

- Date: 2026-05-31
- Scope: bulk-review campaign discovery, operating queue, approval inbox, workflow board,
  assignment plan, and workflow-automation read models
- Finding: `src/api/routers/waves.py` repeated the same `active_on` parsing and campaign-definition
  repository filtering across six read-model endpoints. That kept request-boundary query shaping
  mixed into every controller function and increased the chance of drift in date validation,
  status/as-of filters, pagination, or future campaign read-model route additions.
- Action: extracted campaign read-model query loading to
  `src/api/routers/wave_campaign_read_model_query.py` and updated the six endpoints to consume one
  typed query result containing the repository page and parsed `active_on` date.
- Status: hardened
- Evidence: focused tests in `tests/unit/api/test_wave_campaign_read_model_query.py` plus targeted
  Ruff checks for the changed router/helper/test files.
- Follow-up: keep future campaign read-model endpoints on the shared query helper before adding
  endpoint-specific projection logic.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-051: Campaign definition path parameters lacked reusable API documentation

- Date: 2026-05-31
- Scope: bulk-review campaign definition route path parameters in `src/api/routers/waves.py`
- Finding: campaign-definition endpoints repeated bare `campaign_id`, `campaign_version`, and
  assignment `task_ref` path parameters without shared descriptions or examples. That left a large
  workflow surface dependent on generated default Swagger wording instead of domain-correct API
  documentation.
- Action: introduced reusable FastAPI `Annotated` path aliases for campaign definition id,
  campaign definition version, and assignment task reference, then applied them across the
  campaign-definition route family.
- Status: hardened
- Evidence: OpenAPI regression coverage in `tests/unit/dpm/api/test_waves_api.py`, focused Ruff
  checks, source-file mypy on `src/api/routers/waves.py`, OpenAPI quality gate, and regenerated
  API vocabulary inventory validation.
- Follow-up: apply the same reusable path-parameter documentation pattern to durable wave id and
  wave item id routes in a separate slice.
- Wiki decision: no wiki source change required; this is Swagger/API documentation hardening for
  existing routes with no behavior, payload, or supported-feature change.

## BACKEND-REVIEW-20260531-052: Durable wave path parameters lacked reusable API documentation

- Date: 2026-05-31
- Scope: durable rebalance wave route path parameters in `src/api/routers/waves.py`
- Finding: durable wave endpoints still used bare `wave_id` and `wave_item_id` path parameters
  after campaign-definition path parameters were standardized. That left core wave detail,
  item-selection, workflow, proof-pack, report-input, and supportability routes with weaker
  Swagger parameter descriptions than the campaign route family.
- Action: added reusable FastAPI `Annotated` path aliases for durable wave id and wave item id,
  applied them across the durable wave route family, and regenerated the API vocabulary inventory.
- Status: hardened
- Evidence: OpenAPI regression coverage in `tests/unit/dpm/api/test_waves_api.py`, focused Ruff
  checks, source-file mypy on `src/api/routers/waves.py`, OpenAPI quality gate, and regenerated
  API vocabulary inventory validation.
- Follow-up: continue using shared path-parameter aliases when new wave subroutes are added.
- Wiki decision: no wiki source change required; this is Swagger/API documentation hardening for
  existing routes with no behavior, payload, or supported-feature change.

## BACKEND-REVIEW-20260531-053: Campaign read-model query parameters repeated weak Swagger metadata

- Date: 2026-05-31
- Scope: campaign definition list and bulk-review campaign read-model query parameters
- Finding: campaign-definition list, discovery, operating queue, approval inbox, workflow board,
  assignment plan, and workflow automation endpoints repeated bare query parameter definitions for
  campaign id, campaign status, as-of date, expiry date, include-expired, limit, and offset. The
  route behavior was bounded, but the Swagger metadata and controller signatures were less reusable
  than the API surface warrants.
- Action: introduced shared `Annotated` query aliases for the campaign read-model filters and
  pagination controls, applied them across the campaign read-model endpoints, and regenerated the
  API vocabulary inventory.
- Status: hardened
- Evidence: OpenAPI regression coverage in `tests/unit/dpm/api/test_waves_api.py`, focused Ruff
  checks, source-file mypy on `src/api/routers/waves.py`, OpenAPI quality gate, and regenerated
  API vocabulary inventory validation.
- Follow-up: review campaign action/list endpoints separately before applying the read-model
  pagination aliases there, because those pages represent append-only evidence ledgers rather than
  the front-office campaign read models.
- Wiki decision: no wiki source change required; this is Swagger/API documentation and controller
  maintainability hardening for existing routes with no behavior, payload, or supported-feature
  change.

## BACKEND-REVIEW-20260531-054: Wave route parameter aliases were embedded in the main router

- Date: 2026-05-31
- Scope: reusable wave route path and query parameter aliases
- Finding: after hardening wave Swagger metadata, the reusable `Annotated` path/query aliases lived
  directly in `src/api/routers/waves.py`. That kept domain API documentation primitives mixed with
  route wiring in an already large controller module.
- Action: moved campaign and durable-wave path/query aliases into
  `src/api/routers/wave_route_parameters.py`, leaving `waves.py` to import the shared route
  parameter contracts.
- Status: hardened
- Evidence: focused OpenAPI regression coverage, focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: place future wave route parameter aliases in the shared module instead of adding
  controller-local `Path` or `Query` metadata.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-055: Campaign evidence pagination repeated weak Swagger metadata

- Date: 2026-05-31
- Scope: campaign approval-decision, assignment-action, assignment-task, maker-checker-control, and
  launch-history evidence pages
- Finding: append-only campaign evidence endpoints repeated bare `limit` and `offset` query
  metadata. Those pages are audit/evidence ledgers and should not inherit generic pagination
  wording from generated OpenAPI defaults.
- Action: added shared campaign evidence pagination aliases in
  `src/api/routers/wave_route_parameters.py`, applied them to the append-only evidence pages, and
  regenerated the API vocabulary inventory.
- Status: hardened
- Evidence: OpenAPI regression coverage in `tests/unit/dpm/api/test_waves_api.py`, focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and regenerated API vocabulary inventory
  validation.
- Follow-up: keep read-model pagination and evidence-ledger pagination separate so future docs do
  not blur operational queues with audit/evidence record pages.
- Wiki decision: no wiki source change required; this is Swagger/API documentation hardening for
  existing routes with no behavior, payload, or supported-feature change.

## BACKEND-REVIEW-20260531-056: Campaign read-model context queries repeated entitlement wording

- Date: 2026-05-31
- Scope: campaign operating queue, approval inbox, workflow board, assignment plan, and workflow
  automation query metadata
- Finding: `requested_as_of_date`, `actor_id`, and `include_closed` query parameters repeated
  route-local Swagger text across the campaign read-model endpoints. These fields carry shared
  readiness, expiry, entitlement, and closed-row semantics, so duplicating their descriptions made
  future drift more likely.
- Action: added shared campaign read-model context query aliases for requested as-of date, actor id,
  and closed-row inclusion, applied them to the read-model endpoints, and regenerated the API
  vocabulary inventory.
- Status: hardened
- Evidence: OpenAPI regression coverage in `tests/unit/dpm/api/test_waves_api.py`, focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and regenerated API vocabulary inventory
  validation.
- Follow-up: keep launch-package command queries separate unless they share the same read-model
  semantics; launch commands have stricter operational meaning than queue projections.
- Wiki decision: no wiki source change required; this is Swagger/API documentation and controller
  maintainability hardening for existing routes with no behavior, payload, or supported-feature
  change.

## BACKEND-REVIEW-20260531-057: Campaign launch-readiness queries repeated command wording

- Date: 2026-05-31
- Scope: campaign workflow overview, preview-readiness, and launch-package query metadata
- Finding: launch-readiness endpoints repeated route-local query metadata for requested as-of date,
  actor id, launch-package inclusion, correlation id, and launch-history pagination. These queries
  drive fail-closed launch package guidance and are command-adjacent, so their Swagger wording
  should stay consistent without sharing weaker queue/read-model aliases by accident.
- Action: added shared launch-readiness query aliases in
  `src/api/routers/wave_route_parameters.py`, applied them to workflow overview,
  preview-readiness, and launch-package routes, and regenerated the API vocabulary inventory.
- Status: hardened
- Evidence: OpenAPI regression coverage in `tests/unit/dpm/api/test_waves_api.py`, focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and regenerated API vocabulary inventory
  validation.
- Follow-up: keep launch-readiness query aliases separate from read-model and evidence-page
  pagination aliases so command-adjacent API documentation remains precise.
- Wiki decision: no wiki source change required; this is Swagger/API documentation and controller
  maintainability hardening for existing routes with no behavior, payload, or supported-feature
  change.

## BACKEND-REVIEW-20260531-058: Wave correlation header metadata was duplicated across command routes

- Date: 2026-05-31
- Scope: wave preview, create, source-check, simulate, item selection, approval, staging, handoff,
  and cancellation routes
- Finding: wave command routes repeated route-local `X-Correlation-Id` header metadata. Correlation
  ids are supportability and audit controls, so duplicated Swagger text made it easier for command
  routes to drift in wording or examples.
- Action: added a shared `WaveCorrelationIdHeader` alias in
  `src/api/routers/wave_route_parameters.py`, applied it across wave command routes, pinned the
  OpenAPI header description, and regenerated the API vocabulary inventory.
- Status: hardened
- Evidence: OpenAPI regression coverage in `tests/unit/dpm/api/test_waves_api.py`, focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and regenerated API vocabulary inventory
  validation.
- Follow-up: review durable create `Idempotency-Key` header separately so idempotency semantics stay
  explicit and do not get blurred with optional correlation.
- Wiki decision: no wiki source change required; this is Swagger/API documentation and controller
  maintainability hardening for existing routes with no behavior, payload, or supported-feature
  change.

## BACKEND-REVIEW-20260531-059: Durable wave create idempotency header was route-local metadata

- Date: 2026-05-31
- Scope: durable wave create `Idempotency-Key` header contract
- Finding: the durable wave create endpoint carried its idempotency header metadata directly in
  `src/api/routers/waves.py`. Idempotency is a command-safety contract, so it should be reusable
  route metadata and kept deliberately separate from optional correlation headers.
- Action: added `WaveCreateIdempotencyKeyHeader` to
  `src/api/routers/wave_route_parameters.py`, applied it to durable wave create, pinned the
  OpenAPI header description, and regenerated the API vocabulary inventory.
- Status: hardened
- Evidence: OpenAPI regression coverage in `tests/unit/dpm/api/test_waves_api.py`, focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and regenerated API vocabulary inventory
  validation.
- Follow-up: keep future command idempotency headers modeled as explicit command-safety contracts
  rather than generic header parameters.
- Wiki decision: no wiki source change required; this is Swagger/API documentation and controller
  maintainability hardening for an existing route with no behavior, payload, or supported-feature
  change.

## BACKEND-REVIEW-20260531-060: Campaign read-model routes lived in the monolithic wave router

- Date: 2026-05-31
- Scope: campaign discovery, operating queue, approval inbox, workflow board, assignment plan, and
  workflow automation route definitions
- Finding: read-only front-office campaign read-model routes still lived in
  `src/api/routers/waves.py` after their query contracts and query loader were extracted. That kept
  queue/projection route ownership mixed with campaign definition commands and durable wave command
  routes in the same large controller module.
- Action: moved the campaign read-model route group into
  `src/api/routers/wave_campaign_read_model_routes.py` and mounted it from the main wave router
  without changing route paths or response contracts.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and regenerated API vocabulary inventory
  validation.
- Follow-up: continue extracting route groups by ownership boundary before touching deeper service
  orchestration, so route registration stays easy to verify.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-061: Campaign definition lifecycle routes lived in the monolithic wave router

- Date: 2026-05-31
- Scope: campaign definition create, list, retire, and supersede route definitions
- Finding: campaign definition lifecycle routes still lived directly in
  `src/api/routers/waves.py` even though their response handling already lived in
  `src/api/routers/wave_campaign_definition_http.py`. That kept definition persistence and
  lifecycle registration mixed with read models, workflow evidence, and durable wave command
  routes in the same large controller module.
- Action: moved the campaign definition lifecycle route group into
  `src/api/routers/wave_campaign_definition_routes.py`, mounted it from the main wave router in the
  original registration position, and updated the API regression test to import the request model
  from its owning module instead of relying on an accidental `waves.py` re-export.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: extract the remaining campaign definition detail/action/readiness routes by ownership
  boundary while preserving route registration order and public contracts.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-062: Campaign evidence routes lived in the monolithic wave router

- Date: 2026-05-31
- Scope: campaign approval-decision, assignment-action, assignment-task, and maker-checker-control
  route definitions
- Finding: campaign evidence and control routes still lived directly in
  `src/api/routers/waves.py`. These routes share append-only evidence semantics, pagination
  contracts, and campaign-definition repository access, so keeping them mixed with durable wave
  preview/create and launch orchestration increased controller size and ownership ambiguity.
- Action: moved the campaign evidence/control route group into
  `src/api/routers/wave_campaign_evidence_routes.py` and mounted it from the main wave router after
  the campaign definition detail route, preserving the original public path order and response
  contracts.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: extract campaign lifecycle/readiness read routes separately from the durable launch
  command so read-side supportability remains distinct from wave creation behavior.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-063: Campaign readiness read routes lived beside launch commands

- Date: 2026-05-31
- Scope: campaign lifecycle-events, launch-history, workflow-overview, preview-readiness, and
  launch-package route definitions
- Finding: campaign readiness and supportability read routes still lived directly in
  `src/api/routers/waves.py` beside the durable campaign launch command and generic wave
  preview/create routes. These endpoints are operator read models over persisted campaign
  definitions, not wave creation handlers, so their route ownership should stay separate from
  command orchestration.
- Action: moved the campaign readiness/read route group into
  `src/api/routers/wave_campaign_readiness_routes.py` and mounted it after the campaign evidence
  router, preserving the original public path order and response contracts.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: isolate the durable campaign launch command from generic durable wave preview/create
  routing when the next slice can preserve command dependency wiring clearly.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-064: Campaign launch route lived beside generic wave commands

- Date: 2026-05-31
- Scope: durable bulk-review campaign definition launch route definition
- Finding: the campaign-definition launch endpoint still lived directly in
  `src/api/routers/waves.py` beside generic wave preview/create routes. The route is a campaign
  command with campaign-definition repository wiring, launch-package readiness, and deterministic
  launch idempotency semantics, so keeping it in the generic wave controller blurred ownership.
- Action: moved the durable campaign launch route into
  `src/api/routers/wave_campaign_launch_routes.py` and mounted it after the campaign readiness
  read router, preserving the original public path order and response contract.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: review generic wave preview/create/search/detail routes next, because the remaining
  controller still mixes command, search, detail, item, and workflow subdomains.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-065: Generic wave preview/create routes lived in the main wave router

- Date: 2026-05-31
- Scope: generic wave preview and durable wave create route definitions
- Finding: the non-durable preview and durable create routes still lived directly in
  `src/api/routers/waves.py`, mixing source-resolution command orchestration with search, detail,
  item, workflow, and report-input endpoints. These routes share source resolver wiring, mandate
  repository access, optional correlation, and create idempotency contracts, so they form a
  coherent command boundary.
- Action: moved preview/create route registration into
  `src/api/routers/wave_create_preview_routes.py`. The module uses a registration helper instead
  of a child router because FastAPI rejects included child routers that contribute an empty-string
  path operation; the helper preserves the exact `POST /rebalance/waves` public route and the
  existing `build_core_resolver_client` monkeypatch seam used by regression tests.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: continue separating remaining generic wave search/detail/item/workflow routes by
  read-side and command-side ownership boundaries.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-066: Wave source-check route lived in the main wave router

- Date: 2026-05-31
- Scope: durable wave source-check route definition
- Finding: the source-check command still lived directly in `src/api/routers/waves.py` even though
  its response handling already lived in `src/api/routers/wave_source_check_http.py`. Source-check
  is a source-readiness command with mandate repository wiring and idempotent replay semantics, so
  it should not stay mixed with search, detail, simulation, item selection, and workflow command
  routes.
- Action: moved the source-check route into `src/api/routers/wave_source_check_routes.py` and
  mounted it from the main wave router after item read routes, preserving public path order and
  response contracts. The child router intentionally inherits parent tags to avoid duplicate
  OpenAPI tag entries.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: continue extracting simulation and item/workflow command groups separately so command
  dependencies stay visible and independently testable.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-067: Wave simulation route lived in the main wave router

- Date: 2026-05-31
- Scope: durable wave simulation route definition
- Finding: the simulation command still lived directly in `src/api/routers/waves.py` even though
  its response handling already lived in `src/api/routers/wave_simulation_http.py`. Simulation has
  construction repository, risk authority, run-support, and wave repository dependencies, so it is a
  distinct command boundary from source-check, item selection, and workflow transitions.
- Action: moved the simulation route into `src/api/routers/wave_simulation_routes.py` and mounted
  it after source-check, preserving public path order and response contracts. The child router
  inherits parent tags to avoid duplicate OpenAPI tag entries.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: extract item-selection/proof-pack command routes separately from wave workflow state
  commands.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-068: Wave item-selection route lived in the main wave router

- Date: 2026-05-31
- Scope: durable wave item construction-alternative selection route definition
- Finding: the item-selection command still lived directly in `src/api/routers/waves.py` even
  though its response handling already lived in `src/api/routers/wave_selection_http.py`.
  Selection has construction, proof-pack, mandate, run-support, and wave repository dependencies,
  and it can optionally generate proof-pack evidence, so it should remain separate from wave
  workflow state-transition commands.
- Action: moved the item-selection route into `src/api/routers/wave_selection_routes.py` and
  mounted it after simulation, preserving public path order and response contracts. The child
  router inherits parent tags to avoid duplicate OpenAPI tag entries.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: extract wave workflow state-transition commands into their own route module and then
  review the remaining read-only search/detail/proof-pack/report/supportability routes.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-069: Wave workflow commands lived in the main wave router

- Date: 2026-05-31
- Scope: durable wave approve, stage, handoff, and cancel route definitions
- Finding: wave workflow state-transition commands still lived directly in
  `src/api/routers/waves.py` even though their shared HTTP response handling already lived in
  `src/api/routers/wave_workflow_command_http.py`. These endpoints share a command envelope,
  correlation-id handling, idempotent replay semantics, and wave repository dependency, so keeping
  them mixed with read-only search/detail/supportability routes obscured the command boundary.
- Action: moved the workflow command group into `src/api/routers/wave_workflow_routes.py` and
  mounted it after item selection, preserving public path order and response contracts. The child
  router inherits parent tags to avoid duplicate OpenAPI tag entries.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: extract the remaining read-only wave search/detail/proof-pack/report/supportability
  routes into read-model route modules and review whether the campaign detail route should join the
  campaign-definition route module.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-070: Wave search/detail/item read routes lived in the main router

- Date: 2026-05-31
- Scope: durable wave search, wave detail, and wave item read route definitions
- Finding: read-only durable wave search/detail/item routes still lived directly in
  `src/api/routers/waves.py` after the command routes were extracted. These endpoints are
  persisted read models over wave state and should be owned separately from source-check,
  simulation, selection, and workflow command routes.
- Action: moved search/detail/item route registration into `src/api/routers/wave_read_routes.py`.
  The module uses a registration helper rather than a child router because the search route is an
  empty-string path operation (`GET /rebalance/waves`), which FastAPI cannot include from a
  zero-prefix child router.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: extract proof-pack/report/supportability read routes as a final wave read-support
  group, then move the campaign definition detail route to campaign-definition ownership.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-071: Wave read-support routes lived in the main router

- Date: 2026-05-31
- Scope: durable wave proof-pack posture, report-input, and supportability route definitions
- Finding: wave proof-pack posture, report-input, and supportability reads still lived directly in
  `src/api/routers/waves.py`. These endpoints are read-support views over persisted wave evidence,
  proof-pack linkage, report materialization inputs, and product-safe diagnostics; keeping them in
  the root router mixed operational reads with route composition.
- Action: moved the read-support route group into
  `src/api/routers/wave_read_support_routes.py` and mounted it after workflow commands, preserving
  public path order and response contracts. The child router inherits parent tags to avoid
  duplicate OpenAPI tag entries.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: move the remaining campaign definition detail route into campaign-definition route
  ownership so the main wave router becomes composition-only.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-072: Campaign definition detail route kept the main router non-compositional

- Date: 2026-05-31
- Scope: campaign definition detail route definition and main wave router composition
- Finding: after extracting campaign, wave command, and wave read route groups, the campaign
  definition detail endpoint was the only remaining business route implemented directly in
  `src/api/routers/waves.py`. That kept the root router from becoming a composition-only module
  and left campaign definition ownership split across files.
- Action: moved the campaign definition detail route into
  `src/api/routers/wave_campaign_definition_routes.py` using a separate detail router that is
  mounted after campaign read-model routes, preserving the original public path order and response
  contract. The main wave router now only composes owned route modules.
- Status: hardened
- Evidence: full wave API regression test (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: review the newly extracted route modules for repeated router construction patterns
  and consider a lightweight route-registration convention once the split has stabilized.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-073: PM operating quality correlation header metadata was duplicated

- Date: 2026-05-31
- Scope: PM operating quality command endpoints for score runs, fairness analyses, review actions,
  and summary invocations.
- Finding: eight command routes repeated route-local `X-Correlation-Id` header metadata. The
  correlation id is an audit, supportability, and downstream governance traceability contract, so
  repeated local Swagger descriptions could drift across PM operating quality command endpoints.
- Action: added the shared `PmQualityCorrelationIdHeader` route parameter contract and applied it
  across PM operating quality command routes. The PM operating quality OpenAPI regression now pins
  the governed header description, and the API vocabulary inventory was regenerated to reflect the
  updated Swagger-visible contract.
- Status: hardened
- Evidence: PM operating quality API regression test (`tests/unit/api/test_pm_operating_quality_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift after regeneration.
- Follow-up: continue extracting PM operating quality route groups by lifecycle boundary once
  shared route parameter contracts are stable.
- Wiki decision: no wiki source change required; this is Swagger/API documentation and controller
  maintainability hardening for existing routes with no behavior, payload, supported-feature, or
  operator-contract change.

## BACKEND-REVIEW-20260531-074: PM operating quality policy routes lived in the main router

- Date: 2026-05-31
- Scope: PM operating quality policy persist, list, and detail route definitions.
- Finding: policy administration endpoints still lived directly in
  `src/api/routers/pm_operating_quality.py` alongside score-run, fairness, review-action, and
  support-summary lifecycle routes. That made the router harder to scan and mixed immutable policy
  configuration ownership with execution and evidence workflows.
- Action: moved the policy route group into `src/api/routers/pm_operating_quality_policy_routes.py`
  and mounted it from the parent PM operating quality router, preserving public paths, response
  models, descriptions, and repository behavior.
- Status: hardened
- Evidence: PM operating quality API regression test (`tests/unit/api/test_pm_operating_quality_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: continue extracting PM operating quality lifecycle route groups, with score-run
  extraction deferred until the private helper tests and core-resolver monkeypatch boundary are
  made explicit.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-075: PM operating quality fairness routes were mixed with other lifecycles

- Date: 2026-05-31
- Scope: PM operating quality fairness-analysis preview, create, list, detail, and route-local
  builder behavior.
- Finding: fairness-analysis endpoints and the route-local fairness builder lived inside the
  general PM operating quality router, mixed with score-run, review-action, summary-invocation,
  and policy routes. That obscured the fairness lifecycle boundary and kept model-risk governance
  behavior harder to inspect.
- Action: moved the fairness-analysis route group and builder into
  `src/api/routers/pm_operating_quality_fairness_routes.py` and mounted it from the parent PM
  operating quality router, preserving public paths, response contracts, descriptions, conflict
  handling, and service error mapping.
- Status: hardened
- Evidence: PM operating quality API regression test (`tests/unit/api/test_pm_operating_quality_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: extract review-action and support-summary lifecycle routes next, then make the
  score-run helper/core-resolver test seam explicit before moving score-run routes.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-076: PM operating quality summary-invocation routes were mixed with review flows

- Date: 2026-05-31
- Scope: PM operating quality support-summary invocation preview, create, list, detail, and
  route-local builder behavior.
- Finding: support-summary invocation endpoints and their validation builder lived in the parent
  PM operating quality router alongside score-run, fairness, review-action, and policy routes.
  These routes own append-only support-summary workflow evidence and have a distinct governance
  boundary from supervisory review actions.
- Action: moved the summary-invocation route group and builder into
  `src/api/routers/pm_operating_quality_summary_routes.py` and mounted it from the parent PM
  operating quality router, preserving public paths, response contracts, descriptions, conflict
  handling, missing-target behavior, and validation error mapping.
- Status: hardened
- Evidence: PM operating quality API regression test (`tests/unit/api/test_pm_operating_quality_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: isolate review-action routes after making the parent-level builder monkeypatch
  contract explicit, then finish score-run extraction.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-077: PM operating quality review-action routes obscured the parent router

- Date: 2026-05-31
- Scope: PM operating quality review-action preview, create, list, and detail route registration.
- Finding: review-action endpoints still occupied the parent PM operating quality router even after
  policy, fairness, and support-summary routes were extracted. These routes own supervisory review
  evidence and conflict handling, while the parent should increasingly compose lifecycle modules.
- Action: moved review-action route registration into
  `src/api/routers/pm_operating_quality_review_action_routes.py`. The parent keeps the existing
  `_build_review_action` helper and supplies it through an explicit route-builder adapter so
  existing private tests and monkeypatches remain stable while route ownership is separated.
- Status: hardened
- Evidence: PM operating quality API regression test (`tests/unit/api/test_pm_operating_quality_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: make the score-run builder/core-resolver dependency boundary explicit, then extract
  score-run command and read routes as the final PM operating quality router decomposition step.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-078: PM operating quality score-run routes kept the router non-compositional

- Date: 2026-05-31
- Scope: PM operating quality score-run preview, create, list, and detail route registration.
- Finding: score-run command and read endpoints were the last route definitions implemented
  directly in `src/api/routers/pm_operating_quality.py`. The parent router still needed to retain
  private builder and source-resolution helpers for existing focused tests, but direct route
  definitions were no longer necessary there.
- Action: moved score-run command and read route registration into
  `src/api/routers/pm_operating_quality_score_run_routes.py` with separate command and read
  registration functions so the existing OpenAPI path order is preserved. The parent router now
  composes PM operating quality lifecycle route modules and keeps only builder/support helper
  behavior.
- Status: hardened
- Evidence: PM operating quality API regression test (`tests/unit/api/test_pm_operating_quality_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: review whether PM operating quality helper functions should move behind an explicit
  injectable service boundary once the current private tests are converted away from parent-module
  monkeypatching.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-079: Run artifact endpoint lived in the supportability root router

- Date: 2026-05-31
- Scope: deterministic DPM run artifact route registration for
  `GET /api/v1/rebalance/runs/{rebalance_run_id}/artifact`.
- Finding: the deterministic run artifact endpoint was still implemented directly in
  `src/api/routers/rebalance_runs.py`, which already owns service initialization, feature gates,
  lookup APIs, support bundles, operations, and workflow composition. Artifact retrieval is a
  distinct supportability sub-surface with its own feature gate and audit/replay contract.
- Action: moved artifact route registration into
  `src/api/routers/rebalance_runs_artifact_routes.py` while preserving public path, response
  model, Swagger metadata, feature gates, unsupported-query rejection, and not-found behavior.
- Status: hardened
- Evidence: focused DPM API supportability/artifact regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "artifact or support_bundle or supportability_summary or support_runs_list or idempotency_history"`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: extract run support-bundle routes next, then lookup/read routes, keeping
  supportability service initialization in the parent until dependency ownership is made explicit.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-080: Run support-bundle routes duplicated query metadata in the root router

- Date: 2026-05-31
- Scope: DPM run support-bundle routes by run id, correlation id, idempotency key, and operation
  id.
- Finding: support-bundle endpoints were implemented directly in `src/api/routers/rebalance_runs.py`
  and repeated the same optional-section query parameter metadata on each route. That kept the
  root supportability router large and made the support-bundle API contract more likely to drift
  across lookup variants.
- Action: moved support-bundle route registration into
  `src/api/routers/rebalance_runs_support_bundle_routes.py` and centralized the
  `include_artifact`, `include_async_operation`, and `include_idempotency_history` query parameter
  contracts while preserving paths, response models, Swagger descriptions, feature gates,
  unsupported-query rejection, and not-found behavior.
- Status: hardened
- Evidence: focused DPM API support-bundle regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "support_bundle"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: extract run lookup/read and idempotency-history route groups, then review
  supportability summary and service initialization as separate ownership boundaries.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-081: Run lookup and idempotency routes lived in the supportability root router

- Date: 2026-05-31
- Scope: DPM run lookup routes by correlation id, request hash, idempotency key, run id, and
  idempotency history.
- Finding: run lookup and idempotency supportability endpoints still lived directly in
  `src/api/routers/rebalance_runs.py`, mixed with service initialization, list/search,
  supportability summary, support bundles, artifact, operations, and workflow route composition.
  These endpoints form a distinct read/lineage lookup surface with consistent no-query-parameter
  posture and not-found handling.
- Action: moved lookup and idempotency route registration into
  `src/api/routers/rebalance_runs_lookup_routes.py`, preserving public paths, response models,
  Swagger descriptions, feature gates, unsupported-query rejection, idempotency-history gating, and
  not-found behavior.
- Status: hardened
- Evidence: focused DPM API lookup/supportability regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "supportability or idempotency_history or support_runs_list"`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: review whether list/search and supportability summary should move to separate route
  modules or remain with service initialization until the supportability root module is reduced to
  a composition/service-factory boundary.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-082: Run inventory and summary routes kept supportability router non-compositional

- Date: 2026-05-31
- Scope: DPM run inventory listing and store-wide supportability summary route registration.
- Finding: after artifact, support-bundle, and lookup route extraction, the root
  `src/api/routers/rebalance_runs.py` still directly implemented the run inventory and
  supportability summary endpoints. That kept request/Swagger/controller logic mixed with the
  supportability service factory and feature-gate helpers.
- Action: moved run inventory and supportability summary route registration into
  `src/api/routers/rebalance_runs_inventory_routes.py`, preserving public paths, response models,
  Swagger descriptions, unsupported-query rejection, supportability feature gates, retention
  configuration, and action-register observability recording.
- Status: hardened
- Evidence: focused DPM API inventory/summary regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "supportability_summary or support_runs_list"`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: review the supportability parent module for service-factory naming and explicit route
  composition ordering once operations/workflow modules are aligned with the newer extracted route
  module pattern.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-083: Supportability lineage route was mixed with async operations

- Date: 2026-05-31
- Scope: supportability lineage lookup for `GET /api/v1/rebalance/lineage/{entity_id}`.
- Finding: lineage search was implemented inside `rebalance_runs_operations_routes.py` alongside
  asynchronous operation list/detail routes. Lineage is an audit and traceability search surface
  with a separate feature gate and filter contract, so keeping it mixed with async operation
  polling obscured ownership and made future route review harder.
- Action: moved lineage route registration into `src/api/routers/rebalance_runs_lineage_routes.py`
  while preserving public path, response model, Swagger metadata, feature gates,
  unsupported-query rejection, lineage filters, and empty-page behavior for unknown entity ids.
- Status: hardened
- Evidence: focused DPM API lineage/async-operation regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "lineage or async_operation"`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: review async operation route metadata and workflow route duplication now that lineage
  is owned separately.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-084: Workflow decision routes were mixed with run workflow actions

- Date: 2026-05-31
- Scope: workflow decision listing and workflow-decision history lookup by correlation id.
- Finding: workflow decision search routes lived in `rebalance_runs_workflow_routes.py` alongside
  workflow state, workflow actions, and run/idempotency history routes. Decision search has a
  distinct filter contract and supports operational audit review across runs, while action routes
  own mutation, conflict handling, and workflow metrics.
- Action: moved workflow decision route registration into
  `src/api/routers/rebalance_runs_workflow_decision_routes.py`, preserving public paths, response
  models, Swagger metadata, query filters, feature gates, unsupported-query rejection, and
  not-found behavior.
- Status: hardened
- Evidence: focused DPM API workflow regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "workflow"`), focused Ruff checks, source-file
  mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split workflow state/history reads from workflow action commands so mutating review
  behavior and read-only supportability views are owned separately.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-085: Workflow history routes were mixed with workflow action commands

- Date: 2026-05-31
- Scope: workflow history routes by run id, correlation id, and idempotency key.
- Finding: read-only workflow history endpoints still lived in `rebalance_runs_workflow_routes.py`
  next to mutating workflow action routes. History retrieval is an append-only audit/read surface,
  while action routes own review command handling, transition conflicts, and workflow metrics.
- Action: moved workflow history route registration into
  `src/api/routers/rebalance_runs_workflow_history_routes.py`, preserving public paths, response
  models, Swagger metadata, feature gates, unsupported-query rejection, and not-found behavior.
- Status: hardened
- Evidence: focused DPM API workflow regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "workflow"`), focused Ruff checks, source-file
  mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split workflow action commands from workflow state reads, keeping workflow decision
  metrics with the command route module.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-086: Workflow action command routes were mixed with workflow state reads

- Date: 2026-05-31
- Scope: workflow action command routes by run id, correlation id, and idempotency key.
- Finding: mutating workflow action routes still lived in
  `src/api/routers/rebalance_runs_workflow_routes.py` next to read-only workflow state endpoints
  after decision and history extraction. Workflow commands own transition conflicts, reviewer
  traceability, and decision metrics, so keeping them mixed with state reads made route ownership
  and regression scope less explicit.
- Action: moved workflow action route registration and workflow decision metric recording into
  `src/api/routers/rebalance_runs_workflow_action_routes.py`, preserving public paths, response
  models, Swagger metadata, supportability and workflow feature gates, unsupported-query
  rejection, optional correlation-header behavior, disabled/not-found/conflict mapping, and metric
  outcomes.
- Status: hardened
- Evidence: focused DPM API workflow regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "workflow"`), focused Ruff checks, source-file
  mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review remaining workflow state routes and parent module composition for final
  supportability route ownership clarity.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-087: Workflow state routes were still owned by the composition shell

- Date: 2026-05-31
- Scope: read-only workflow state routes by run id, correlation id, and idempotency key.
- Finding: after extracting workflow decisions, history, and action commands,
  `src/api/routers/rebalance_runs_workflow_routes.py` still directly owned workflow state route
  handlers while also acting as the workflow route composition shell. That left one route family in
  a different ownership style from the rest of the workflow supportability surface.
- Action: moved workflow state route registration into
  `src/api/routers/rebalance_runs_workflow_state_routes.py` and reduced
  `rebalance_runs_workflow_routes.py` to explicit composition imports for state, action, and
  history route modules, preserving public paths, response models, Swagger metadata, feature
  gates, unsupported-query rejection, and not-found behavior.
- Status: hardened
- Evidence: focused DPM API workflow regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "workflow"`), focused Ruff checks, source-file
  mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review the supportability root composition module for service-factory and route-order
  readability once the async-operation module has the same ownership clarity.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-088: Async operation point lookups were mixed with list filtering

- Date: 2026-05-31
- Scope: async operation lookup routes by operation id and correlation id.
- Finding: `src/api/routers/rebalance_runs_operations_routes.py` owned both the query-heavy async
  operation list endpoint and point lookup endpoints. Lookup routes have simpler no-query
  contracts and not-found behavior, while the list endpoint owns pagination and filter validation,
  so keeping them together made review scope broader than necessary.
- Action: moved async operation point lookup route registration into
  `src/api/routers/rebalance_runs_async_operation_lookup_routes.py` and left the operations module
  to register the list endpoint plus the lookup module import, preserving public paths, response
  models, Swagger metadata, supportability and async-operation feature gates, and not-found
  behavior.
- Status: hardened
- Evidence: focused DPM API async-operation regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "async_operation"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split async operation list filtering into an explicit inventory route module so the
  operations shell mirrors the workflow route composition pattern.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-089: Async operation inventory route still lived in the operations shell

- Date: 2026-05-31
- Scope: async operation list route with creation-window, type, status, correlation, and cursor
  filters.
- Finding: after point lookup extraction, `src/api/routers/rebalance_runs_operations_routes.py`
  still directly owned the async operation list endpoint while also acting as the route composition
  shell. The list endpoint has the query-heavy filter and pagination contract, so keeping it in the
  shell left async-operation route ownership inconsistent with the workflow route pattern.
- Action: moved async operation list route registration into
  `src/api/routers/rebalance_runs_async_operation_inventory_routes.py` and reduced
  `rebalance_runs_operations_routes.py` to explicit composition imports for inventory and lookup
  route modules, preserving public path, response model, Swagger metadata, query filters,
  unsupported-query rejection, supportability and async-operation feature gates, and pagination
  behavior.
- Status: hardened
- Evidence: focused DPM API async-operation regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "async_operation"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review the supportability root module for naming and composition readability now that
  workflow and async-operation route families follow the same shell-plus-owned-module pattern.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-090: Support-bundle include flags were embedded in route handlers

- Date: 2026-05-31
- Scope: support-bundle include-flag query parameter contract.
- Finding: `src/api/routers/rebalance_runs_support_bundle_routes.py` owned the shared
  `include_artifact`, `include_async_operation`, and `include_idempotency_history` query parameter
  metadata inline with route handlers. That made the include-flag contract harder to reuse as
  support-bundle route ownership is split by resolver type.
- Action: moved the support-bundle allowed-query set and typed include-flag aliases into
  `src/api/routers/rebalance_runs_support_bundle_parameters.py`, preserving query names, defaults,
  Swagger metadata, unsupported-query rejection, and response behavior.
- Status: hardened
- Evidence: focused DPM API support-bundle regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "support_bundle"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split operation-resolved support-bundle lookup from direct run/correlation/idempotency
  support-bundle routes using the shared include-flag contract.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-091: Operation-resolved support bundle was mixed with run resolvers

- Date: 2026-05-31
- Scope: support-bundle lookup by asynchronous operation id.
- Finding: `src/api/routers/rebalance_runs_support_bundle_routes.py` mixed direct run,
  correlation, idempotency, and operation-id support-bundle resolvers in one module. The
  operation-id resolver follows the async-operation mapping path before reaching a run bundle, so
  it has a different supportability ownership boundary from direct run/key lookup routes.
- Action: moved the operation-id support-bundle route registration into
  `src/api/routers/rebalance_runs_support_bundle_operation_routes.py`, reusing the shared
  include-flag query parameter contract and preserving public path, response model, Swagger
  metadata, supportability and support-bundle feature gates, unsupported-query rejection, and
  not-found behavior.
- Status: hardened
- Evidence: focused DPM API support-bundle regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "support_bundle"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review whether direct support-bundle run, correlation, and idempotency resolvers
  should be split once remaining lookup route ownership is simplified.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-092: Idempotency support bundle was mixed with direct run resolvers

- Date: 2026-05-31
- Scope: support-bundle lookup by idempotency key.
- Finding: `src/api/routers/rebalance_runs_support_bundle_routes.py` still mixed the
  idempotency-key support-bundle resolver with direct run and correlation resolvers. The
  idempotency route resolves through retry-key mapping and can include idempotency history, so it
  has a distinct supportability contract from direct run/correlation bundle lookup.
- Action: moved idempotency-key support-bundle route registration into
  `src/api/routers/rebalance_runs_support_bundle_idempotency_routes.py`, reusing the shared
  include-flag query parameter contract and preserving public path, response model, Swagger
  metadata, supportability and support-bundle feature gates, unsupported-query rejection, and
  not-found behavior.
- Status: hardened
- Evidence: focused DPM API support-bundle regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "support_bundle"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split correlation-resolved support-bundle lookup from direct run support-bundle lookup
  so the remaining support-bundle shell has explicit resolver ownership.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-093: Correlation support bundle was mixed with direct run lookup

- Date: 2026-05-31
- Scope: support-bundle lookup by submitted run correlation id.
- Finding: `src/api/routers/rebalance_runs_support_bundle_routes.py` still owned both direct
  run-id support-bundle lookup and correlation-id support-bundle lookup. Correlation lookup is a
  trace-resolution support path used when the caller has the submitted correlation id rather than
  the persisted run id, so it benefits from separate route ownership and focused review scope.
- Action: moved correlation-id support-bundle route registration into
  `src/api/routers/rebalance_runs_support_bundle_correlation_routes.py`, reusing the shared
  include-flag query parameter contract and preserving public path, response model, Swagger
  metadata, supportability and support-bundle feature gates, unsupported-query rejection, and
  not-found behavior.
- Status: hardened
- Evidence: focused DPM API support-bundle regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "support_bundle"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: move the remaining direct run-id support-bundle route into its own module and leave
  the support-bundle shell responsible only for composition order.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-094: Direct run support bundle was still owned by the composition shell

- Date: 2026-05-31
- Scope: support-bundle lookup by run id.
- Finding: after operation, idempotency, and correlation support-bundle extraction,
  `src/api/routers/rebalance_runs_support_bundle_routes.py` still directly owned the run-id
  support-bundle endpoint while also acting as the support-bundle route composition shell. That
  left one resolver in a different ownership style from the rest of the support-bundle surface.
- Action: moved direct run-id support-bundle route registration into
  `src/api/routers/rebalance_runs_support_bundle_run_routes.py` and reduced the support-bundle
  shell to explicit composition imports for run, correlation, idempotency, and operation resolver
  modules, preserving public path, response model, Swagger metadata, supportability and
  support-bundle feature gates, unsupported-query rejection, include-flag behavior, and not-found
  mapping.
- Status: hardened
- Evidence: focused DPM API support-bundle regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "support_bundle"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review run lookup/idempotency lookup route ownership with the same resolver-boundary
  pattern used for support bundles.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-095: Idempotency history lookup was mixed with current run lookups

- Date: 2026-05-31
- Scope: append-only idempotency history route for retry/audit reconstruction.
- Finding: `src/api/routers/rebalance_runs_lookup_routes.py` mixed current run lookup routes with
  the append-only idempotency history route. The history route has a distinct feature gate and
  audit contract from current lookup by correlation, request hash, idempotency key, or run id.
- Action: moved idempotency history route registration into
  `src/api/routers/rebalance_runs_lookup_idempotency_history_routes.py`, preserving public path,
  response model, Swagger metadata, supportability and idempotency-history feature gates,
  unsupported-query rejection, and not-found behavior.
- Status: hardened
- Evidence: focused DPM API idempotency-history regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "idempotency_history"`), focused Ruff checks,
  source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split current idempotency-key lookup from correlation, request-hash, and run-id lookup
  routes so each resolver boundary has focused ownership.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-096: Current idempotency lookup was mixed with run lookup resolvers

- Date: 2026-05-31
- Scope: current idempotency-key to run mapping lookup route.
- Finding: `src/api/routers/rebalance_runs_lookup_routes.py` still mixed the current idempotency
  mapping route with correlation, request-hash, and direct run-id lookup routes. Current
  idempotency lookup is retry-token supportability behavior and has a distinct resolver boundary
  from trace, request-fingerprint, and run-id lookup.
- Action: moved current idempotency lookup route registration into
  `src/api/routers/rebalance_runs_lookup_idempotency_routes.py`, preserving public path, response
  model, Swagger metadata, supportability feature gate, unsupported-query rejection, and not-found
  behavior.
- Status: hardened
- Evidence: focused DPM API idempotency regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "idempotency"`), focused Ruff checks, source-file
  mypy, OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split request-hash lookup and direct run-id lookup from correlation lookup, preserving
  route registration order for specific lookup paths before the run-id catch-all route.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-097: Request-hash lookup was mixed with trace and run-id lookups

- Date: 2026-05-31
- Scope: latest run lookup by canonical request hash.
- Finding: `src/api/routers/rebalance_runs_lookup_routes.py` still mixed request-hash lookup with
  correlation and direct run-id lookup routes. Request-hash lookup supports retry/replay and
  fingerprint-based investigations, while correlation lookup supports trace resolution and run-id
  lookup is the direct persisted identifier path.
- Action: moved request-hash lookup route registration into
  `src/api/routers/rebalance_runs_lookup_request_hash_routes.py`, preserving public path, response
  model, Swagger metadata, supportability feature gate, unsupported-query rejection, URL-encoded
  hash path behavior, and not-found behavior.
- Status: hardened
- Evidence: focused DPM API request-hash/supportability regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "request_hash or supportability"`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split direct run-id lookup from correlation lookup and leave the lookup shell
  responsible only for specific-before-catch-all route composition.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-098: Direct run-id lookup was still owned by the lookup shell

- Date: 2026-05-31
- Scope: direct persisted run-id lookup route.
- Finding: after request-hash and idempotency lookup extraction,
  `src/api/routers/rebalance_runs_lookup_routes.py` still owned the direct run-id lookup route
  while also coordinating lookup route composition. The run-id route is the specific persisted
  identifier path and must remain registered after specific lookup paths to avoid catch-all
  ambiguity.
- Action: moved direct run-id lookup route registration into
  `src/api/routers/rebalance_runs_lookup_run_routes.py`, preserving public path, response model,
  Swagger metadata, supportability feature gate, unsupported-query rejection, not-found behavior,
  and specific-before-catch-all registration order.
- Status: hardened
- Evidence: focused DPM API supportability/run-list regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "supportability or support_runs_list"`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: move correlation-id lookup into its own module and reduce the lookup shell to
  explicit route composition only.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-099: Correlation lookup was still owned by the lookup composition shell

- Date: 2026-05-31
- Scope: latest run lookup by submitted correlation id.
- Finding: after request-hash, idempotency, idempotency-history, and run-id lookup extraction,
  `src/api/routers/rebalance_runs_lookup_routes.py` still directly owned the correlation lookup
  route while also acting as the lookup route composition shell. That left trace-resolution lookup
  in a different ownership style from the other lookup resolver families.
- Action: moved correlation-id lookup route registration into
  `src/api/routers/rebalance_runs_lookup_correlation_routes.py` and reduced the lookup shell to
  explicit composition imports in specific-before-catch-all order, preserving public path, response
  model, Swagger metadata, supportability feature gate, unsupported-query rejection, and not-found
  behavior.
- Status: hardened
- Evidence: focused DPM API supportability/idempotency regression selection
  (`tests/unit/dpm/api/test_api_rebalance.py -k "supportability or support_runs_list or idempotency"`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: review route composition shells for a shared readability pattern once this PR slice is
  raised and CI feedback is available.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-100: Outcome-review observability mapping was embedded in controller

- Date: 2026-05-31
- Scope: outcome-review supportability metric surfaces and state/reason mapping.
- Finding: `src/api/routers/outcome_reviews.py` owned supportability surface names and metric
  state/reason mapping inline with HTTP route handlers. That made controller code responsible for
  observability policy and increased the blast radius for the upcoming outcome-review route
  decomposition.
- Action: moved outcome-review supportability surface constants and metric state/reason mapping
  into `src/api/routers/outcome_review_observability.py`, preserving metric surface values,
  supportability states, reason labels, refresh/create/supportability behavior, and structured log
  fields.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split outcome-review command/read/supportability/handoff routes into owned modules
  now that shared observability policy is outside the controller.
- Wiki decision: no wiki source change required; this is internal controller modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-101: Outcome-review preview route was mixed with durable review routes

- Date: 2026-05-31
- Scope: non-durable outcome-review preview endpoint.
- Finding: `src/api/routers/outcome_reviews.py` mixed the read-only preview comparison endpoint
  with durable creation, source refresh, lookup, supportability, report, AI evidence, run lookup,
  and wave lookup routes. Preview has no persistence side effect and owns validation-only
  comparison behavior, so it should be reviewed separately from durable command paths.
- Action: moved preview route registration into
  `src/api/routers/outcome_review_preview_routes.py`, preserving public path, response model,
  Swagger guidance, validation error mapping, and source-owner truth boundary text.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split durable create and source-refresh command routes from read/supportability
  outcome-review routes.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-102: Outcome-review create command was mixed with read routes

- Date: 2026-05-31
- Scope: durable outcome-review creation endpoint.
- Finding: `src/api/routers/outcome_reviews.py` mixed immutable review creation with search,
  lookup, supportability, source refresh, report, AI evidence, run lookup, and wave lookup routes.
  Creation owns idempotency, conflict handling, persistence, correlation fallback, and
  supportability metric emission, so it should have a focused command-route owner.
- Action: moved create route registration into `src/api/routers/outcome_review_create_routes.py`,
  preserving public path, response model, Swagger guidance, idempotency header metadata,
  correlation-id behavior, validation and conflict error mapping, persistence dependency, and
  supportability metrics.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split source-refresh command handling from read/supportability/handoff routes.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-103: Outcome-review source refresh was mixed with read routes

- Date: 2026-05-31
- Scope: durable outcome-review source-refresh endpoint.
- Finding: `src/api/routers/outcome_reviews.py` mixed source refresh with search, lookup,
  supportability, report, AI evidence, run lookup, and wave lookup routes. Refresh appends
  source-refresh events, owns refreshed comparison validation, and emits not-found/supportability
  metrics, so it belongs in a command-specific route module.
- Action: moved source-refresh route registration into
  `src/api/routers/outcome_review_refresh_routes.py`, preserving public path, response model,
  Swagger guidance, repository dependency, validation and not-found error mapping, append-only
  refresh event behavior, and supportability metrics.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split read/search/supportability/report/AI handoff routes into owned modules.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-104: Outcome-review supportability diagnostics were mixed with reads

- Date: 2026-05-31
- Scope: outcome-review supportability endpoint, remediation routing, boundary projection, and
  structured diagnostics.
- Finding: `src/api/routers/outcome_reviews.py` mixed operator supportability diagnostics with
  plain search/lookup and downstream report/AI handoff routes. Supportability owns bounded
  diagnostic counts, remediation routes, external execution and client communication boundaries,
  supportability metrics, and structured logging, so it should be reviewed independently.
- Action: moved supportability route registration, response assembly, remediation route mapping,
  and structured diagnostic logging into
  `src/api/routers/outcome_review_supportability_routes.py`, preserving public path, response
  model, Swagger guidance, not-found mapping, supportability metrics, remediation route outputs,
  and boundary projections.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split downstream report/AI evidence handoff routes from remaining search and lookup
  routes.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-105: Outcome-review handoff routes were mixed with local reads

- Date: 2026-05-31
- Scope: downstream report input and AI evidence input routes.
- Finding: `src/api/routers/outcome_reviews.py` mixed downstream handoff routes for
  `lotus-report`/render/archive and `lotus-ai` consumers with local search and lookup routes.
  These handoff routes share proof-pack, wave, mandate, and outcome-review dependencies and expose
  bounded integration payloads rather than simple persisted review reads.
- Action: moved report-input and AI-evidence-input route registration into
  `src/api/routers/outcome_review_handoff_routes.py`, preserving public paths, response models,
  Swagger guidance, repository dependencies, not-found behavior, external execution boundary
  projection, client communication boundary projection, portfolio-memory context, and AI forbidden
  action payloads.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split outcome-review search, direct lookup, run lookup, and wave lookup into
  separately owned read modules.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-106: Outcome-review search was mixed with point lookups

- Date: 2026-05-31
- Scope: outcome-review search route with metadata, source-owner, source-type, and pagination
  filters.
- Finding: `src/api/routers/outcome_reviews.py` mixed query-heavy outcome-review search with
  direct lookup, run lookup, and wave lookup routes. Search owns bounded pagination, source-lineage
  scan limits, normalized source filters, applied-filter response shaping, and source owner/type
  facets, so it should be isolated from point lookup routes.
- Action: moved search route registration into `src/api/routers/outcome_review_search_routes.py`,
  preserving public path, response model, Swagger guidance, query parameter metadata, normalized
  filter behavior, applied-filter payloads, source owner/type counts, and source-owner boundary
  text.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split direct review lookup, run lookup, and wave lookup routes into owned modules.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-107: Direct outcome-review lookup was mixed with cross-resource lookups

- Date: 2026-05-31
- Scope: direct outcome-review lookup by outcome-review id.
- Finding: `src/api/routers/outcome_reviews.py` mixed direct persisted review lookup with run and
  wave lookup routes. Direct lookup is a simple manage-owned identifier read, while run and wave
  lookup routes are cross-resource views under different router prefixes.
- Action: moved direct outcome-review lookup route registration into
  `src/api/routers/outcome_review_lookup_routes.py`, preserving public path, response model,
  Swagger guidance, repository dependency, persisted-truth boundary text, and not-found behavior.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split run lookup and wave lookup routes from the remaining composition shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-108: Run outcome-review lookup was mixed with wave lookup

- Date: 2026-05-31
- Scope: run-scoped outcome-review lookup under `/rebalance/runs`.
- Finding: `src/api/routers/outcome_reviews.py` still mixed the run-scoped lookup route with the
  wave-scoped lookup route while also coordinating the base outcome-review router. The run lookup
  is a cross-resource view that connects RFC-0039/RFC-0040/RFC-0041 run evidence to RFC-0042
  closure truth and has different routing ownership than wave-level review lists.
- Action: moved run-scoped outcome-review lookup route registration into
  `src/api/routers/outcome_review_run_lookup_routes.py`, preserving public path, response model,
  Swagger guidance, repository dependency, first-review lookup behavior, and not-found mapping.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split wave outcome-review listing into its own route module and reduce
  `outcome_reviews.py` to router construction plus composition imports.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-109: Wave outcome-review listing was still owned by the router shell

- Date: 2026-05-31
- Scope: wave-scoped outcome-review listing under `/rebalance/waves`.
- Finding: after extracting base outcome-review routes and run lookup, `src/api/routers/outcome_reviews.py`
  still directly owned the wave-scoped outcome-review listing while also acting as router
  construction and composition. Wave lookup is a cross-resource list view with its own pagination
  and applied wave filter semantics.
- Action: moved wave-scoped outcome-review listing into
  `src/api/routers/outcome_review_wave_lookup_routes.py` and reduced `outcome_reviews.py` to router
  construction plus explicit composition imports, preserving public path, response model, Swagger
  guidance, pagination parameters, repository dependency, applied wave filter payload, and source
  owner/type facet behavior.
- Status: hardened
- Evidence: focused outcome-review API regression
  (`tests/unit/api/test_outcome_reviews_api.py`), focused Ruff checks, source-file mypy, OpenAPI
  quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review the next largest router for the same command/read/supportability route
  ownership pattern.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-110: Mandate API contracts were embedded in route handlers

- Date: 2026-05-31
- Scope: mandate API response examples and core-refresh request/response models.
- Finding: `src/api/routers/mandates.py` mixed OpenAPI examples and Pydantic contract models with
  read, refresh, and health route handlers. The refresh response contract owns serialization of
  compiled mandate twins, health snapshots, monitoring exceptions, and field-gap codes, so it
  should be independently reviewable from route registration.
- Action: moved the mandate response example and refresh request/response contracts into
  `src/api/routers/mandate_models.py`, preserving public schemas, Swagger examples, response
  serialization, and route behavior.
- Status: hardened
- Evidence: focused mandate API regression (`tests/unit/dpm/api/test_mandates_api.py`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: split mandate read, refresh, and health route registrations into separately owned
  modules.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-111: Mandate read routes were mixed with command handlers

- Date: 2026-05-31
- Scope: mandate latest-by-portfolio, latest-by-id, version history, and version diff routes.
- Finding: `src/api/routers/mandates.py` mixed read-only mandate state access with core refresh and
  health recalculation commands. The read routes are repository-backed persisted-state views with
  not-found and diff-unavailable mappings, while refresh and health routes own command semantics
  and downstream source dependencies.
- Action: moved read-only mandate route registration into
  `src/api/routers/mandate_read_routes.py`, preserving public paths, response models, Swagger
  guidance, examples, repository dependency wiring, not-found behavior, explicit-version diff
  behavior, and 409 mapping for unavailable diffs.
- Status: hardened
- Evidence: focused mandate API regression (`tests/unit/dpm/api/test_mandates_api.py`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: split core refresh and health route registrations from the remaining mandate router
  shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-112: Mandate core-refresh command was mixed with health routes

- Date: 2026-05-31
- Scope: `POST /api/v1/mandates/{mandate_id}/refresh-from-core`.
- Finding: the mandate router still coupled the lotus-core acquisition command with persisted
  health read/recalculate routes. The refresh route owns core resolver dependency injection,
  correlation propagation, source-unavailable and source-incomplete mappings, and source-backed
  response assembly, which is a distinct integration boundary from local health access.
- Action: moved core-refresh route registration into
  `src/api/routers/mandate_refresh_routes.py`, preserving public path, response model, Swagger
  guidance, response example, repository and core resolver dependencies, correlation forwarding,
  503 mapping for unavailable core sources, and 424 mapping for incomplete source products.
- Status: hardened
- Evidence: focused mandate API regression (`tests/unit/dpm/api/test_mandates_api.py`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: split mandate health read/recalculate routes from the remaining router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-113: Mandate health routes were still owned by the composition shell

- Date: 2026-05-31
- Scope: mandate health snapshot read and health recalculation routes.
- Finding: after moving mandate reads and core refresh, `src/api/routers/mandates.py` still owned
  health read/recalculate route handlers while also acting as the router composition shell. Health
  access owns persisted health state, explicit recalculation input validation, source analytics
  posture persistence, and 404/424 error mappings, so it should be reviewed independently from
  route composition.
- Action: moved health route registration into `src/api/routers/mandate_health_routes.py` and
  reduced `mandates.py` to router construction, the core resolver dependency hook, and explicit
  route-module imports. Public paths, response models, Swagger guidance, repository dependency
  wiring, health-not-found behavior, recalculation behavior, and source-incomplete mapping were
  preserved.
- Status: hardened
- Evidence: focused mandate API regression (`tests/unit/dpm/api/test_mandates_api.py`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: review the next largest router for the same composition-shell and route-family
  ownership pattern.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-114: Monitoring API contracts were embedded in route handlers

- Date: 2026-05-31
- Scope: monitoring run-once request, monitoring run page, monitoring exception page, and
  exception-resolution request models.
- Finding: `src/api/routers/monitoring.py` mixed Pydantic API contracts with command-center,
  run-once, monitoring-run lookup, and exception queue handlers. These models define public
  operator-facing payload shape and pagination semantics, so they should be reviewable separately
  from route orchestration logic.
- Action: moved monitoring API request/page contracts into
  `src/api/routers/monitoring_models.py`, preserving public schemas, Swagger field descriptions,
  examples, default portfolio-type behavior, pagination cursors, and exception resolution payload
  shape.
- Status: hardened
- Evidence: focused monitoring API regression (`tests/unit/dpm/api/test_monitoring_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split command-center, run-once, monitoring-run lookup, and exception queue route
  registrations into separately owned modules.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-115: Command-center summary was mixed with monitoring execution

- Date: 2026-05-31
- Scope: `GET /api/v1/dpm/command-center`.
- Finding: `src/api/routers/monitoring.py` mixed the command-center read model with monitoring
  run execution, run lookup, and exception queue mutations. The command-center route owns bounded
  PM/supervision summary filters, supportability posture, attention bucket limits, and Gateway /
  Workbench read-model semantics, so it should be reviewed independently from execution commands.
- Action: moved command-center route registration into
  `src/api/routers/monitoring_command_center_routes.py`, preserving public path, response model,
  Swagger guidance, query filters, health-state validation, active-exception limit bounds,
  repository dependency wiring, and supportability response behavior.
- Status: hardened
- Evidence: focused monitoring API regression (`tests/unit/dpm/api/test_monitoring_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split monitoring run-once execution, monitoring run lookup/listing, and exception
  queue routes into owned modules.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-116: Monitoring run reads were mixed with execution and exception queues

- Date: 2026-05-31
- Scope: monitoring run list and monitoring run detail endpoints.
- Finding: `src/api/routers/monitoring.py` mixed persisted monitoring-run search/detail reads with
  run-once execution and exception queue mutation. Run reads own bounded pagination, terminal
  status filtering, cursor handling, and run-not-found mapping, which are separate from source
  cohort resolution and exception resolution behavior.
- Action: moved monitoring-run read route registration into
  `src/api/routers/monitoring_run_read_routes.py`, preserving public paths, response models,
  Swagger guidance, status filter vocabulary, pagination bounds, repository dependency wiring,
  cursor response behavior, and 404 mapping for missing run ids.
- Status: hardened
- Evidence: focused monitoring API regression (`tests/unit/dpm/api/test_monitoring_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split exception queue routes and source-backed run-once execution from the remaining
  monitoring router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-117: Monitoring exception queue routes were mixed with run execution

- Date: 2026-05-31
- Scope: monitoring exception search and exception resolution endpoints.
- Finding: `src/api/routers/monitoring.py` still mixed operator exception queue reads and
  resolution mutations with source-backed monitoring run execution. Exception queues own
  mandate/portfolio/state filtering, bounded pagination, resolution reason capture, and 404
  mapping for missing exception ids, so they should be isolated from cohort resolution logic.
- Action: moved monitoring exception route registration into
  `src/api/routers/monitoring_exception_routes.py`, preserving public paths, response models,
  Swagger guidance, state filter vocabulary, pagination bounds, repository dependency wiring,
  cursor response behavior, resolution semantics, and missing-exception 404 mapping.
- Status: hardened
- Evidence: focused monitoring API regression (`tests/unit/dpm/api/test_monitoring_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split source-backed run-once execution from the remaining monitoring router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-118: Monitoring run-once execution was owned by the router shell

- Date: 2026-05-31
- Scope: `POST /api/v1/dpm/monitoring/run-once`.
- Finding: after extracting command-center, run-read, and exception queue routes,
  `src/api/routers/monitoring.py` still owned the source-backed run-once executor while also acting
  as the router composition shell. Run-once owns explicit mandate execution, PM-book cohort
  discovery through lotus-core, source supportability gating, source lineage filters, run
  persistence, and 422/424/503/404 mappings, so it should be independently reviewable.
- Action: moved run-once route registration into `src/api/routers/monitoring_run_once_routes.py`
  and reduced `monitoring.py` to router construction, the core resolver dependency hook, and
  explicit route-module imports. The existing `build_core_resolver_client` monkeypatch seam is
  preserved through `get_core_resolver_client`, and public path, response model, Swagger guidance,
  PM-book source filters, source-readiness handling, and error mappings were preserved.
- Status: hardened
- Evidence: focused monitoring API regression (`tests/unit/dpm/api/test_monitoring_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: review the next largest router or source-resolution module for route-family and
  integration-boundary ownership.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-119: Policy-pack route documentation constants hid route ownership

- Date: 2026-05-31
- Scope: policy-pack OpenAPI descriptions and response maps.
- Finding: `src/api/routers/rebalance_policy_packs.py` mixed long Swagger descriptions and
  response maps with policy-pack resolution, repository setup, catalog reads, and admin mutations.
  The documentation constants define the operator-facing supportability contract but do not own
  runtime behavior, so keeping them in the router made the route file harder to review.
- Action: moved policy-pack route descriptions and response maps into
  `src/api/routers/rebalance_policy_pack_docs.py`, preserving public OpenAPI text, status-code
  descriptions, unsupported query-parameter documentation, admin API disabled guidance, and all
  runtime exports from the original router module.
- Status: hardened
- Evidence: focused policy-pack API/config regression, focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split policy-pack catalog read routes and admin mutation routes while preserving the
  existing service/test import seams from `rebalance_policy_packs.py`.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-120: Effective policy-pack resolution route was mixed with catalog APIs

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/policies/effective`.
- Finding: `src/api/routers/rebalance_policy_packs.py` mixed effective policy-pack resolution with
  catalog reads, admin mutations, and repository setup. The effective route is a read-only
  supportability diagnostic over request, tenant, and global default precedence; it does not own
  catalog item retrieval or mutation.
- Action: moved effective policy-pack route registration into
  `src/api/routers/rebalance_policy_pack_effective_routes.py`, preserving public path, response
  model, Swagger guidance, request/tenant header metadata, query-parameter rejection,
  policy-resolution metric recording, and the existing resolver exports from
  `rebalance_policy_packs.py`.
- Status: hardened
- Evidence: focused policy-pack API/config regression, focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split catalog read routes and admin mutation routes while preserving existing
  repository/configuration import seams.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-121: Policy-pack catalog reads were mixed with admin mutations

- Date: 2026-05-31
- Scope: policy-pack catalog list and catalog item read endpoints.
- Finding: `src/api/routers/rebalance_policy_packs.py` mixed read-only catalog inspection with
  admin upsert/delete controls. Catalog reads own selected-policy context, repository-backed
  catalog listing, sorted response shape, item lookup, and not-found behavior, while admin routes
  own feature-gated mutation semantics.
- Action: moved catalog read route registration into
  `src/api/routers/rebalance_policy_pack_catalog_routes.py`, preserving public paths, response
  models, Swagger guidance, request/tenant header metadata, query-parameter rejection, resolution
  metric recording, sorted item order, selected-policy presence behavior, and missing-item 404
  mapping.
- Status: hardened
- Evidence: focused policy-pack API/config regression, focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split admin mutation routes from the remaining policy-pack router shell while
  preserving repository/configuration import seams.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-122: Policy-pack admin mutations were owned by helper module

- Date: 2026-05-31
- Scope: policy-pack upsert and delete admin endpoints.
- Finding: after extracting policy-pack documentation, effective resolution, and catalog reads,
  `src/api/routers/rebalance_policy_packs.py` still owned admin mutation routes while also
  carrying repository/configuration helper exports used by services and tests. Admin mutation
  routes have a distinct feature-gated control-plane boundary and should be reviewed separately.
- Action: moved policy-pack admin route registration into
  `src/api/routers/rebalance_policy_pack_admin_routes.py`, preserving public paths, response
  models, Swagger guidance, admin feature gating, query-parameter rejection, upsert payload
  projection, repository mutation behavior, delete behavior, and missing-item 404 mapping. The
  original module now retains router construction, route composition, and repository/configuration
  helpers for existing import seams.
- Status: hardened
- Evidence: focused policy-pack API/config regression, focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review whether repository/configuration helpers should move behind an explicit
  policy-pack dependency module once service/test import seams can be updated safely.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-123: Proof-pack API contracts were embedded in route handlers

- Date: 2026-05-31
- Scope: proof-pack OpenAPI example, generate request/response, and lookup response models.
- Finding: `src/api/routers/proof_packs.py` mixed public API contracts with proof-pack generation,
  lookup, Markdown, report-input, and AI-evidence-input route handlers. These contracts define
  source selection, idempotent generation options, governed regime-stress context, and handoff URL
  response shape, so they should be reviewable separately from route orchestration.
- Action: moved proof-pack API models and example payload into
  `src/api/routers/proof_pack_models.py`, preserving public schemas, Swagger descriptions,
  examples, default include flags, regime-stress authority text, and response URL fields.
- Status: hardened
- Evidence: focused proof-pack API regression (`tests/unit/dpm/api/test_proof_pack_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split proof-pack generation, lookup/Markdown, and downstream handoff input routes
  into separately owned modules.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-124: Proof-pack generation was mixed with read and handoff routes

- Date: 2026-05-31
- Scope: `POST /api/v1/rebalance/proof-packs`.
- Finding: `src/api/routers/proof_packs.py` mixed the idempotent proof-pack generation command
  with persisted proof-pack reads, Markdown rendering, and downstream report/AI handoff input
  routes. Generation owns source selection, required idempotency, rebalance-run versus selected
  alternative validation, source-backed regime-stress context, handoff reference materialization,
  and governed service exception mapping.
- Action: moved generation route registration and response URL assembly into
  `src/api/routers/proof_pack_generate_routes.py`, preserving public path, response model, Swagger
  guidance, idempotency and correlation headers, dependency wiring, request validation behavior,
  service calls, handoff-ref creation, URL fields, and HTTP exception mapping.
- Status: hardened
- Evidence: focused proof-pack API regression (`tests/unit/dpm/api/test_proof_pack_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split proof-pack lookup/Markdown and downstream handoff input routes from the
  remaining router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-125: Proof-pack reads were mixed with downstream handoff routes

- Date: 2026-05-31
- Scope: proof-pack persisted lookup and deterministic Markdown summary routes.
- Finding: after extracting proof-pack generation, `src/api/routers/proof_packs.py` still mixed
  basic persisted proof-pack reads with downstream report-input and AI-evidence-input routes. The
  lookup and Markdown routes own local proof-pack retrieval and deterministic human-readable
  rendering, while handoff routes own downstream payload assembly with wave, outcome, and mandate
  dependencies.
- Action: moved proof-pack lookup and Markdown route registration into
  `src/api/routers/proof_pack_read_routes.py`, preserving public paths, response model, Markdown
  response class, Swagger guidance, repository dependency wiring, deterministic renderer call, and
  proof-pack-not-found mapping.
- Status: hardened
- Evidence: focused proof-pack API regression (`tests/unit/dpm/api/test_proof_pack_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split report-input and AI-evidence-input handoff routes from the remaining router
  shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-126: Proof-pack handoff routes were still owned by the router shell

- Date: 2026-05-31
- Scope: proof-pack report-input and AI-evidence-input routes.
- Finding: after extracting proof-pack API models, generation, and local reads,
  `src/api/routers/proof_packs.py` still owned downstream handoff routes while also acting as the
  composition shell. Handoff routes require proof-pack, wave, outcome-review, and mandate
  repositories and expose deterministic payloads for `lotus-report` and `lotus-ai`, so they should
  be reviewed independently from local proof-pack reads.
- Action: moved report-input and AI-evidence-input route registration into
  `src/api/routers/proof_pack_handoff_routes.py` and reduced `proof_packs.py` to router
  construction plus explicit route-module imports. Public paths, response models, Swagger
  guidance, repository dependency wiring, handoff service calls, and proof-pack-not-found mapping
  were preserved.
- Status: hardened
- Evidence: focused proof-pack API regression (`tests/unit/dpm/api/test_proof_pack_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: review the next largest route surface for the same command/read/handoff ownership
  pattern.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-127: Portfolio-memory search was mixed with detail reads

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/portfolio-memory/search`.
- Finding: `src/api/routers/portfolio_memory.py` mixed search-index behavior with exact event
  lookup, detail timeline reads, and source repository dependency wiring. Search owns filter
  vocabulary guidance, supportability-state pattern validation, source-scan bounds, normalization,
  pagination, and validation-to-422 mapping; detail reads own a different bounded timeline
  contract.
- Action: moved portfolio-memory search route registration into
  `src/api/routers/portfolio_memory_search_routes.py`, preserving public path, response model,
  Swagger guidance, supported event/supportability descriptions, query bounds, repository-bundle
  dependency wiring, filter normalization, service call, and validation error mapping.
- Status: hardened
- Evidence: focused portfolio-memory API regression
  (`tests/unit/dpm/api/test_portfolio_memory_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split exact event lookup and detail timeline reads from the remaining
  portfolio-memory router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-128: Portfolio-memory event lookup was mixed with detail reads

- Date: 2026-05-31
- Scope: exact portfolio-memory event lookup route.
- Finding: after extracting search, `src/api/routers/portfolio_memory.py` still mixed exact event
  lookup with detail timeline assembly and source repository dependency wiring. Event lookup owns
  a distinct drill-down contract: bounded scan, exact event id matching, content-hash
  reconciliation, and a detailed not-found diagnostic that reports the scanned event count.
- Action: moved exact event lookup route registration into
  `src/api/routers/portfolio_memory_event_routes.py`, preserving public path, response model,
  Swagger guidance, path/query parameter metadata, source repository dependency wiring, support
  boundary text, lookup behavior, and 404 diagnostic shape.
- Status: hardened
- Evidence: focused portfolio-memory API regression
  (`tests/unit/dpm/api/test_portfolio_memory_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: split portfolio-memory detail timeline read from the remaining router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-129: Portfolio-memory detail read was owned by the dependency shell

- Date: 2026-05-31
- Scope: source-backed portfolio-memory detail timeline route.
- Finding: after extracting search and exact event lookup, `src/api/routers/portfolio_memory.py`
  still owned the detail timeline route while also carrying source repository dependency wiring.
  The detail route owns bounded timeline assembly, portfolio path metadata, and the source-backed
  memory contract, while the remaining module should only construct the router and dependency
  bundle used across route modules.
- Action: moved detail timeline route registration into
  `src/api/routers/portfolio_memory_detail_routes.py` and reduced `portfolio_memory.py` to router
  construction, source repository dependency wiring, and explicit route-module imports. Public
  path, response model, Swagger guidance, limit bounds, repository-bundle dependency wiring, and
  service call were preserved.
- Status: hardened
- Evidence: focused portfolio-memory API regression
  (`tests/unit/dpm/api/test_portfolio_memory_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review the next large route surface for route-family decomposition after checking
  branch commit count against the PR target.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-130: Construction request contracts were embedded in route handlers

- Date: 2026-05-31
- Scope: construction alternative-set API request contracts and Swagger example payload.
- Finding: `src/api/routers/construction.py` mixed route registration with generated alternative
  set request contracts, selection request contracts, stateful/stateless envelope conversion, and
  OpenAPI example payloads. These models are shared by the generate and selection route families
  and should remain independently reviewable from handler orchestration.
- Action: moved construction request models and the alternative-set example payload into
  `src/api/routers/construction_models.py`, preserving field names, defaults, examples,
  descriptions, envelope conversion behavior, and imported domain vocabularies.
- Status: hardened
- Evidence: focused construction API regression (`tests/unit/dpm/api/test_construction_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split construction generate, read, and selection route handlers into bounded route
  modules while preserving the parent router import used by `src/api/main.py`.
- Wiki decision: no wiki source change required; this is internal router/model modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-131: Construction generate orchestration was mixed with read routes

- Date: 2026-05-31
- Scope: `POST /api/v1/construction/alternative-sets/generate`.
- Finding: the construction router still mixed the generate command path with alternative-set read
  and selection routes. Generation owns idempotency replay, stateful/stateless rebalance-envelope
  resolution, optional risk-authority enrichment, run-support persistence, and source-context error
  mapping; read and selection handlers have narrower repository-only contracts.
- Action: moved the generate route registration and handler into
  `src/api/routers/construction_generate_routes.py`, preserving public path, response model,
  Swagger guidance, idempotency and correlation headers, database/session dependency wiring,
  source-resolution call, risk-authority and run-support dependencies, service arguments, and API
  exception mapping.
- Status: hardened
- Evidence: focused construction API regression (`tests/unit/dpm/api/test_construction_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split construction read and selection handlers from the remaining router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-132: Construction read lookup was mixed with selection commands

- Date: 2026-05-31
- Scope: `GET /api/v1/construction/alternative-sets/{alternative_set_id}`.
- Finding: after extracting generation, the construction router still mixed the persisted
  alternative-set read model with selection command behavior. The read route owns a repository-only
  lookup and audit/presentation Swagger contract, while selection owns PM decision capture and
  explicit selection error translation.
- Action: moved the alternative-set read route registration into
  `src/api/routers/construction_read_routes.py`, preserving public path, response model, Swagger
  description, example payload, path metadata, repository dependency, service call, and exception
  mapping.
- Status: hardened
- Evidence: focused construction API regression (`tests/unit/dpm/api/test_construction_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: split construction selection command from the remaining router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-133: Construction selection command was owned by the router shell

- Date: 2026-05-31
- Scope: `POST /api/v1/construction/alternative-sets/{alternative_set_id}/selections`.
- Finding: after extracting generate and read routes, `src/api/routers/construction.py` still
  owned the alternative-selection command while also acting as the route registration shell. The
  selection command owns PM decision capture, bounded reason/comment request semantics,
  correlation propagation, and explicit API error translation.
- Action: moved construction selection route registration into
  `src/api/routers/construction_selection_routes.py` and reduced `construction.py` to router
  construction plus explicit route-module imports. Public path, response model, Swagger guidance,
  path/header metadata, repository dependency, service call arguments, and HTTP error mapping were
  preserved.
- Status: hardened
- Evidence: focused construction API regression (`tests/unit/dpm/api/test_construction_api.py`),
  focused Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory
  validation with no drift.
- Follow-up: review the next large route or service surface after checking branch commit count
  against the PR target.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-134: PM operating-quality builders were embedded in router assembly

- Date: 2026-05-31
- Scope: PM operating-quality score-run and review-action builder helpers.
- Finding: `src/api/routers/pm_operating_quality.py` mixed router assembly with score-run
  construction, PM-book source evidence materialization, policy resolution, book-scope signal
  projection, and review-action target lookup. The route shell should coordinate route modules,
  while builder behavior should be isolated for focused review and testing.
- Action: moved builder internals into `src/api/routers/pm_operating_quality_builders.py` while
  keeping the existing private names on `pm_operating_quality.py` as compatibility wrappers for
  tests and monkeypatch seams. Route registration order, public API paths, PM-book resolver
  injection, policy lookup semantics, source-reference projection, review-action construction, and
  error mapping were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: review PM operating-quality route registration order and remaining model surface after
  this behavior-preserving builder split.
- Wiki decision: no wiki source change required; this is internal builder modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-135: Integration capability schemas were embedded in route code

- Date: 2026-05-31
- Scope: `GET /api/v1/integration/capabilities` response schemas and OpenAPI examples.
- Finding: `src/api/routers/integration_capabilities.py` mixed the gateway-facing capability route
  with contract schemas, consumer vocabulary, and a long OpenAPI example payload. This made the
  runtime feature-resolution logic harder to review separately from the published control-plane
  contract.
- Action: moved the consumer type alias, feature/workflow/response models, and capabilities
  response examples into `src/api/routers/integration_capabilities_models.py`, preserving schema
  names, field descriptions, examples, supported consumer literals, and OpenAPI example content.
- Status: hardened
- Evidence: focused integration-capabilities API regression
  (`tests/unit/dpm/api/test_integration_capabilities_api.py` plus health contract checks), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: review the remaining integration-capabilities runtime helpers for a similarly bounded
  feature-resolution extraction.
- Wiki decision: no wiki source change required; this is internal schema modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-136: Integration capability feature resolution lived in the route module

- Date: 2026-05-31
- Scope: integration-capabilities environment and feature-resolution helpers.
- Finding: after extracting schemas, `src/api/routers/integration_capabilities.py` still mixed the
  HTTP route with environment parsing, stateful publishability checks, supported input-mode
  ordering, feature capability assembly, workflow assembly, and response construction. This
  control-plane logic is cross-app contract-sensitive and should be reviewable without scanning
  FastAPI route metadata.
- Action: moved feature-resolution builders into
  `src/api/routers/integration_capabilities_builders.py` while retaining compatibility wrapper
  names in `integration_capabilities.py`. The route still owns query validation and solver
  dependency injection so existing tests and monkeypatch seams remain intact.
- Status: hardened
- Evidence: focused integration-capabilities API regression
  (`tests/unit/dpm/api/test_integration_capabilities_api.py` plus health contract checks), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: monitor neighboring `lotus-gateway` and `lotus-core` capability/source-contract
  refactors for consumer vocabulary or stateful resolver posture changes.
- Wiki decision: no wiki source change required; this is internal builder modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-137: Single-run rebalance simulation was mixed with batch analysis

- Date: 2026-05-31
- Scope: `POST /api/v1/rebalance/simulate`.
- Finding: `src/api/routers/rebalance_simulation.py` mixed the single-run simulation command with
  synchronous batch analysis, asynchronous batch submission, and async operation execution. The
  single-run command owns idempotency-key semantics, policy-pack override headers, stateful/source
  envelope resolution, and the simulation response examples.
- Action: moved the single-run simulation route registration into
  `src/api/routers/rebalance_simulation_simulate_routes.py`, preserving public path, response
  model, Swagger guidance, header metadata, example payloads, database dependency, source-envelope
  resolution, service call arguments, and route registration order.
- Status: hardened
- Evidence: focused rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: split synchronous and asynchronous batch-analysis routes from the remaining router
  shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-138: Synchronous batch analysis was mixed with async execution routes

- Date: 2026-05-31
- Scope: `POST /api/v1/rebalance/analyze`.
- Finding: after extracting single-run simulation, the rebalance simulation router still mixed
  immediate batch analysis with asynchronous batch acceptance and manual operation execution.
  Synchronous analysis owns immediate batch result semantics, scenario-order execution, batch
  response examples, and policy-pack header propagation.
- Action: moved synchronous batch-analysis route registration into
  `src/api/routers/rebalance_simulation_analyze_routes.py`, preserving public path, response model,
  Swagger guidance, header metadata, request field metadata, source-envelope resolution, service
  call arguments, compatibility import from `src/api/main.py`, and route registration order.
- Status: hardened
- Evidence: focused rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: split asynchronous batch acceptance and manual operation execution from the remaining
  router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-139: Async batch acceptance was mixed with manual execution

- Date: 2026-05-31
- Scope: `POST /api/v1/rebalance/analyze/async`.
- Finding: after extracting simulation and synchronous analysis routes, the rebalance simulation
  router still mixed async batch acceptance with manual pending-operation execution. Async
  acceptance owns `202 Accepted`, polling-handle semantics, correlation response headers,
  conflict examples, and policy-pack header propagation for deferred scenario analysis.
- Action: moved asynchronous batch-analysis route registration into
  `src/api/routers/rebalance_simulation_async_routes.py`, preserving public path, response model,
  Swagger guidance, `X-Correlation-Id` response header, header metadata, request field metadata,
  source-envelope resolution, service call arguments, compatibility import from `src/api/main.py`,
  and route registration order.
- Status: hardened
- Evidence: focused rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: split manual pending-operation execution from the remaining router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-140: Manual async operation execution was owned by the route shell

- Date: 2026-05-31
- Scope: `POST /api/v1/rebalance/operations/{operation_id}/execute`.
- Finding: after extracting simulation, synchronous analysis, and async acceptance, the rebalance
  simulation router still owned manual pending-operation execution while also acting as the route
  registration shell. Manual execution owns run-support service dependency wiring, pending-state
  execution semantics, and terminal operation status response mapping.
- Action: moved manual async operation execution route registration into
  `src/api/routers/rebalance_simulation_operation_routes.py` and reduced
  `rebalance_simulation.py` to router construction plus explicit route-module imports and
  compatibility handler re-exports used by `src/api/main.py`. Public path, response model, Swagger
  guidance, path metadata, service dependency, service call, and route order were preserved.
- Status: hardened
- Evidence: focused rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`), focused
  Ruff checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with
  no drift.
- Follow-up: review the next large route surface after checking branch commit count against the PR
  target.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-141: Campaign definition materialization was mixed with source discovery

- Date: 2026-05-31
- Scope: persisted bulk-review campaign definition request materialization.
- Finding: `src/api/routers/wave_campaign_source_resolution.py` mixed persisted campaign-definition
  materialization with live Core DPM portfolio-universe discovery and membership/governance
  source-resolution logic. Persisted definitions own a separate fail-closed contract: reference
  completeness, status eligibility, as-of-date parity, candidate projection, and governance
  hydration.
- Action: moved persisted campaign-definition request materialization into
  `src/api/routers/wave_campaign_definition_resolution.py`, preserving validation codes/messages,
  source-reference construction, candidate projection, governance hydration, and the wave portfolio
  resolution call path through an explicit direct import.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split Core DPM portfolio-universe discovery and campaign membership governance from
  the remaining source-resolution module.
- Wiki decision: no wiki source change required; this is internal source-resolution modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-142: Core DPM universe discovery was mixed with campaign membership

- Date: 2026-05-31
- Scope: Core DPM portfolio-universe candidate discovery for bulk-review campaign waves.
- Finding: `src/api/routers/wave_campaign_source_resolution.py` still mixed live Core
  portfolio-universe paging and source-readiness guards with Manage-owned campaign membership
  hashing and governance projection. Core discovery owns upstream availability mapping,
  non-terminating page protection, truncated-page rejection, duplicate candidate detection, and
  Core source-reference construction.
- Action: moved Core DPM portfolio-universe discovery into
  `src/api/routers/wave_core_portfolio_universe_resolution.py`, preserving page bounds,
  supportability checks, error codes/messages, candidate deduplication, source refs, and the
  campaign membership call path.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split campaign membership governance projection from the remaining source-resolution
  module.
- Wiki decision: no wiki source change required; this is internal source-resolution modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-143: Campaign governance projection was mixed with membership assembly

- Date: 2026-05-31
- Scope: bulk-review campaign governance diagnostics and source-reference projection.
- Finding: after extracting persisted definitions and Core candidate discovery,
  `src/api/routers/wave_campaign_source_resolution.py` still mixed campaign governance validation
  and source-reference projection with membership selection and membership hashing. Governance owns
  approval posture, expiry posture, actor entitlement posture, governance hashing, and governance
  lineage projection.
- Action: moved campaign governance projection into
  `src/api/routers/wave_campaign_governance_resolution.py`, preserving not-supplied diagnostics,
  approval/expiry/entitlement calculations, governance hash inputs, source refs, and membership
  assembly behavior.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: review the remaining wave campaign source-resolution module for smaller membership
  assembly seams or move to the next large wave route surface.
- Wiki decision: no wiki source change required; this is internal source-resolution modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-144: Campaign discovery read model was mixed with queue projections

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/waves/campaign-discovery`.
- Finding: `src/api/routers/wave_campaign_read_model_routes.py` mixed persisted campaign discovery
  with operating queue, approval inbox, workflow board, assignment plan, and automation readiness
  projections. Discovery owns a narrower read model: persisted definition lookup, active-on
  filtering, expired-row filtering, and universe-posture discovery item construction.
- Action: moved campaign discovery route registration into
  `src/api/routers/wave_campaign_discovery_routes.py` and included it before the remaining
  read-model routes, preserving public path, response model, Swagger guidance, query parameters,
  repository dependency, query loading, filtering behavior, and route order.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split the operating queue and attention/workflow projections from the remaining
  campaign read-model router.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-145: Campaign operating queue was mixed with attention projections

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/waves/campaign-operating-queue`.
- Finding: after extracting campaign discovery, the campaign read-model router still mixed the
  operating queue with approval inbox, workflow board, assignment plan, and automation readiness.
  The operating queue owns launch-ready versus attention posture over persisted definitions,
  requested-as-of/actor context, active-on filtering, and expired-row inclusion.
- Action: moved the operating queue route registration into
  `src/api/routers/wave_campaign_operating_queue_routes.py` and included it after discovery,
  preserving public path, response model, Swagger guidance, query parameters, repository
  dependency, read-model query loading, page builder arguments, and route order.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split approval inbox and workflow-board projections from the remaining campaign
  read-model router.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-146: Campaign approval inbox was mixed with workflow projections

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/waves/campaign-approval-inbox`.
- Finding: after extracting discovery and operating queue routes, the campaign read-model router
  still mixed approval attention inbox behavior with workflow board, assignment plan, and
  automation readiness. Approval inbox owns approval-complete/required/incomplete, expiry
  attention, entitlement attention, closed-row inclusion, and optional inbox-status filtering.
- Action: moved the approval inbox route registration into
  `src/api/routers/wave_campaign_approval_inbox_routes.py` and included it after operating queue,
  preserving public path, response model, Swagger guidance, query parameters, repository
  dependency, read-model query loading, page builder arguments, and route order.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split workflow-board and assignment projections from the remaining campaign read-model
  router.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-147: Campaign workflow board was mixed with assignment projections

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/waves/campaign-workflow-board`.
- Finding: after extracting discovery, operating queue, and approval inbox routes, the campaign
  read-model router still mixed workflow-board behavior with assignment plan and automation
  readiness. The workflow board owns cross-actor next-action rows, board-status filtering,
  next-action filtering, and closed-row inclusion over persisted definitions.
- Action: moved workflow-board route registration into
  `src/api/routers/wave_campaign_workflow_board_routes.py` and included it after approval inbox,
  preserving public path, response model, Swagger guidance, query parameters, repository
  dependency, read-model query loading, page builder arguments, and route order.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split assignment plan and automation readiness from the remaining campaign read-model
  router.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-148: Campaign assignment plan was mixed with automation readiness

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/waves/campaign-assignment-plan`.
- Finding: after extracting workflow-board routing, the campaign read-model router still mixed
  assignment planning with automation readiness. Assignment planning owns assigned-actor,
  escalation-tier, SLA posture, next-action filtering, closed-row inclusion, and reason-code
  projection derived from workflow-board posture.
- Action: moved assignment-plan route registration into
  `src/api/routers/wave_campaign_assignment_plan_routes.py` and included it after workflow board,
  preserving public path, response model, Swagger guidance, query parameters, repository
  dependency, read-model query loading, page builder arguments, and route order.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split automation readiness from the remaining campaign read-model router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-149: Campaign automation readiness was owned by the read-model shell

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/waves/campaign-workflow-automation`.
- Finding: after extracting discovery, queue, approval inbox, workflow board, and assignment plan,
  `src/api/routers/wave_campaign_read_model_routes.py` still owned automation readiness while also
  acting as the read-model router aggregator. Automation readiness owns Manage-side assignment-task
  proposal posture, automation-status/action filtering, external workflow orchestration boundary
  wording, and capability-posture publication.
- Action: moved automation-readiness route registration into
  `src/api/routers/wave_campaign_workflow_automation_routes.py` and reduced
  `wave_campaign_read_model_routes.py` to a pure subrouter aggregator. Public path, response
  model, Swagger guidance, query parameters, repository dependency, read-model query loading, page
  builder arguments, capability-posture contract, and route order were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: prepare the ~50-commit branch for PR gate validation.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-150: Campaign evidence mixed approval decisions with task controls

- Date: 2026-05-31
- Scope:
  `POST/GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions`.
- Finding: `src/api/routers/wave_campaign_evidence_routes.py` mixed approval-decision evidence
  with assignment-action, assignment-task, and maker-checker control routes. Approval decisions own
  append-only approval evidence and read-page posture, while the remaining routes own separate
  assignment workflow and maker-checker control lifecycles.
- Action: moved approval-decision route registration into
  `src/api/routers/wave_campaign_approval_decision_evidence_routes.py` and included it first from
  `wave_campaign_evidence_routes.py`, preserving public paths, response models, Swagger guidance,
  repository dependency wiring, response helper calls, and route order.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split assignment-action evidence from the remaining campaign evidence router.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-151: Campaign evidence mixed assignment actions with task state

- Date: 2026-05-31
- Scope:
  `POST/GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions`.
- Finding: after extracting approval-decision evidence, the campaign evidence router still mixed
  assignment-action append-only evidence with assignment-task state transitions and maker-checker
  control evidence. Assignment actions own assignment/escalation posture history and bounded page
  projection, while task and maker-checker routes own separate mutable-control lifecycles.
- Action: moved assignment-action route registration into
  `src/api/routers/wave_campaign_assignment_action_evidence_routes.py` and included it after
  approval-decision evidence from `wave_campaign_evidence_routes.py`, preserving public paths,
  response models, Swagger guidance, repository dependency wiring, response helper calls, and
  route order.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split assignment-task lifecycle evidence from the remaining campaign evidence router.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-152: Campaign evidence mixed assignment task lifecycle with controls

- Date: 2026-05-31
- Scope:
  `POST/GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`
  and
  `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions`.
- Finding: after extracting approval-decision and assignment-action evidence, the campaign
  evidence router still mixed mutable assignment-task lifecycle routing with maker-checker control
  evidence. Assignment tasks own controlled open/transition state, task-status filtering, and SLA
  posture paging, while maker-checker controls own separate approval-control evidence.
- Action: moved assignment-task route registration into
  `src/api/routers/wave_campaign_assignment_task_evidence_routes.py` and included it after
  assignment-action evidence from `wave_campaign_evidence_routes.py`, preserving public paths,
  response models, Swagger guidance, status filtering, repository dependency wiring, response
  helper calls, and route order.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split maker-checker controls from the remaining campaign evidence router shell.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-153: Campaign maker-checker controls were owned by the evidence shell

- Date: 2026-05-31
- Scope:
  `POST/GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls`.
- Finding: after extracting approval-decision, assignment-action, and assignment-task routes,
  `src/api/routers/wave_campaign_evidence_routes.py` still owned maker-checker control endpoints
  while also acting as the campaign evidence router aggregator. Maker-checker controls own
  append-only control evidence and distinct submitter/reviewer posture; the shell should only
  compose evidence subrouters.
- Action: moved maker-checker control route registration into
  `src/api/routers/wave_campaign_maker_checker_evidence_routes.py` and reduced
  `wave_campaign_evidence_routes.py` to a pure aggregator over approval-decision,
  assignment-action, assignment-task, and maker-checker evidence subrouters. Public paths, response
  models, Swagger guidance, repository dependency wiring, response helper calls, and route order
  were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect the next largest wave router seam after campaign evidence routing is fully
  modularized.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-154: PM quality summary route owned invocation construction

- Date: 2026-05-31
- Scope: `POST /api/v1/rebalance/pm-operating-quality/summary-invocations/preview` and
  `POST /api/v1/rebalance/pm-operating-quality/summary-invocations`.
- Finding: `src/api/routers/pm_operating_quality_summary_routes.py` mixed controller handlers with
  summary-invocation construction orchestration, including score-run/review-action lookup,
  domain-builder calls, correlation-id fallback, and HTTP error mapping. That made the route module
  harder to review as a controller and concentrated service-boundary behavior in endpoint code.
- Action: moved summary-invocation construction and HTTP exception mapping into
  `src/api/routers/pm_operating_quality_summary_invocation_builder.py`, leaving preview/create
  endpoints to compose dependencies, call the route-support builder, persist on create, and return
  response DTOs. Public paths, request/response models, correlation-id behavior, not-found details,
  validation error mapping, and conflict handling were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: inspect remaining PM operating-quality route modules for repeated controller-owned
  lookup/build/persist orchestration.
- Wiki decision: no wiki source change required; this is internal controller modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-155: PM quality summary route mixed command and read endpoints

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/pm-operating-quality/summary-invocations` and
  `GET /api/v1/rebalance/pm-operating-quality/summary-invocations/{summary_invocation_id}`.
- Finding: after extracting summary-invocation construction, the summary route still mixed
  preview/create command endpoints with persisted read endpoints. The read side owns bounded query
  filters, pagination, immutable lookup, and not-found mapping, while preview/create own
  review-gated invocation construction and persistence.
- Action: moved summary-invocation list/get route registration into
  `src/api/routers/pm_operating_quality_summary_read_routes.py` and included it after preview/create
  commands from `pm_operating_quality_summary_routes.py`. Public paths, response models, Swagger
  guidance, query parameters, pagination bounds, repository dependency wiring, not-found details,
  and route order were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: inspect PM operating-quality score-run and review-action route modules for the same
  command/read split pattern.
- Wiki decision: no wiki source change required; this is internal controller modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-156: PM quality review-action routes mixed command and read registration

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/pm-operating-quality/review-actions` and
  `GET /api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}`.
- Finding: `src/api/routers/pm_operating_quality_review_action_routes.py` registered preview/create
  command endpoints and persisted read endpoints in one module. Review-action reads own bounded
  target/policy/date/state filters, pagination, immutable lookup, and not-found mapping, while the
  command side owns review-action construction and conflict-safe persistence.
- Action: moved review-action list/get route registration into
  `src/api/routers/pm_operating_quality_review_action_read_routes.py` and kept
  `register_pm_quality_review_action_routes` as the stable parent registration entry point. Public
  paths, response models, Swagger guidance, query parameters, pagination bounds, repository
  dependency wiring, not-found details, and route order were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: inspect whether PM operating-quality score-run read registration should be moved to a
  dedicated module for consistency with review-action and summary read routing.
- Wiki decision: no wiki source change required; this is internal controller modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-157: PM quality score-run reads lived in the command module

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/pm-operating-quality/score-runs` and
  `GET /api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}`.
- Finding: score-run command and read registration were already separated by function, but both
  lived in `src/api/routers/pm_operating_quality_score_run_routes.py`. That left the command module
  carrying read-side query filters, pagination, immutable lookup, and not-found mapping even after
  review-action and summary reads were split into dedicated modules.
- Action: moved score-run list/get route registration into
  `src/api/routers/pm_operating_quality_score_run_read_routes.py` while keeping
  `register_pm_quality_score_run_read_routes` import-compatible from the existing command module.
  Public paths, response models, Swagger guidance, query parameters, pagination bounds, repository
  dependency wiring, not-found details, and route order were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: inspect PM operating-quality fairness routes for command/read separation and
  controller-owned orchestration.
- Wiki decision: no wiki source change required; this is internal controller modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-158: PM quality fairness route mixed command and read endpoints

- Date: 2026-05-31
- Scope: `GET /api/v1/rebalance/pm-operating-quality/fairness-analyses` and
  `GET /api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}`.
- Finding: `src/api/routers/pm_operating_quality_fairness_routes.py` mixed preview/create command
  endpoints, persisted read endpoints, and fairness-analysis construction. The read side owns
  policy/date/state filters, pagination, immutable lookup, and not-found mapping, while preview and
  create own cross-segment command construction and conflict-safe persistence.
- Action: moved fairness-analysis list/get route registration into
  `src/api/routers/pm_operating_quality_fairness_read_routes.py` and included it after the
  preview/create routes from `pm_operating_quality_fairness_routes.py`. Public paths, response
  models, Swagger guidance, query parameters, pagination bounds, repository dependency wiring,
  not-found details, and route order were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: extract fairness-analysis command construction from the remaining fairness command
  route module.
- Wiki decision: no wiki source change required; this is internal controller modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-159: PM quality fairness route owned command construction

- Date: 2026-05-31
- Scope: `POST /api/v1/rebalance/pm-operating-quality/fairness-analyses/preview` and
  `POST /api/v1/rebalance/pm-operating-quality/fairness-analyses`.
- Finding: after splitting fairness-analysis reads, the fairness command route still owned
  cross-segment command construction and service-error-to-HTTP mapping. That kept request-to-command
  transformation, correlation-id fallback, service invocation, and error status selection inside
  endpoint code rather than a route-support boundary.
- Action: moved fairness-analysis command construction and HTTP exception mapping into
  `src/api/routers/pm_operating_quality_fairness_builder.py`, leaving preview/create endpoints to
  compose dependencies, call the builder, persist on create, and return response DTOs. Public
  paths, request/response models, correlation-id behavior, not-found mapping for missing score
  runs, validation error mapping, and conflict handling were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: inspect remaining PM operating-quality parent router private wrappers for stale
  compatibility shims that can be reduced without breaking tests.
- Wiki decision: no wiki source change required; this is internal controller modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-160: PM quality builders mixed score-run assembly with Core book sourcing

- Date: 2026-05-31
- Scope: PM operating-quality score-run construction with optional `pm_book_scope`.
- Finding: `src/api/routers/pm_operating_quality_builders.py` mixed score-run assembly and
  review-action assembly with Core PM-book membership sourcing. The PM-book scope path owns
  Core resolver invocation, unavailable/incomplete source mapping, source-ready validation, empty
  membership fail-closed behavior, source refs, bounded member projection, and conversion into a
  `SOURCE_QUALITY` evidence signal.
- Action: moved PM-book scope sourcing and signal conversion into
  `src/api/routers/pm_operating_quality_book_scope_builder.py` while keeping the existing
  `pm_operating_quality_builders` import surface intact for parent-router compatibility and tests.
  Public routes, request/response models, failure status codes/details, source refs, member limits,
  reason codes, and correlation-id behavior were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: inspect whether policy resolution should be split from score-run assembly once PM-book
  sourcing is stable in its own module.
- Wiki decision: no wiki source change required; this is internal builder modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-161: PM quality policy resolution lived inside score-run builders

- Date: 2026-05-31
- Scope: PM operating-quality score-run policy resolution.
- Finding: after separating Core PM-book sourcing, `pm_operating_quality_builders.py` still owned
  policy reference resolution. Policy resolution has its own contract: prefer inline bank-owned
  policy when supplied, require both `policy_id` and `policy_version` for repository lookup, return
  governed 422 for missing references, and return governed 404 for unknown policy versions.
- Action: moved policy resolution into
  `src/api/routers/pm_operating_quality_policy_resolution.py` while keeping the existing
  `pm_operating_quality_builders.resolve_policy` import surface intact for parent-router
  compatibility and tests. Public routes, request/response models, error status codes/details, and
  score-run construction behavior were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: continue reducing `pm_operating_quality_builders.py` toward score-run and review-action
  orchestration only.
- Wiki decision: no wiki source change required; this is internal builder modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-162: PM quality builders mixed score-run and review-action assembly

- Date: 2026-05-31
- Scope: PM operating-quality review-action construction.
- Finding: after separating PM-book sourcing and policy resolution,
  `pm_operating_quality_builders.py` still mixed score-run construction with review-action target
  lookup, fairness/score-run not-found mapping, review-action builder invocation, correlation-id
  fallback, and validation error mapping.
- Action: moved review-action construction into
  `src/api/routers/pm_operating_quality_review_action_builder.py` while keeping the existing
  `pm_operating_quality_builders.build_review_action` import surface intact for parent-router
  compatibility and tests. Public routes, request/response models, target lookup semantics,
  not-found details, validation mapping, and correlation-id behavior were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: reduce `pm_operating_quality_builders.py` to a score-run builder compatibility module
  or move score-run construction into a dedicated module.
- Wiki decision: no wiki source change required; this is internal builder modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-163: PM quality score-run construction owned the compatibility builder

- Date: 2026-05-31
- Scope: PM operating-quality score-run construction.
- Finding: after extracting review-action construction, `pm_operating_quality_builders.py` still
  owned score-run assembly directly. That left outcome-review lookup, policy resolution,
  optional PM-book scope enrichment, evidence aggregation, domain score-run builder invocation,
  correlation-id fallback, and validation error mapping in the compatibility module.
- Action: moved score-run construction into
  `src/api/routers/pm_operating_quality_score_run_builder.py` and reduced
  `pm_operating_quality_builders.py` to a compatibility re-export module for score-run,
  review-action, PM-book scope, and policy helper imports used by the parent router and tests.
  Public routes, request/response models, outcome-review not-found behavior, policy/PM-book
  enrichment, validation mapping, and correlation-id behavior were preserved.
- Status: hardened
- Evidence: focused PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, source-file mypy,
  OpenAPI quality gate, and API vocabulary inventory validation with no drift.
- Follow-up: inspect larger wave route helper modules after PM operating-quality builders are split.
- Wiki decision: no wiki source change required; this is internal builder modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-164: Campaign action HTTP mixed approval evidence with other evidence helpers

- Date: 2026-05-31
- Scope:
  `POST/GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions`.
- Finding: after campaign evidence routes were split, `wave_campaign_action_http.py` still mixed
  approval-decision response helpers with assignment-action, assignment-task, and maker-checker
  response helpers. Approval decisions own append-only approval mutation, approval page projection,
  conflict/value HTTP mapping, and persisted-definition not-found handling.
- Action: moved approval-decision HTTP response helpers into
  `src/api/routers/wave_campaign_approval_decision_http.py`, moved persisted-definition not-found
  handling into `src/api/routers/wave_campaign_action_common.py`, and kept
  `wave_campaign_action_http.py` as a compatibility import surface for existing evidence route
  modules. Public paths, request/response models, repository calls, conflict/value/not-found
  mappings, and route behavior were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split assignment-action, assignment-task, and maker-checker HTTP helpers from the
  remaining campaign action compatibility module.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-165: Campaign action HTTP mixed assignment-action helpers with task lifecycle helpers

- Date: 2026-05-31
- Scope:
  `POST/GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions`.
- Finding: `wave_campaign_action_http.py` still owned assignment-action append/projection helpers
  alongside assignment-task lifecycle and maker-checker control helpers. That kept separate evidence
  families in one module after the route families had already been split.
- Action: moved assignment-action HTTP response helpers into
  `src/api/routers/wave_campaign_assignment_action_http.py`, updated the assignment-action evidence
  route to import the focused helper module directly, and kept `wave_campaign_action_http.py` as a
  compatibility import surface for existing callers. Public paths, request/response models,
  repository calls, conflict/value/not-found mappings, and route behavior were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split assignment-task and maker-checker HTTP helpers from the remaining campaign action
  compatibility module.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-166: Campaign action HTTP mixed assignment-task lifecycle with maker-checker controls

- Date: 2026-05-31
- Scope:
  `POST/GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`
  and `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions`.
- Finding: `wave_campaign_action_http.py` still owned assignment-task open, transition, and list
  helpers alongside maker-checker controls. That blurred task lifecycle response construction with
  a separate control evidence family.
- Action: moved assignment-task HTTP response helpers into
  `src/api/routers/wave_campaign_assignment_task_http.py`, updated the assignment-task evidence
  route to import the focused helper module directly, and kept `wave_campaign_action_http.py` as a
  compatibility import surface for existing callers. Public paths, request/response models,
  repository calls, conflict/value/not-found mappings, status filtering, and route behavior were
  preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split maker-checker HTTP helpers from the remaining campaign action compatibility
  module.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-167: Campaign action HTTP compatibility module still owned maker-checker helpers

- Date: 2026-05-31
- Scope:
  `POST/GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls`.
- Finding: after approval-decision, assignment-action, and assignment-task helpers were extracted,
  `wave_campaign_action_http.py` still owned maker-checker control response helpers. That prevented
  the legacy action helper module from becoming a pure compatibility surface.
- Action: moved maker-checker HTTP response helpers into
  `src/api/routers/wave_campaign_maker_checker_http.py`, updated the maker-checker evidence route
  to import the focused helper module directly, and reduced `wave_campaign_action_http.py` to
  compatibility re-exports for existing callers. Public paths, request/response models, repository
  calls, conflict/value/not-found mappings, control pagination, and route behavior were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect whether remaining compatibility imports can be retired after downstream callers
  have moved to the focused helper modules.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-168: Approval-decision route still depended on campaign action compatibility imports

- Date: 2026-05-31
- Scope:
  `src/api/routers/wave_campaign_approval_decision_evidence_routes.py` helper imports.
- Finding: after the approval-decision HTTP helpers were extracted, the approval-decision evidence
  route still imported them through `wave_campaign_action_http.py`. That kept a local route coupled
  to a compatibility module instead of the focused helper boundary.
- Action: updated the approval-decision evidence route to import
  `src/api/routers/wave_campaign_approval_decision_http.py` directly. The action compatibility
  module remains available for existing external/internal callers that have not moved yet.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: keep `wave_campaign_action_http.py` as compatibility-only unless a later cleanup can
  prove no downstream import consumers remain.
- Wiki decision: no wiki source change required; this is internal import-boundary cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-169: Campaign definition HTTP mixed response orchestration with reusable error mapping

- Date: 2026-05-31
- Scope: `src/api/routers/wave_campaign_definition_http.py` HTTP error/date mapping helpers.
- Finding: campaign-definition response orchestration lived in the same module as reusable HTTP
  exception builders and campaign discovery date parsing. Downstream campaign helpers imported that
  module for error mapping even when they did not need definition response orchestration.
- Action: moved reusable campaign-definition HTTP exception builders and discovery date parsing into
  `src/api/routers/wave_campaign_definition_errors.py`, kept `wave_campaign_definition_http.py`
  import-compatible for existing callers, and moved focused helper tests to the new boundary.
  Not-found, conflict, validation, lifecycle, launch-blocked, and discovery-date behavior were
  preserved.
- Status: hardened
- Evidence: focused campaign-definition helper tests
  (`tests/unit/api/test_wave_campaign_definition_http.py`), focused waves API regression
  (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff checks, source-file mypy, OpenAPI quality
  gate, and API vocabulary inventory validation with no drift.
- Follow-up: move downstream helper imports from `wave_campaign_definition_http.py` to the focused
  error module when touching those modules for adjacent work.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-170: Campaign action helpers depended on definition response module for error mapping

- Date: 2026-05-31
- Scope:
  `src/api/routers/wave_campaign_*_http.py` action/evidence helper imports for campaign-definition
  error mapping.
- Finding: the extracted approval-decision, assignment-action, assignment-task, maker-checker, and
  shared action helpers still imported reusable campaign-definition error builders through
  `wave_campaign_definition_http.py`. That kept action evidence helpers coupled to definition
  response orchestration after the reusable mapping boundary had been extracted.
- Action: moved action/evidence helper imports for conflict, validation, and not-found mapping to
  `src/api/routers/wave_campaign_definition_errors.py` while keeping
  `get_campaign_definition_or_404()` sourced from `wave_campaign_definition_http.py`. Route behavior,
  status codes, and response payloads were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: apply the same direct error-module import pattern to launch/read helpers when touching
  those modules for adjacent work.
- Wiki decision: no wiki source change required; this is internal import-boundary cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-171: Campaign launch/read helpers imported error mapping through definition responses

- Date: 2026-05-31
- Scope:
  `src/api/routers/wave_campaign_launch_http.py`, `src/api/routers/wave_campaign_read_http.py`, and
  `src/api/routers/wave_campaign_read_model_query.py`.
- Finding: launch and read-model helpers still imported campaign-definition conflict,
  launch-blocked, and discovery-date parsing through `wave_campaign_definition_http.py`. That kept
  read/launch helpers coupled to definition response orchestration for reusable mapping utilities.
- Action: moved those imports to `src/api/routers/wave_campaign_definition_errors.py` while keeping
  `get_campaign_definition_or_404()` sourced from the definition response helper. Launch error
  mapping, discovery-date validation, read-model query behavior, and route contracts were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: keep `wave_campaign_definition_http.py` as the definition response/lookup helper
  boundary and use `wave_campaign_definition_errors.py` for reusable HTTP mapping in new helpers.
- Wiki decision: no wiki source change required; this is internal import-boundary cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-172: Campaign definition response helper mixed create/read with lifecycle commands

- Date: 2026-05-31
- Scope:
  `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/retire`
  and
  `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede`.
- Finding: `wave_campaign_definition_http.py` still owned retire and supersede response
  orchestration alongside definition create/list/get helpers. The lifecycle commands have distinct
  validation, lifecycle-error mapping, and audit semantics from definition persistence and reads.
- Action: moved retire/supersede response helpers into
  `src/api/routers/wave_campaign_definition_lifecycle_http.py`, updated the definition route to
  import lifecycle helpers directly, and kept `wave_campaign_definition_http.py` import-compatible
  for existing callers. Public paths, request/response models, lifecycle status mapping,
  not-found/conflict/value mapping, and route behavior were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect whether definition create/list/get helpers should be split into write and read
  modules after lifecycle extraction has stabilized.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-173: Campaign definition helper mixed write construction with read lookup and listing

- Date: 2026-05-31
- Scope:
  `PUT/GET /api/v1/rebalance/waves/campaign-definitions` helper boundaries and shared definition
  lookup imports.
- Finding: `wave_campaign_definition_http.py` still mixed definition write construction with read
  lookup/list pagination and also served as the lookup import point for downstream campaign helpers.
  That made unrelated action, launch, and read helpers depend on a compatibility module instead of a
  focused definition lookup boundary.
- Action: moved definition lookup/get/list helpers into
  `src/api/routers/wave_campaign_definition_read_http.py`, moved PUT response construction into
  `src/api/routers/wave_campaign_definition_write_http.py`, updated routes and downstream helpers
  to import the focused modules directly, and kept `wave_campaign_definition_http.py`
  import-compatible. Public paths, request/response models, not-found/conflict/value mapping,
  pagination count behavior, and route contracts were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: keep `wave_campaign_definition_http.py` as compatibility-only unless a later cleanup
  proves all downstream imports have moved and external import compatibility can be retired.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-174: Campaign read helper mixed audit projections with readiness projections

- Date: 2026-05-31
- Scope:
  `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/lifecycle-events`
  and
  `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-history`.
- Finding: `wave_campaign_read_http.py` owned simple audit projections alongside workflow overview,
  preview readiness, and launch-package projections. Lifecycle events and launch history have a
  distinct append-only audit/read-model purpose from readiness and launch packaging.
- Action: moved lifecycle-event and launch-history response helpers into
  `src/api/routers/wave_campaign_audit_read_http.py`, updated readiness routes to import audit
  helpers directly, and kept `wave_campaign_read_http.py` import-compatible for existing callers.
  Public paths, response models, pagination, not-found mapping, and route behavior were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split workflow overview/readiness/launch-package helpers into a focused readiness
  projection module after audit read extraction is stable.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-175: Campaign read compatibility module still owned readiness projections

- Date: 2026-05-31
- Scope:
  `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview`,
  `/preview-readiness`, and `/launch-package`.
- Finding: after audit read extraction, `wave_campaign_read_http.py` still owned workflow overview,
  preview readiness, and launch-package response helpers. These helpers compose fail-closed launch
  supportability and operator package projections, which is a separate concern from audit read
  projection and compatibility re-exports.
- Action: moved readiness/launch-package response helpers into
  `src/api/routers/wave_campaign_readiness_projection_http.py`, updated readiness routes to import
  the focused projection module directly, and reduced `wave_campaign_read_http.py` to compatibility
  re-exports. Public paths, response models, date validation, not-found mapping, launch-history
  bounds, launch-package inclusion, and route behavior were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect remaining compatibility-only modules for local route imports before retiring
  any compatibility surface.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-176: Campaign readiness router mixed audit endpoints with readiness endpoints

- Date: 2026-05-31
- Scope:
  campaign-definition audit endpoints under `/lifecycle-events` and `/launch-history` in
  `src/api/routers/wave_campaign_readiness_routes.py`.
- Finding: after audit/readiness helper extraction, the route module still combined append-only
  audit read endpoints with workflow overview, preview-readiness, and launch-package endpoints.
  This kept route ownership less clear even though the helper boundaries were already separated.
- Action: moved lifecycle-events and launch-history endpoints into
  `src/api/routers/wave_campaign_audit_read_routes.py`, included that router before readiness
  routes from `waves.py`, and left `wave_campaign_readiness_routes.py` focused on readiness and
  launch-package projections. Public paths, response models, route order, pagination, dependency
  wiring, Swagger descriptions, and route behavior were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect whether campaign-definition route modules should be grouped under a higher-level
  route aggregator once compatibility-only helper modules are stable.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-177: Campaign definition routes mixed lifecycle commands with create/read routes

- Date: 2026-05-31
- Scope:
  `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/retire`
  and
  `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede`.
- Finding: `wave_campaign_definition_routes.py` still mixed lifecycle command endpoints with
  definition create/list/get endpoints after the lifecycle response helper had already been
  separated. That kept route ownership broader than the underlying helper boundary.
- Action: moved retire and supersede endpoints into
  `src/api/routers/wave_campaign_definition_lifecycle_routes.py` and included that router
  immediately after the campaign definition create/list router in `waves.py`. Public paths,
  response models, route order, dependency wiring, Swagger descriptions, and lifecycle behavior were
  preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect whether definition detail/read routing should be grouped under a campaign
  definition route aggregator once the remaining route modules are stable.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-178: Campaign readiness router mixed workflow overview with readiness endpoints

- Date: 2026-05-31
- Scope:
  `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview`.
- Finding: `wave_campaign_readiness_routes.py` still combined the workflow overview route with
  preview-readiness and launch-package endpoints. Workflow overview composes audit, readiness, and
  optional launch-package posture for operators, while the remaining readiness routes expose direct
  supportability and package projections.
- Action: moved the workflow-overview endpoint into
  `src/api/routers/wave_campaign_workflow_overview_routes.py`, included that router before the
  readiness router in `waves.py`, and left `wave_campaign_readiness_routes.py` focused on
  preview-readiness and launch-package endpoints. Public path, response model, query parameters,
  route order, dependency wiring, Swagger description, and behavior were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect whether preview-readiness and launch-package routes should remain together or
  split once launch-package projection ownership is stable.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-179: Campaign readiness router mixed preview readiness with launch package routing

- Date: 2026-05-31
- Scope:
  `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package`.
- Finding: after workflow-overview route extraction, `wave_campaign_readiness_routes.py` still mixed
  direct preview-readiness checks with launch-package routing. Launch package is operator packaging
  for a future create request with idempotency/correlation guidance, while preview-readiness is the
  direct fail-closed supportability check.
- Action: moved the launch-package endpoint into
  `src/api/routers/wave_campaign_launch_package_routes.py`, included that router after
  preview-readiness routes and before durable launch routes in `waves.py`, and left
  `wave_campaign_readiness_routes.py` focused on preview-readiness. Public path, response model,
  query parameters, route order, dependency wiring, Swagger description, and behavior were
  preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect route aggregation once campaign-definition read/write/lifecycle/audit/readiness
  routing has stabilized.
- Wiki decision: no wiki source change required; this is internal route modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-180: Campaign readiness projection helper mixed workflow overview with direct readiness projections

- Date: 2026-05-31
- Scope:
  `src/api/routers/wave_campaign_readiness_projection_http.py` workflow-overview response helper.
- Finding: after workflow-overview routing was split, the projection helper still lived with direct
  preview-readiness and launch-package projection helpers. Workflow overview composes readiness,
  lifecycle audit, launch-history, active-on filtering, and optional launch-package posture, which is
  broader than direct readiness/package construction.
- Action: moved workflow-overview response construction into
  `src/api/routers/wave_campaign_workflow_overview_http.py`, updated the workflow-overview route to
  import the focused helper directly, and kept `wave_campaign_readiness_projection_http.py`
  import-compatible for existing callers. Public behavior, date validation, not-found mapping,
  launch-history bounds, launch-package inclusion, and response shape were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: split launch-package projection from preview-readiness projection if future route or
  helper work touches that boundary.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260531-181: Campaign readiness projection helper mixed launch package with preview readiness

- Date: 2026-05-31
- Scope:
  `src/api/routers/wave_campaign_readiness_projection_http.py` launch-package response helper.
- Finding: after launch-package route extraction, launch-package response construction still lived
  in the preview-readiness projection helper module. Launch package builds operator create-request
  guidance with idempotency and correlation metadata, while preview readiness is the direct
  fail-closed supportability check.
- Action: moved launch-package response construction into
  `src/api/routers/wave_campaign_launch_package_http.py`, updated the launch-package route to import
  that focused helper directly, and kept `wave_campaign_readiness_projection_http.py`
  import-compatible for existing callers. Public behavior, not-found mapping, requested as-of date,
  actor, correlation, and response shape were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: keep `wave_campaign_readiness_projection_http.py` as preview-readiness plus
  compatibility re-exports unless a future cleanup can safely retire compatibility imports.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-182: Campaign readiness projection compatibility module still owned preview readiness

- Date: 2026-06-01
- Scope:
  `src/api/routers/wave_campaign_readiness_projection_http.py` preview-readiness response helper.
- Finding: after workflow-overview and launch-package helper extraction, the readiness projection
  module still owned preview-readiness response construction while also acting as a compatibility
  re-export surface. That left the direct fail-closed supportability check in a compatibility module.
- Action: moved preview-readiness response construction into
  `src/api/routers/wave_campaign_preview_readiness_http.py`, updated the preview-readiness route to
  import the focused helper directly, and reduced `wave_campaign_readiness_projection_http.py` to
  compatibility re-exports. Public behavior, not-found mapping, requested as-of date, optional
  actor entitlement input, and response shape were preserved.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), focused Ruff
  checks, source-file mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: inspect compatibility-only campaign helper modules for safe retirement only after local
  route imports and downstream callers are proven migrated.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-183: Campaign read compatibility helpers had no internal callers

- Date: 2026-06-01
- Scope:
  `src/api/routers/wave_campaign_read_http.py` and
  `src/api/routers/wave_campaign_readiness_projection_http.py`.
- Finding: after campaign audit, workflow-overview, preview-readiness, and launch-package helpers
  were split and routes imported focused modules directly, the legacy read/readiness projection
  helper modules only re-exported focused helpers and had no internal callers. Keeping them made the
  route helper surface larger without preserving any active application path.
- Action: removed the unused compatibility helper modules. Public routes, response models,
  OpenAPI output, and focused helper ownership were preserved because all route modules already
  import the focused audit/readiness/launch-package helpers directly.
- Status: hardened
- Evidence: focused waves API regression (`tests/unit/dpm/api/test_waves_api.py`), router-wide Ruff
  checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation with no
  drift.
- Follow-up: continue retiring compatibility-only modules only after repository-local import scans
  prove no active callers remain.
- Wiki decision: no wiki source change required; this is internal dead compatibility module cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-184: Campaign action compatibility helper had no internal callers

- Date: 2026-06-01
- Scope: `src/api/routers/wave_campaign_action_http.py`.
- Finding: after assignment-action, assignment-task, maker-checker, and approval-decision helpers
  were split and routes imported focused modules directly, the action helper only re-exported those
  focused helpers and had no repository-local callers.
- Action: removed the unused compatibility helper module. Public routes, response models, OpenAPI
  output, and focused action helper ownership were preserved because all route modules already
  import the focused helpers directly.
- Status: hardened
- Evidence: repository-local import scan found no active callers; focused waves API regression
  (`tests/unit/dpm/api/test_waves_api.py`), router-wide Ruff checks, router-wide mypy, OpenAPI
  quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: continue retiring compatibility-only modules only after repository-local import scans
  prove no active callers remain.
- Wiki decision: no wiki source change required; this is internal dead compatibility module cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-185: Campaign definition compatibility helper had no internal callers

- Date: 2026-06-01
- Scope: `src/api/routers/wave_campaign_definition_http.py`.
- Finding: after definition read, write, error, and lifecycle helpers were split and routes imported
  focused modules directly, the definition helper only re-exported those focused helpers and had no
  repository-local callers.
- Action: removed the unused compatibility helper module. Public routes, response models, OpenAPI
  output, validation-error mapping, not-found mapping, conflict mapping, and focused definition
  helper ownership were preserved because all route modules already import the focused helpers
  directly.
- Status: hardened
- Evidence: repository-local import scan found no active callers; focused waves API regression
  (`tests/unit/dpm/api/test_waves_api.py`), router-wide Ruff checks, router-wide mypy, OpenAPI
  quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: continue retiring compatibility-only modules only after repository-local import scans
  prove no active callers remain.
- Wiki decision: no wiki source change required; this is internal dead compatibility module cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-186: PM operating quality compatibility builder had one parent-router caller

- Date: 2026-06-01
- Scope:
  `src/api/routers/pm_operating_quality.py` and
  `src/api/routers/pm_operating_quality_builders.py`.
- Finding: after PM quality score-run, review-action, policy-resolution, and PM-book scope builders
  were split, the compatibility builder only re-exported focused helpers. The only active
  repository-local caller was the parent PM operating quality router, which kept the router coupled
  to an obsolete import surface.
- Action: updated the parent router to import focused helper modules directly and removed the
  unused compatibility builder. Public routes, request/response models, private edge helpers,
  repository wiring, OpenAPI output, and PM-book fail-closed behavior were preserved.
- Status: hardened
- Evidence: repository-local import scan found no active callers; PM operating quality API
  regression (`tests/unit/api/test_pm_operating_quality_api.py`), router-wide Ruff checks,
  router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation passed with no
  drift.
- Follow-up: continue removing compatibility-only router modules only after route and test imports
  are proven migrated.
- Wiki decision: no wiki source change required; this is internal helper import cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-187: Rebalance operations composition route only imported leaf routes

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs.py` and
  `src/api/routers/rebalance_runs_operations_routes.py`.
- Finding: after async operation inventory and lookup routes were split, the operations composition
  module only imported those two leaf route modules. Keeping the extra import layer made parent
  router registration less direct without owning behavior.
- Action: registered the async operation inventory and lookup leaf routes directly from the parent
  rebalance run router and removed the obsolete composition module. Public paths, route ordering,
  response models, OpenAPI output, feature gates, and query-parameter rejection behavior were
  preserved.
- Status: hardened
- Evidence: repository-local import scan found no active callers; DPM rebalance API regression
  (`tests/unit/dpm/api/test_api_rebalance.py`), router-wide Ruff checks, router-wide mypy, OpenAPI
  quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: inspect remaining composition-only rebalance run route modules for the same safe
  direct-registration cleanup.
- Wiki decision: no wiki source change required; this is internal route registration cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-188: Rebalance support-bundle composition route only imported leaf routes

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs.py` and
  `src/api/routers/rebalance_runs_support_bundle_routes.py`.
- Finding: after support-bundle run, correlation, idempotency, and operation routes were split, the
  support-bundle composition module only imported those leaf route modules. Keeping the extra import
  layer made parent router registration less direct without owning behavior.
- Action: registered support-bundle leaf routes directly from the parent rebalance run router and
  removed the obsolete composition module. Public paths, route ordering, response models, OpenAPI
  output, feature gates, and lookup semantics were preserved.
- Status: hardened
- Evidence: repository-local import scan found no active callers; DPM rebalance API regression
  (`tests/unit/dpm/api/test_api_rebalance.py`), router-wide Ruff checks, router-wide mypy, OpenAPI
  quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: inspect remaining composition-only rebalance run route modules for the same safe
  direct-registration cleanup.
- Wiki decision: no wiki source change required; this is internal route registration cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-189: Rebalance workflow composition route only imported leaf routes

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs.py` and
  `src/api/routers/rebalance_runs_workflow_routes.py`.
- Finding: after workflow state, action, and history routes were split, the workflow composition
  module only imported those leaf route modules. Keeping the extra import layer made parent router
  registration less direct without owning behavior.
- Action: registered workflow leaf routes directly from the parent rebalance run router and removed
  the obsolete composition module. Public paths, route ordering, response models, OpenAPI output,
  workflow feature gates, and action/history semantics were preserved.
- Status: hardened
- Evidence: repository-local import scan found no active callers; DPM rebalance API regression
  (`tests/unit/dpm/api/test_api_rebalance.py`), router-wide Ruff checks, router-wide mypy, OpenAPI
  quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: inspect remaining composition-only rebalance run route modules for the same safe
  direct-registration cleanup.
- Wiki decision: no wiki source change required; this is internal route registration cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-190: Rebalance lookup composition route only imported leaf routes

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs.py` and
  `src/api/routers/rebalance_runs_lookup_routes.py`.
- Finding: after correlation, request-hash, idempotency, idempotency-history, and run-id lookup
  routes were split, the lookup composition module only imported those leaf route modules. Keeping
  the extra import layer made parent router registration less direct without owning behavior.
- Action: registered lookup leaf routes directly from the parent rebalance run router and removed
  the obsolete composition module. Public paths, route ordering, response models, OpenAPI output,
  feature gates, and lookup semantics were preserved.
- Status: hardened
- Evidence: repository-local import scan found no active callers; DPM rebalance API regression
  (`tests/unit/dpm/api/test_api_rebalance.py`), router-wide Ruff checks, router-wide mypy, OpenAPI
  quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: keep rebalance run route registration direct unless a composition module owns real
  behavior or reusable route grouping.
- Wiki decision: no wiki source change required; this is internal route registration cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-191: Wave campaign evidence composition route only included leaf routers

- Date: 2026-06-01
- Scope:
  `src/api/routers/waves.py` and `src/api/routers/wave_campaign_evidence_routes.py`.
- Finding: after approval-decision, assignment-action, assignment-task, and maker-checker evidence
  routes were split, the campaign evidence route module only grouped those leaf routers. Keeping an
  extra aggregator made the campaign route registration less direct without owning behavior.
- Action: registered campaign evidence leaf routers directly from the parent wave router and
  removed the obsolete aggregation module. Public paths, route ordering, response models, OpenAPI
  output, evidence persistence semantics, and maker-checker behavior were preserved.
- Status: hardened
- Evidence: repository-local import scan found no active callers; focused waves API regression
  (`tests/unit/dpm/api/test_waves_api.py`), router-wide Ruff checks, router-wide mypy, OpenAPI
  quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: keep wave campaign route registration direct unless a grouping module owns real
  behavior or reusable route policy.
- Wiki decision: no wiki source change required; this is internal route registration cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-192: Rebalance run parent router repeated route-module imports

- Date: 2026-06-01
- Scope: `src/api/routers/rebalance_runs.py`.
- Finding: after removing composition-only route modules, the rebalance run parent router had a
  long block of repeated `importlib.import_module()` calls. That made registration order harder to
  scan and created copy/paste friction for future route slices.
- Action: centralized the route module names in one ordered tuple and registered them through a
  single loop. Public paths, route ordering, response models, OpenAPI output, feature gates, and
  supportability behavior were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: use ordered route-module inventories for parent routers when dynamic registration is
  still the safest pattern.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-193: Outcome review parent router repeated route-module imports

- Date: 2026-06-01
- Scope: `src/api/routers/outcome_reviews.py`.
- Finding: the outcome review parent router registered primary outcome-review routes and cross-link
  run/wave lookup routes through repeated `importlib.import_module()` calls. That made route order
  harder to scan and increased copy/paste friction for future outcome-review route slices.
- Action: centralized primary route module names and cross-link route module names in ordered
  tuples and registered each group through a single loop after its owning parent router was
  initialized. Public paths, route ordering, response models, OpenAPI output, lookup prefixes,
  supportability behavior, and handoff behavior were preserved.
- Status: hardened
- Evidence: outcome review API regression (`tests/unit/api/test_outcome_reviews_api.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: use ordered route-module inventories for parent routers when dynamic registration is
  still the safest pattern.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-194: Proof-pack parent router repeated route-module imports

- Date: 2026-06-01
- Scope: `src/api/routers/proof_packs.py`.
- Finding: the proof-pack parent router registered generate, read, and handoff routes through
  repeated `importlib.import_module()` calls. That made route order less explicit as an inventory
  and created copy/paste friction for future proof-pack slices.
- Action: centralized proof-pack route module names in one ordered tuple and registered them through
  a single loop. Public paths, route ordering, response models, OpenAPI output, proof-pack
  generation, read, and handoff behavior were preserved.
- Status: hardened
- Evidence: proof-pack API regression (`tests/unit/dpm/api/test_proof_pack_api.py`), router-wide
  Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation
  passed with no drift.
- Follow-up: use ordered route-module inventories for parent routers when dynamic registration is
  still the safest pattern.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-195: Construction parent router repeated route-module imports

- Date: 2026-06-01
- Scope: `src/api/routers/construction.py`.
- Finding: the construction parent router registered generate, read, and selection routes through
  repeated `importlib.import_module()` calls. That made route order less explicit as an inventory
  and created copy/paste friction for future construction route slices.
- Action: centralized construction route module names in one ordered tuple and registered them
  through a single loop. Public paths, route ordering, response models, OpenAPI output,
  construction alternative generation, read, and selection behavior were preserved.
- Status: hardened
- Evidence: construction API regression (`tests/unit/dpm/api/test_construction_api.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: use ordered route-module inventories for parent routers when dynamic registration is
  still the safest pattern.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-196: Mandate parent router repeated route-module imports

- Date: 2026-06-01
- Scope: `src/api/routers/mandates.py`.
- Finding: the mandate parent router registered read, refresh, and health routes through repeated
  `importlib.import_module()` calls. That made route order less explicit as an inventory and
  created copy/paste friction for future mandate route slices.
- Action: centralized mandate route module names in one ordered tuple and registered them through a
  single loop. Public paths, route ordering, response models, OpenAPI output, core resolver
  dependency flow, mandate read, refresh, and health behavior were preserved.
- Status: hardened
- Evidence: mandate API regression (`tests/unit/dpm/api/test_mandates_api.py`), router-wide Ruff
  checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation passed
  with no drift.
- Follow-up: use ordered route-module inventories for parent routers when dynamic registration is
  still the safest pattern.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-197: Monitoring parent router repeated route-module imports

- Date: 2026-06-01
- Scope: `src/api/routers/monitoring.py`.
- Finding: the monitoring parent router registered command-center, run-once, run-read, and
  exception routes through repeated `importlib.import_module()` calls. That made route order less
  explicit as an inventory and created copy/paste friction for future monitoring route slices.
- Action: centralized monitoring route module names in one ordered tuple and registered them
  through a single loop. Public paths, route ordering, response models, OpenAPI output, core
  resolver dependency flow, command-center, monitoring run, and exception behavior were preserved.
- Status: hardened
- Evidence: monitoring API regression (`tests/unit/dpm/api/test_monitoring_api.py`), router-wide
  Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation
  passed with no drift.
- Follow-up: use ordered route-module inventories for parent routers when dynamic registration is
  still the safest pattern.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-198: Portfolio memory parent router repeated route-module imports

- Date: 2026-06-01
- Scope: `src/api/routers/portfolio_memory.py`.
- Finding: the portfolio memory parent router registered search, event, and detail routes through
  repeated `importlib.import_module()` calls. That made route order less explicit as an inventory
  and created copy/paste friction for future portfolio-memory route slices.
- Action: centralized portfolio memory route module names in one ordered tuple and registered them
  through a single loop. Public paths, route ordering, response models, OpenAPI output, source
  repository dependency flow, search, event, and detail behavior were preserved.
- Status: hardened
- Evidence: portfolio memory API regression (`tests/unit/dpm/api/test_portfolio_memory_api.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: use ordered route-module inventories for parent routers when dynamic registration is
  still the safest pattern.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-199: Policy-pack parent router repeated route-module imports

- Date: 2026-06-01
- Scope: `src/api/routers/rebalance_policy_packs.py`.
- Finding: the policy-pack parent router registered effective-resolution, catalog, and admin
  routes through repeated `importlib.import_module()` calls. That made route order less explicit as
  an inventory and created copy/paste friction for future policy-pack route slices.
- Action: centralized policy-pack route module names in one ordered tuple and registered them
  through a single loop. Public paths, route ordering, response models, OpenAPI output, backend
  initialization behavior, policy-pack resolution metrics, catalog, and admin behavior were
  preserved.
- Status: hardened
- Evidence: policy-pack API regression (`tests/unit/dpm/api/test_dpm_policy_pack_admin_api.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: use ordered route-module inventories for parent routers when dynamic registration is
  still the safest pattern.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-200: Rebalance simulation parent router repeated dynamic callable imports

- Date: 2026-06-01
- Scope: `src/api/routers/rebalance_simulation.py`.
- Finding: the rebalance simulation parent router still used repeated dynamic module imports plus
  repeated attribute extraction for simulate, analyze, async analyze, and operation execution
  routes. Unlike simple parent routers, this module also exposes compatibility callables consumed by
  `src/api/main.py`, so removing those exports would be a behavior risk.
- Action: introduced a focused route-callable loader and kept the explicit compatibility exports for
  `simulate_rebalance`, `analyze_scenarios`, `analyze_scenarios_async`, and
  `execute_dpm_async_operation`. Public paths, route ordering, response models, OpenAPI output,
  idempotency behavior, async operation behavior, and `src/api/main.py` imports were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: keep explicit route callable exports until `src/api/main.py` no longer imports endpoint
  functions for compatibility.
- Wiki decision: no wiki source change required; this is internal route registration readability
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-201: Parent routers duplicated route-module registration loops

- Date: 2026-06-01
- Scope:
  `src/api/routers/route_registration.py`, `src/api/routers/construction.py`,
  `src/api/routers/mandates.py`, and `src/api/routers/monitoring.py`.
- Finding: after construction, mandate, and monitoring parent routers were converted to ordered
  route-module inventories, each still repeated the same dynamic registration loop. That duplicated
  parent-router mechanics across services and made future registration changes more error-prone.
- Action: introduced `register_route_modules()` as the shared router registration helper and applied
  it to the construction, mandate, and monitoring parent routers. Public paths, route ordering,
  response models, OpenAPI output, dependency flow, and route behavior were preserved.
- Status: hardened
- Evidence: construction, mandate, and monitoring API regressions
  (`tests/unit/dpm/api/test_construction_api.py`, `tests/unit/dpm/api/test_mandates_api.py`, and
  `tests/unit/dpm/api/test_monitoring_api.py`), router-wide Ruff checks, router-wide mypy, OpenAPI
  quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: apply the helper to remaining parent routers in small, focused slices after their
  focused regressions pass.
- Wiki decision: no wiki source change required; this is internal route registration reuse cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-202: Proof, portfolio-memory, and policy-pack routers duplicated registration loops

- Date: 2026-06-01
- Scope:
  `src/api/routers/proof_packs.py`, `src/api/routers/portfolio_memory.py`, and
  `src/api/routers/rebalance_policy_packs.py`.
- Finding: proof-pack, portfolio-memory, and policy-pack parent routers still repeated local
  route-module registration loops after their route inventories were centralized. That left the
  same import mechanics duplicated across business surfaces.
- Action: replaced the local loops with the shared `register_route_modules()` helper while
  preserving each router's ordered route inventory. Public paths, route ordering, response models,
  OpenAPI output, repository/dependency flow, proof-pack, portfolio-memory, and policy-pack
  behavior were preserved.
- Status: hardened
- Evidence: proof-pack, portfolio-memory, and policy-pack API regressions
  (`tests/unit/dpm/api/test_proof_pack_api.py`,
  `tests/unit/dpm/api/test_portfolio_memory_api.py`, and
  `tests/unit/dpm/api/test_dpm_policy_pack_admin_api.py`), router-wide Ruff checks, router-wide
  mypy, OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: apply the helper to remaining parent routers in small, focused slices after their
  focused regressions pass.
- Wiki decision: no wiki source change required; this is internal route registration reuse cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-203: Outcome and rebalance parent routers duplicated registration loops

- Date: 2026-06-01
- Scope: `src/api/routers/outcome_reviews.py` and `src/api/routers/rebalance_runs.py`.
- Finding: outcome-review and rebalance-run parent routers still repeated local route-module
  registration loops after their route inventories were centralized. That duplicated the same
  parent-router mechanics across two of the larger operational API surfaces.
- Action: replaced the local loops with the shared `register_route_modules()` helper while
  preserving each router's ordered route inventory. Public paths, route ordering, response models,
  OpenAPI output, outcome-review lookup prefixes, rebalance run supportability behavior, and
  workflow/async operation registration were preserved.
- Status: hardened
- Evidence: outcome-review and DPM rebalance API regressions
  (`tests/unit/api/test_outcome_reviews_api.py` and `tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: keep `rebalance_simulation.py` on its callable-loader pattern while `src/api/main.py`
  imports endpoint functions for compatibility.
- Wiki decision: no wiki source change required; this is internal route registration reuse cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-204: Rebalance simulation kept a local route-callable loader

- Date: 2026-06-01
- Scope:
  `src/api/routers/route_registration.py` and `src/api/routers/rebalance_simulation.py`.
- Finding: after route registration mechanics were centralized, rebalance simulation still owned a
  local dynamic callable loader for compatibility endpoint exports consumed by `src/api/main.py`.
  That left dynamic route import mechanics split between the shared utility and one parent router.
- Action: moved the callable loading helper into `route_registration.py` and updated
  `rebalance_simulation.py` to reuse it while keeping explicit exports for `simulate_rebalance`,
  `analyze_scenarios`, `analyze_scenarios_async`, and `execute_dpm_async_operation`. Public paths,
  route ordering, response models, OpenAPI output, idempotency behavior, async operation behavior,
  and `src/api/main.py` imports were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: keep explicit route callable exports until `src/api/main.py` no longer imports endpoint
  functions for compatibility.
- Wiki decision: no wiki source change required; this is internal route registration reuse cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-205: Rebalance workflow action routes duplicated HTTP mapping and metrics

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs_workflow_action_routes.py` and
  `src/api/routers/rebalance_runs_workflow_action_http.py`.
- Finding: the run-id, correlation-id, and idempotency-key workflow action routes repeated the same
  success metric, not-found mapping, disabled mapping, and conflict mapping. That duplicated
  operational behavior across three command routes and increased drift risk for future workflow
  action changes.
- Action: extracted the shared workflow-action metric and HTTP exception mapping into
  `apply_workflow_action_with_http_mapping()` and kept each route focused on request validation,
  handle resolution, and service invocation. Public paths, request/response models, OpenAPI output,
  unsupported-query rejection, correlation-id fallback behavior, metric labels, disabled/not-found
  `404` mapping, and conflict `409` mapping were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: inspect remaining high-traffic command routes for duplicated HTTP mapping before
  adding new workflow behavior.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-206: Rebalance workflow read routes repeated not-found mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs_workflow_state_routes.py`,
  `src/api/routers/rebalance_runs_workflow_history_routes.py`,
  `src/api/routers/rebalance_runs_workflow_decision_routes.py`, and
  `src/api/routers/rebalance_runs_workflow_read_http.py`.
- Finding: workflow state, history, and correlation decision read routes each repeated the same
  `DpmRunNotFoundError` to `404` HTTP mapping after feature-flag and query-parameter checks. The
  duplicated branch was mechanically identical and raised drift risk across the three operational
  run handles.
- Action: extracted `read_workflow_with_http_mapping()` and routed workflow read service calls
  through it. Public paths, response models, feature-flag assertions, unsupported-query rejection,
  OpenAPI output, and `404` detail behavior were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: evaluate whether non-workflow rebalance run lookups should share a broader run
  not-found helper after the workflow read surfaces are stable.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-207: Rebalance support-bundle routes repeated not-found mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs_support_bundle_run_routes.py`,
  `src/api/routers/rebalance_runs_support_bundle_correlation_routes.py`,
  `src/api/routers/rebalance_runs_support_bundle_idempotency_routes.py`,
  `src/api/routers/rebalance_runs_support_bundle_operation_routes.py`, and
  `src/api/routers/rebalance_runs_support_bundle_http.py`.
- Finding: the run-id, correlation-id, idempotency-key, and async-operation support-bundle
  routes repeated identical `DpmRunNotFoundError` to `404` mapping around service calls. The
  repeated branch made supportability lookup behavior easier to drift while future bundle
  sections are added.
- Action: extracted `read_support_bundle_with_http_mapping()` and routed all support-bundle
  service calls through it. Public paths, query parameters, feature-flag assertions, response
  models, OpenAPI output, and `404` detail behavior were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: keep optional support-bundle section toggles centralized in
  `rebalance_runs_support_bundle_parameters.py`; avoid duplicating include-flag vocabulary in
  future support-bundle route modules.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-208: Rebalance route helpers duplicated run not-found mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs_http.py`,
  `src/api/routers/rebalance_runs_workflow_read_http.py`, and
  `src/api/routers/rebalance_runs_support_bundle_http.py`.
- Finding: the workflow-read and support-bundle helper modules each carried their own
  `DpmRunNotFoundError` to `404` mapping. That avoided route-level duplication but introduced a
  second layer where the same HTTP primitive could drift as more rebalance helper modules are
  added.
- Action: introduced `read_run_with_not_found_http_mapping()` as the shared rebalance-run HTTP
  primitive and made the workflow-read and support-bundle helpers delegate to it. Public routes,
  response models, OpenAPI output, and `404` detail behavior were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: reuse the shared primitive when consolidating remaining rebalance run lookup routes
  that map `DpmRunNotFoundError` to `404`.
- Wiki decision: no wiki source change required; this is internal helper consolidation with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-209: Rebalance run lookup routes repeated not-found mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs_lookup_run_routes.py`,
  `src/api/routers/rebalance_runs_lookup_correlation_routes.py`,
  `src/api/routers/rebalance_runs_lookup_idempotency_routes.py`,
  `src/api/routers/rebalance_runs_lookup_request_hash_routes.py`, and
  `src/api/routers/rebalance_runs_lookup_idempotency_history_routes.py`.
- Finding: run lookup endpoints for run id, correlation id, idempotency key, request hash, and
  idempotency history repeated identical `DpmRunNotFoundError` to `404` handling. That made
  operational lookup behavior more verbose and easier to drift from support-bundle and workflow
  lookup behavior.
- Action: routed the lookup service calls through `read_run_with_not_found_http_mapping()`.
  Public paths, response models, feature-flag assertions, unsupported-query rejection, OpenAPI
  output, and `404` detail behavior were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: apply the same primitive to artifact and async-operation lookup routes if validation
  confirms no semantic distinction is needed.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-210: Rebalance artifact and async lookup routes repeated not-found mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/rebalance_runs_artifact_routes.py` and
  `src/api/routers/rebalance_runs_async_operation_lookup_routes.py`.
- Finding: artifact lookup and async-operation lookup routes still repeated the same
  `DpmRunNotFoundError` to `404` mapping after the run lookup routes had moved to the shared
  rebalance-run HTTP primitive. That left a small but avoidable inconsistency across operator
  support lookup surfaces.
- Action: routed artifact, operation-id, and correlation-id async operation reads through
  `read_run_with_not_found_http_mapping()`. Public paths, response models, feature-flag
  assertions, OpenAPI output, and `404` detail behavior were preserved.
- Status: hardened
- Evidence: DPM rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: keep the workflow action helper separate because it maps additional disabled and
  conflict workflow outcomes, not only run-not-found lookup behavior.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-211: Mandate and monitoring routes repeated not-found mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/mandate_http.py`, `src/api/routers/mandate_read_routes.py`,
  `src/api/routers/mandate_health_routes.py`,
  `src/api/routers/monitoring_exception_routes.py`,
  `src/api/routers/monitoring_run_read_routes.py`, and
  `src/api/routers/monitoring_run_once_routes.py`.
- Finding: mandate read, mandate health, monitoring run read, monitoring exception resolution,
  and monitoring run-once routes repeated the same domain not-found to `404` HTTP mapping. The
  repeated branches made mandate supportability routes more verbose and raised drift risk for
  future DPM command-center surfaces.
- Action: introduced `read_mandate_with_not_found_http_mapping()` and routed the not-found read
  and command service calls through it. Public paths, response models, source-readiness handling,
  OpenAPI output, and `404` detail behavior were preserved. The run-once filter assembly was moved
  into a small helper so the route body stays focused on selector validation and service
  invocation.
- Status: hardened
- Evidence: mandate and monitoring API regressions
  (`tests/unit/dpm/api/test_mandates_api.py` and
  `tests/unit/dpm/api/test_monitoring_api.py`), router-wide Ruff checks, router-wide mypy,
  OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: inspect mandate source-incomplete `424` handling for possible shared helper reuse
  after the not-found mapping has settled.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-212: Mandate source-incomplete routes repeated 424 mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/mandate_http.py`, `src/api/routers/mandate_health_routes.py`, and
  `src/api/routers/mandate_refresh_routes.py`.
- Finding: mandate health recalculation and refresh-from-core routes repeated identical
  `DpmMandateSourceIncompleteError` to `424 Failed Dependency` HTTP mapping with string detail.
  PM-book monitoring kept a separate structured code payload and was intentionally left outside
  this helper.
- Action: added `mandate_source_incomplete_http_exception()` to the mandate HTTP helper and reused
  it from the two matching route branches. Public paths, response models, OpenAPI output,
  source-unavailable `503` behavior, and existing `424` detail strings were preserved.
- Status: hardened
- Evidence: mandate and monitoring API regressions
  (`tests/unit/dpm/api/test_mandates_api.py` and
  `tests/unit/dpm/api/test_monitoring_api.py`), router-wide Ruff checks, router-wide mypy,
  OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: keep structured PM-book source-readiness failures explicit until a broader
  source-dependency error envelope is introduced.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-213: Outcome-review routes repeated HTTP exception construction

- Date: 2026-06-01
- Scope:
  `src/api/routers/outcome_review_http.py`,
  `src/api/routers/outcome_review_create_routes.py`,
  `src/api/routers/outcome_review_preview_routes.py`,
  `src/api/routers/outcome_review_refresh_routes.py`,
  `src/api/routers/outcome_review_lookup_routes.py`,
  `src/api/routers/outcome_review_run_lookup_routes.py`,
  `src/api/routers/outcome_review_supportability_routes.py`, and
  `src/api/routers/outcome_review_handoff_routes.py`.
- Finding: outcome-review routes repeated construction of the same `404`, `409`, and `422` HTTP
  exceptions with identical public details. The repeated branches made RFC-0042 operator and
  handoff routes harder to keep consistent as report, AI, supportability, and source-refresh
  surfaces evolve.
- Action: introduced `outcome_review_http.py` with shared not-found, conflict, and validation
  HTTP helpers and reused them from the matching routes. Public paths, response models,
  observability emission, OpenAPI output, and existing error details were preserved.
- Status: hardened
- Evidence: outcome-review API regression (`tests/unit/api/test_outcome_reviews_api.py`),
  router-wide Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: inspect PM-operating-quality route builders for the same repeated validation/conflict
  mapping pattern after outcome-review helper behavior is stable.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-214: PM operating quality routes repeated conflict mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/pm_operating_quality_http.py`,
  `src/api/routers/pm_operating_quality_score_run_routes.py`,
  `src/api/routers/pm_operating_quality_fairness_routes.py`,
  `src/api/routers/pm_operating_quality_review_action_routes.py`,
  `src/api/routers/pm_operating_quality_summary_routes.py`, and
  `src/api/routers/pm_operating_quality_policy_routes.py`.
- Finding: persisted PM operating-quality score runs, fairness analyses, review actions, summary
  invocations, and policy versions each repeated the same persistence-conflict to `409` HTTP
  mapping. The repeated branches made PM-quality governance routes noisier and increased drift
  risk for future persisted evidence surfaces.
- Action: introduced `pm_quality_conflict_http_exception()` and reused it from the persisted
  command routes while leaving route-specific validation, missing-resource, and source-dependency
  failures unchanged. Public paths, response models, OpenAPI output, and `409` detail strings were
  preserved.
- Status: hardened
- Evidence: PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), router-wide Ruff checks, router-wide mypy,
  OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: inspect PM-quality read-route not-found handling and builder validation handling as
  separate slices; those carry distinct detail payloads and should not be mixed into this conflict
  helper.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-215: PM operating quality read routes repeated not-found mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/pm_operating_quality_http.py`,
  `src/api/routers/pm_operating_quality_score_run_read_routes.py`,
  `src/api/routers/pm_operating_quality_fairness_read_routes.py`,
  `src/api/routers/pm_operating_quality_review_action_read_routes.py`,
  `src/api/routers/pm_operating_quality_summary_read_routes.py`, and
  `src/api/routers/pm_operating_quality_policy_routes.py`.
- Finding: PM operating-quality read routes repeated the same `404` response construction with
  a governed `PM_QUALITY_*_NOT_FOUND:<identifier>` detail. The detail codes differed by evidence
  family, but the HTTP construction pattern was identical and duplicated across score runs,
  fairness analyses, review actions, summary invocations, and policy versions.
- Action: added `pm_quality_not_found_http_exception()` to the PM-quality HTTP helper and reused
  it from the matching read routes. Public paths, response models, OpenAPI output, and existing
  `404` detail strings were preserved.
- Status: hardened
- Evidence: PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), router-wide Ruff checks, router-wide mypy,
  OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: inspect PM-quality builder validation handling separately because those failures
  intentionally mix missing persisted inputs and validation/conflict semantics.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-216: PM operating quality builders repeated validation mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/pm_operating_quality_http.py`,
  `src/api/routers/pm_operating_quality_policy_resolution.py`,
  `src/api/routers/pm_operating_quality_score_run_builder.py`,
  `src/api/routers/pm_operating_quality_fairness_builder.py`,
  `src/api/routers/pm_operating_quality_review_action_builder.py`, and
  `src/api/routers/pm_operating_quality_summary_invocation_builder.py`.
- Finding: PM operating-quality builder modules repeated the same `422` validation HTTP mapping
  and several matching PM-quality prerequisite `404` mappings. The repeated branches made the
  builder layer less consistent with the route-level PM-quality HTTP helper introduced for
  persisted reads and writes.
- Action: added `pm_quality_validation_http_exception()` and reused the existing
  `pm_quality_not_found_http_exception()` across PM-quality policy resolution, score-run,
  fairness, review-action, and summary-invocation builders. Public paths, response models,
  OpenAPI output, and existing `404`/`422` detail strings were preserved.
- Status: hardened
- Evidence: PM operating-quality API and service regressions
  (`tests/unit/api/test_pm_operating_quality_api.py` and
  `tests/unit/api/test_pm_operating_quality_service.py`), router-wide Ruff checks, router-wide
  mypy, OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: leave outcome-review prerequisite lookup in the score-run builder separate until a
  broader cross-domain prerequisite error helper is introduced.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-217: PM operating quality PM-book source dependency mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/pm_operating_quality_http.py` and
  `src/api/routers/pm_operating_quality_book_scope_builder.py`.
- Finding: PM operating-quality PM-book scope materialization still constructed source dependency
  HTTP failures inline for core resolver unavailability, incomplete PM-book membership data,
  source-readiness failure, and empty membership results. These mappings are PM-quality-specific
  contract details and should stay reusable near the rest of the PM-quality HTTP translation layer
  as Manage integrates with ongoing core and gateway refactors.
- Action: added PM-quality PM-book source dependency HTTP helpers and reused them from the book
  scope builder. Public paths, response models, OpenAPI output, and existing `503`/`424` detail
  payloads were preserved.
- Status: hardened
- Evidence: PM operating-quality API regression
  (`tests/unit/api/test_pm_operating_quality_api.py`), focused Ruff checks, router-wide mypy,
  OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: keep monitoring PM-book selector source-readiness mappings separate until monitoring
  and PM-quality agree on a shared source-dependency error envelope.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-218: Monitoring run-once PM-book selector HTTP mapping

- Date: 2026-06-01
- Scope:
  `src/api/routers/monitoring_http.py`, `src/api/routers/monitoring_run_once_routes.py`, and
  `tests/unit/dpm/api/test_monitoring_api.py`.
- Finding: monitoring run-once PM-book discovery constructed selector validation, core resolver
  source dependency, source-readiness, empty membership, and mandate snapshot dependency HTTP
  failures inline. That route-level branching mixed workflow orchestration with contract-specific
  error translation and made Manage more brittle while lotus-core and lotus-gateway integration
  surfaces are being refactored by other agents.
- Action: introduced monitoring-specific PM-book selector HTTP helpers and reused them from the
  run-once route. Added regression coverage for core resolver unavailable and incomplete source
  dependency mappings. Public paths, response models, OpenAPI output, and existing `422`,
  `503`, and `424` detail payloads were preserved.
- Status: hardened
- Evidence: monitoring API regression (`tests/unit/dpm/api/test_monitoring_api.py`), focused
  Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation
  passed with no drift.
- Follow-up: evaluate whether wave PM-book review source dependency mapping can reuse a shared
  lower-level envelope after core/gateway refactors settle; do not prematurely merge monitoring,
  PM-quality, and wave-specific messages.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-219: Mandate diff conflict HTTP mapping

- Date: 2026-06-01
- Scope: `src/api/routers/mandate_http.py` and `src/api/routers/mandate_read_routes.py`.
- Finding: mandate read routes already reused shared not-found HTTP mapping, but the mandate diff
  route still constructed its `409` unavailable-comparison response inline. The remaining branch
  was small, but it kept diff-specific contract translation outside the mandate HTTP helper layer.
- Action: added `mandate_diff_unavailable_http_exception()` and reused it from the mandate diff
  route. Public paths, response models, OpenAPI output, and existing `409` detail strings were
  preserved.
- Status: hardened
- Evidence: mandate API regression (`tests/unit/dpm/api/test_mandates_api.py`), focused Ruff
  checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation passed
  with no drift.
- Follow-up: inspect mandate refresh source-unavailable mapping separately; it is a `503`
  dependency failure and should not be mixed into the diff conflict helper.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-220: Mandate refresh source-unavailable HTTP mapping

- Date: 2026-06-01
- Scope: `src/api/routers/mandate_http.py` and `src/api/routers/mandate_refresh_routes.py`.
- Finding: mandate refresh already reused the shared source-incomplete `424` helper, but still
  constructed the source-unavailable `503` dependency failure inline. Keeping only one side of the
  refresh dependency contract in the helper layer made the route noisier and less consistent.
- Action: added `mandate_source_unavailable_http_exception()` and reused it from refresh-from-core.
  Public paths, response models, OpenAPI output, and existing `503` detail strings were preserved.
- Status: hardened
- Evidence: mandate API regression (`tests/unit/dpm/api/test_mandates_api.py`), focused Ruff
  checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation passed
  with no drift.
- Follow-up: keep mandate PM-book monitoring mappings in `monitoring_http.py` because those expose
  structured selector-specific detail payloads instead of mandate refresh strings.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-221: Proof-pack service leaked HTTP translation

- Date: 2026-06-01
- Scope:
  `src/api/services/proof_pack_service.py`, `src/api/routers/proof_pack_http.py`,
  `src/api/routers/proof_pack_generate_routes.py`,
  `src/api/routers/proof_pack_read_routes.py`,
  `src/api/routers/proof_pack_handoff_routes.py`, and
  `tests/unit/dpm/proof_packs/test_proof_pack_service.py`.
- Finding: `proof_pack_service` imported FastAPI and returned `HTTPException` objects from
  `to_api_http_exception()`. That kept transport-specific error translation inside an API service
  that otherwise owns proof-pack orchestration and handoff reference hydration.
- Action: moved proof-pack exception-to-HTTP mapping into the router helper
  `proof_pack_http.py`, reused it from proof-pack generate/read/handoff routes, and updated the
  focused mapping regression to assert the router-layer helper. Public paths, response models,
  OpenAPI output, and existing `404`/`409`/`424`/`500` details were preserved.
- Status: hardened
- Evidence: proof-pack service regression
  (`tests/unit/dpm/proof_packs/test_proof_pack_service.py`), proof-pack router/service Ruff checks,
  router-wide mypy, no FastAPI transport imports in `proof_pack_service.py`, OpenAPI quality gate,
  and API vocabulary inventory validation passed with no drift.
- Follow-up: inspect construction and rebalance simulation API services for the same FastAPI
  transport leakage in separate slices; those have larger route/service seams.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-222: Construction service leaked HTTP translation

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_service.py`, `src/api/routers/construction_http.py`,
  `src/api/routers/construction_generate_routes.py`,
  `src/api/routers/construction_read_routes.py`,
  `src/api/routers/construction_selection_routes.py`, and
  `tests/unit/dpm/api/test_construction_api.py`.
- Finding: `construction_service` imported FastAPI solely to convert construction domain errors
  into HTTP responses for generation, read, and selection routes. That transport dependency made a
  large construction orchestration module harder to treat as reusable application logic.
- Action: moved construction exception-to-HTTP mapping into `construction_http.py`, reused it from
  the construction routes, and added focused mapping regression coverage. Public paths, response
  models, OpenAPI output, and existing `404`/`409`/`500` detail strings were preserved.
- Status: hardened
- Evidence: construction API regression (`tests/unit/dpm/api/test_construction_api.py`),
  construction router/service Ruff checks, router-wide mypy, no FastAPI transport imports in
  `construction_service.py`, OpenAPI quality gate, and API vocabulary inventory validation passed
  with no drift.
- Follow-up: continue decomposing `construction_service.py` by construction concern; the HTTP
  boundary cleanup removes one transport dependency but the module remains too large for the
  long-term enterprise maintainability target.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-223: Rebalance envelope source-resolution HTTP leakage

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_simulation_service.py`,
  `src/api/routers/rebalance_simulation_http.py`,
  `src/api/routers/rebalance_simulation_simulate_routes.py`,
  `src/api/routers/rebalance_simulation_analyze_routes.py`,
  `src/api/routers/rebalance_simulation_async_routes.py`,
  `src/api/routers/construction_generate_routes.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: rebalance execution-envelope and stateful source-resolution helpers raised FastAPI
  `HTTPException` directly for missing stateless/stateful input, disabled stateful sourcing,
  unavailable core resolver, and incomplete core context. These helpers are reused by simulation,
  batch analysis, async analysis, and construction generation, so transport-specific failures in
  the service layer made shared source-resolution logic harder to reuse and test as application
  logic.
- Action: introduced domain-level rebalance envelope/source-resolution exceptions, added
  `rebalance_simulation_http.py` for route-layer HTTP mapping, and reused it from simulation,
  analysis, async-analysis, and construction generation routes. Public paths, response models,
  OpenAPI output, observability recording, and existing `422`/`409`/`503`/`424` detail strings
  were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge, rebalance API, and construction API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py`,
  `tests/unit/dpm/api/test_api_rebalance.py`, and
  `tests/unit/dpm/api/test_construction_api.py`), rebalance/construction router/service Ruff
  checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory validation passed
  with no drift.
- Follow-up: continue moving idempotency and async-operation HTTP mappings out of
  `rebalance_simulation_service.py` in smaller slices; those paths have separate persistence and
  operation-state semantics.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-224: Rebalance simulation idempotency HTTP leakage

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_simulation_errors.py`,
  `src/api/services/rebalance_simulation_service.py`,
  `src/api/routers/rebalance_simulation_http.py`,
  `src/api/routers/rebalance_simulation_simulate_routes.py`, and
  `tests/unit/dpm/api/test_api_rebalance.py`.
- Finding: `simulate_rebalance()` still raised FastAPI `HTTPException` directly for replay
  idempotency conflicts, inconsistent idempotency lookup state, and support-store write failures.
  These failures are part of simulation application semantics and should be represented as domain
  errors before the route layer maps them to HTTP.
- Action: introduced simulation idempotency domain exceptions, mapped them in
  `rebalance_simulation_http.py`, and reused that mapper from the simulation route. Public paths,
  response models, OpenAPI output, observability recording, and existing `409`/`503` detail
  strings were preserved.
- Status: hardened
- Evidence: rebalance API regression (`tests/unit/dpm/api/test_api_rebalance.py`), rebalance
  router/service Ruff checks, router-wide mypy, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: move async-operation disabled/conflict/manual execution HTTP mappings out of
  `rebalance_simulation_service.py` separately; those remain operation-state specific.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-225: Rebalance async-operation HTTP leakage

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_simulation_errors.py`,
  `src/api/services/rebalance_simulation_service.py`,
  `src/api/routers/rebalance_simulation_http.py`,
  `src/api/routers/rebalance_simulation_async_routes.py`,
  `src/api/routers/rebalance_simulation_operation_routes.py`,
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`, and
  `tests/unit/dpm/api/test_api_rebalance.py`.
- Finding: async analysis submit and manual operation execution still raised FastAPI
  `HTTPException` directly for disabled async operations, correlation conflicts, disabled manual
  execution, missing operations, and non-executable operation state. These operation-state
  semantics belong in the application layer and should be mapped to HTTP only at the route edge.
- Action: introduced rebalance async-operation domain exceptions, extended
  `rebalance_simulation_http.py` with async-operation HTTP mapping, and reused it from async submit
  and manual execution routes. Public paths, response models, OpenAPI output, observability
  recording, and existing `404`/`409` detail strings were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), rebalance router/service Ruff checks, router-wide
  mypy, OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: after async-operation mapping stabilizes, inspect remaining scenario-loop catches in
  `execute_batch_analysis()` and `run_analyze_async_operation()` for whether `HTTPException`
  compatibility handling can be narrowed without weakening failure capture.
- Wiki decision: no wiki source change required; this is internal route/helper modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-226: Rebalance run-support provider HTTP boundary

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_run_support_service.py`,
  `src/api/routers/rebalance_runs.py`, `src/api/main.py`,
  `src/api/services/rebalance_simulation_service.py`,
  `src/api/routers/rebalance_simulation_http.py`,
  `src/api/services/rebalance_simulation_errors.py`,
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`, and
  `tests/unit/dpm/api/test_api_rebalance.py`.
- Finding: the reusable run-support service provider and supportability persistence helper lived in
  the run-support router module and translated backend initialization failures directly to
  FastAPI `HTTPException`. Rebalance simulation consumed that router helper for idempotency,
  supportability persistence, and async analysis submission, which kept transport behavior inside
  application-service execution paths.
- Action: moved run-support provider construction and supportability persistence into
  `rebalance_run_support_service.py` with an application-level unavailable exception, kept
  `rebalance_runs.py` as the HTTP mapper for route dependencies, and had rebalance simulation
  consume the non-HTTP provider directly. Support backend initialization failures are translated
  to rebalance simulation or async-operation domain errors before the router maps them to the
  preserved `503` response detail.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the touched
  router/service modules, OpenAPI quality gate, and API vocabulary inventory validation passed
  with no drift.
- Follow-up: continue reducing router-owned service-provider state by moving remaining
  run-support feature guards and route helper exports behind narrower HTTP adapter modules when a
  route slice already touches those surfaces.
- Wiki decision: no wiki source change required; this is internal provider-boundary modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-227: Rebalance batch-analysis helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_batch_analysis.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `rebalance_simulation_service.py` still mixed orchestration with pure batch-analysis
  helper logic for invalid scenario-option formatting, base snapshot identity resolution, and
  comparison-metric construction. That made the already-large simulation service harder to scan
  and harder to test at the helper boundary.
- Action: extracted the pure batch-analysis helpers into `rebalance_batch_analysis.py` and kept
  `execute_batch_analysis()` focused on orchestration, policy application, simulation execution,
  supportability persistence, observability, and response assembly. Public routes, payloads,
  OpenAPI output, and comparison metric behavior were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the helper
  and simulation service, OpenAPI quality gate, and API vocabulary inventory validation passed with
  no drift.
- Follow-up: continue extracting independent source-resolution, policy-pack, and async-operation
  helper families from `rebalance_simulation_service.py` when each can be covered without broad
  route churn.
- Wiki decision: no wiki source change required; this is internal helper modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-228: Policy-pack service/router boundary

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_policy_pack_service.py`,
  `src/api/routers/rebalance_policy_packs.py`,
  `src/api/routers/rebalance_policy_pack_catalog_routes.py`,
  `src/api/routers/rebalance_policy_pack_effective_routes.py`,
  `src/api/routers/rebalance_simulation_analyze_routes.py`,
  `src/api/routers/rebalance_simulation_async_routes.py`,
  `src/api/services/rebalance_simulation_service.py`,
  `src/api/services/rebalance_simulation_errors.py`,
  `src/api/routers/rebalance_simulation_http.py`,
  `src/api/persistence_profile.py`, and policy-pack/rebalance test fixtures.
- Finding: policy-pack repository construction, catalog loading, tenant/default resolution, and
  backend error normalization lived in the policy-pack router module. Rebalance simulation and
  persistence-profile guardrails imported those helpers from the router, so reusable application
  logic still depended on transport and route-registration code.
- Action: moved policy-pack resolution, repository construction, catalog loading, DSN/backend
  helpers, and catalog-unavailable application errors into
  `rebalance_policy_pack_service.py`. The policy-pack router now maps service unavailable errors
  to HTTP, while rebalance simulation maps selected-policy catalog failures through its existing
  route-edge HTTP mapper. Public routes, response models, OpenAPI output, and existing `503`
  detail strings were preserved.
- Status: hardened
- Evidence: policy-pack config/admin, persistence-profile, and rebalance API regressions
  (`tests/unit/dpm/api/test_dpm_policy_pack_config.py`,
  `tests/unit/dpm/api/test_dpm_policy_pack_admin_api.py`,
  `tests/unit/api/test_persistence_profile.py`, and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over touched
  policy/rebalance modules, OpenAPI quality gate, and API vocabulary inventory validation passed
  with no drift.
- Follow-up: continue moving remaining reusable runtime configuration helpers out of router
  modules when each consumer can switch without widening the public API surface.
- Wiki decision: no wiki source change required; this is internal service-boundary modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-229: Run-support config service boundary

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_run_support_config.py`,
  `src/api/routers/rebalance_runs_config.py`,
  `src/api/services/rebalance_run_support_service.py`,
  `src/api/routers/rebalance_runs.py`,
  `src/api/routers/rebalance_runs_inventory_routes.py`,
  `src/api/persistence_profile.py`, `src/api/production_cutover_contract.py`, and focused
  run-support, persistence, cutover, and rebalance tests.
- Finding: run-support repository/configuration helpers lived under the router package even though
  they provided application configuration, environment parsing, repository construction, and
  production guardrail inputs. The run-support service and production guardrails therefore still
  depended on router package plumbing after the provider extraction.
- Action: moved run-support configuration and repository-construction helpers into
  `rebalance_run_support_config.py`, kept `rebalance_runs_config.py` as a compatibility shim for
  route-local imports, and updated service, persistence-profile, cutover, and test patch paths to
  use the service module. No public route, payload, OpenAPI, or operator detail changed.
- Status: hardened
- Evidence: run-support config, runtime request-model/service edge, persistence-profile,
  production-cutover, and rebalance API regressions
  (`tests/unit/dpm/api/test_dpm_runs_config.py`,
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`,
  `tests/unit/api/test_persistence_profile.py`,
  `tests/unit/shared/dependencies/test_production_cutover_contract.py`, and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over touched
  run-support modules, service-layer import scan showing no remaining FastAPI/router imports,
  OpenAPI quality gate, and API vocabulary inventory validation passed with no drift.
- Follow-up: continue decomposing router-adjacent helper modules in other domains, especially
  wave and PM operating quality builders that still mix request/HTTP concerns with reusable
  application logic.
- Wiki decision: no wiki source change required; this is internal configuration-boundary
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-230: Core resolver construction service boundary

- Date: 2026-06-01
- Scope:
  `src/api/services/core_resolver_service.py`,
  `src/api/services/rebalance_simulation_service.py`,
  core-resolver-consuming routers for mandates, monitoring, PM operating quality, and waves, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `rebalance_simulation_service.py` still owned DPM core resolver client construction and
  source-sourcing environment parsing even though mandate refresh, monitoring, PM operating
  quality, wave preview, and campaign launch routes also consumed that capability. This made a
  rebalance orchestration module the de facto owner of cross-domain core integration plumbing.
- Action: extracted core resolver client construction and DPM core resolver environment parsing
  into `core_resolver_service.py`, updated consuming routers to import the resolver factory from
  that module, and kept compatibility exports in `rebalance_simulation_service.py` for existing
  stateful envelope tests and callers. Public routes, OpenAPI output, resolver defaults, timeout
  and retry semantics, and stateful source-resolution behavior were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge, rebalance API, mandate API, monitoring API, PM
  operating quality API, and waves API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py`,
  `tests/unit/dpm/api/test_api_rebalance.py`, `tests/unit/dpm/api/test_mandates_api.py`,
  `tests/unit/dpm/api/test_monitoring_api.py`,
  `tests/unit/api/test_pm_operating_quality_api.py`, and
  `tests/unit/dpm/api/test_waves_api.py`), focused Ruff checks, focused mypy over the resolver
  service and consuming routers, OpenAPI quality gate, and API vocabulary inventory validation
  passed with no drift.
- Follow-up: move stateful envelope resolution itself out of `rebalance_simulation_service.py` in a
  later slice once the compatibility path for existing tests and main-module overrides is narrowed.
- Wiki decision: no wiki source change required; this is internal integration-helper modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-231: Rebalance source-lineage helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_source_lineage.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `rebalance_simulation_service.py` still owned source-input mode classification and
  result lineage stamping while also coordinating policy packs, idempotency, run-support
  recording, batch analysis, and async execution. That kept audit-lineage mutation coupled to a
  broad orchestration module and made the stateful/stateless behavior harder to verify directly.
- Action: extracted source-input mode classification and result source-lineage stamping into
  `rebalance_source_lineage.py`, updated simulation orchestration to call the helper, and kept
  compatibility aliases for existing private helper callers. Public routes, OpenAPI output,
  result payload shape, source-lineage field names, and supportability semantics were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the
  source-lineage and simulation services, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: continue reducing `rebalance_simulation_service.py` by extracting stateful envelope
  resolution and async execution helpers in later small slices once their test seams are direct.
- Wiki decision: no wiki source change required; this is internal service-boundary modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-232: Rebalance async configuration service boundary

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_async_config.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: async operation feature flags, manual-execution gating, and execution-mode
  normalization were still embedded in `rebalance_simulation_service.py`, even though they are
  reusable runtime configuration concerns and are also compatibility-exported through
  `src/api/main.py`. This kept configuration parsing mixed into simulation orchestration.
- Action: extracted async flag and mode helpers into `rebalance_async_config.py`, updated
  simulation orchestration to use the dedicated helper for async operation gating, and preserved
  compatibility exports from `rebalance_simulation_service.py`. Public routes, OpenAPI output,
  accepted execution modes, default behavior, and async disabled/manual-disabled error details
  were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the async
  config and simulation services, OpenAPI quality gate, and API vocabulary inventory validation
  passed with no drift.
- Follow-up: continue extracting async execution orchestration from `rebalance_simulation_service.py`
  once the operation lifecycle can be isolated without widening the HTTP error-mapping surface.
- Wiki decision: no wiki source change required; this is internal runtime-configuration modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-233: Rebalance idempotency replay helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_idempotency_replay.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `simulate_rebalance` still contained the full idempotency replay lookup path,
  including support-service availability mapping, request-hash conflict detection, missing-run
  consistency handling, replay result validation, and execution telemetry. This made the main
  simulation orchestration harder to read and kept replay edge behavior coupled to unrelated
  policy-pack and persistence-write flow.
- Action: extracted replay lookup/conflict/inconsistent-store handling into
  `rebalance_idempotency_replay.py`, kept the support-service factory injectable so existing
  test/main patch seams remain valid, and updated `simulate_rebalance` to return replayed results
  through the helper. Public routes, OpenAPI output, idempotency error details, telemetry labels,
  and replay payload shape were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the
  idempotency replay and simulation services, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: extract simulation supportability-write handling next, so replay lookup and
  persistence failure behavior are both independently testable service helpers.
- Wiki decision: no wiki source change required; this is internal orchestration modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-234: Rebalance supportability-write helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_supportability_write.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `simulate_rebalance` still owned post-run supportability persistence and the
  fail-closed/fail-open split between replay-enabled idempotency writes and replay-disabled best
  effort persistence. That made supportability-store failure semantics harder to test without a
  full simulation request path.
- Action: extracted simulation supportability recording into `rebalance_supportability_write.py`,
  preserved the main-module override for `record_dpm_run_for_support`, and kept replay-enabled
  write failures mapped to `DPM_IDEMPOTENCY_STORE_WRITE_FAILED` while replay-disabled failures are
  logged and do not block simulation. Public routes, OpenAPI output, result payloads, and error
  details were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the
  supportability-write and simulation services, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: continue extracting the remaining policy-resolution and batch-execution orchestration
  from `rebalance_simulation_service.py` only in small slices with direct lower-level coverage.
- Wiki decision: no wiki source change required; this is internal supportability-write modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-235: Async analyze payload parser extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_async_operation_payload.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `run_analyze_async_operation` still parsed both current persisted async-operation
  envelopes and legacy raw batch payloads inline before delegating to batch analysis. That made
  backward-compatibility behavior for stored operations hard to test without running the async
  operation executor.
- Action: extracted current/legacy async analyze payload parsing into
  `rebalance_async_operation_payload.py`, including batch request validation, optional persisted
  source-context validation, and policy-context selectors. The operation executor now consumes a
  typed payload object before invoking batch analysis. Public routes, OpenAPI output, stored
  operation payload compatibility, and policy-pack selector behavior were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the async
  payload and simulation services, OpenAPI quality gate, and API vocabulary inventory validation
  passed with no drift.
- Follow-up: continue reducing `run_analyze_async_operation` by extracting completion/failure
  recording once the operation lifecycle can be isolated without changing support-service calls.
- Wiki decision: no wiki source change required; this is internal async-operation modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-236: Async analyze completion helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_async_operation_completion.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `run_analyze_async_operation` still mixed batch execution with support-service
  completion/failure writes and async telemetry recording. This made operation lifecycle side
  effects harder to verify without inducing execution success and failure paths through the full
  async executor.
- Action: extracted async analyze success and failure completion into
  `rebalance_async_operation_completion.py`, preserving support-service calls, failure code/message
  derivation, logger behavior, and async telemetry outcomes. Public routes, OpenAPI output, stored
  operation state transitions, and response payloads were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the async
  completion and simulation services, OpenAPI quality gate, and API vocabulary inventory validation
  passed with no drift.
- Follow-up: move batch scenario execution out of `rebalance_simulation_service.py` in a later
  slice once the run-function and support-write seams can be passed explicitly.
- Wiki decision: no wiki source change required; this is internal async-operation lifecycle
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-237: Batch scenario execution helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_batch_execution.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `execute_batch_analysis` still owned scenario option validation, per-scenario engine
  invocation, source-lineage stamping, supportability recording, comparison-metric assembly,
  partial-failure warnings, and execution telemetry. That made the batch API orchestration too
  broad and kept invalid-option behavior tied to the full route-level request path.
- Action: extracted batch scenario execution into `rebalance_batch_execution.py`, passing the run
  function and supportability recorder explicitly so existing override seams remain intact.
  `execute_batch_analysis` now resolves policy context and delegates scenario execution to the
  helper. Public routes, OpenAPI output, batch result shape, invalid-option messages, partial
  failure warnings, and supportability writes were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the batch
  execution and simulation services, OpenAPI quality gate, and API vocabulary inventory validation
  passed with no drift.
- Follow-up: continue narrowing `rebalance_simulation_service.py` toward policy-context
  resolution, sync simulation orchestration, and async operation orchestration only.
- Wiki decision: no wiki source change required; this is internal batch-execution modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-238: Rebalance policy-pack execution helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_policy_pack_execution.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `rebalance_simulation_service.py` still owned selected policy-pack catalog loading,
  catalog-unavailable error translation, and policy-resolution telemetry. These behaviors are
  execution-policy concerns used by simulate/analyze/analyze-async paths and should be directly
  testable without the larger simulation orchestration.
- Action: extracted selected policy-pack definition resolution and telemetry recording into
  `rebalance_policy_pack_execution.py`, while preserving the existing
  `rebalance_simulation_service.load_dpm_policy_pack_catalog` patch seam through a compatibility
  wrapper. Public routes, OpenAPI output, disabled-policy catalog short-circuit behavior,
  policy-pack telemetry labels, and catalog-unavailable error details were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the
  policy-pack execution and simulation services, OpenAPI quality gate, and API vocabulary
  inventory validation passed with no drift.
- Follow-up: continue reducing `rebalance_simulation_service.py` by extracting stateful envelope
  resolution and async submission envelope construction in small compatibility-preserving slices.
- Wiki decision: no wiki source change required; this is internal policy-execution modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-239: Stateful source-context helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_stateful_source_context.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `_resolve_stateful_source_context` still owned stateful payload gating, resolver
  construction, core-resolver exception mapping, resolver telemetry, and canonical context hashing.
  That kept source-data integration mechanics in the main rebalance orchestration module and made
  gate behavior harder to test without the compatibility wrapper.
- Action: extracted stateful source-context resolution into
  `rebalance_stateful_source_context.py`, with explicit resolver factory and feature flag inputs.
  The existing `_resolve_stateful_source_context` wrapper remains as the compatibility seam for
  current tests and main-module overrides. Public routes, OpenAPI output, stateful disabled/missing
  payload details, core resolver error mapping, telemetry labels, and context hash behavior were
  preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the
  stateful-source and simulation services, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: extract stateless/stateful envelope-to-request transformation next so core-context
  validation and request materialization have direct helper tests.
- Wiki decision: no wiki source change required; this is internal core-sourcing modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-240: Rebalance request-envelope resolution helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_request_envelope_resolution.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `rebalance_simulation_service.py` still owned stateless envelope validation,
  stateful source-context resolution delegation, core-context-to-request transformation, and
  transform-error mapping for both simulate and batch analyze paths. That kept request
  materialization mixed into orchestration and made stateless pass-through/stateful failure mapping
  harder to prove directly.
- Action: extracted rebalance and batch request-envelope materialization into
  `rebalance_request_envelope_resolution.py`, with explicit stateful resolver and request-builder
  dependencies. The existing service functions remain as compatibility wrappers for route callers
  and tests. Public routes, OpenAPI output, stateless missing-payload details, core-context
  incomplete mapping, and request payload shape were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the
  request-envelope and simulation services, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: extract async submission payload construction and submit telemetry next so async
  operation intake has direct helper coverage.
- Wiki decision: no wiki source change required; this is internal request-materialization
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-241: Async analyze submission payload helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_async_submission_payload.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `submit_and_optionally_execute_async_analysis` still built the persisted async analyze
  request envelope inline, including batch request serialization, policy-context selectors, and
  optional source-context serialization. That made the stored-operation contract harder to test
  without exercising the full async submit path.
- Action: extracted async analyze request-json construction into
  `rebalance_async_submission_payload.py` and updated async submission to use the helper. Public
  routes, OpenAPI output, stored operation envelope shape, policy context keys, and source-context
  serialization behavior were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the async
  submission and simulation services, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: extract async submit telemetry/conflict handling once support-service submit behavior
  can remain injectable and independently testable.
- Wiki decision: no wiki source change required; this is internal async submission modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-242: Stale in-memory idempotency cache removal

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_simulation_service.py`, `src/api/main.py`,
  `tests/unit/dpm/api/test_api_rebalance.py`,
  `tests/unit/dpm/api/test_proof_pack_api.py`, and
  `tests/integration/dpm/api/test_dpm_api_workflow_integration.py`.
- Finding: `DPM_IDEMPOTENCY_CACHE` and `DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE` remained exported
  compatibility state from the earlier in-memory replay implementation. Production replay and
  run lookup now use the run-support service/repository path, and current tests only cleared the
  stale cache without any code path reading or writing it.
- Action: removed the stale cache object, default cache-size constant, and `src.api.main` exports,
  then updated unit and integration fixtures to reset the real run-support service only. This
  removes misleading state that could imply an unsupported in-process idempotency replay path.
- Status: hardened
- Evidence: rebalance API, proof-pack API, and DPM workflow integration regressions
  (`tests/unit/dpm/api/test_api_rebalance.py`, `tests/unit/dpm/api/test_proof_pack_api.py`, and
  `tests/integration/dpm/api/test_dpm_api_workflow_integration.py`), focused Ruff checks, focused
  mypy over `src/api/services/rebalance_simulation_service.py` and `src/api/main.py`, repository
  search showing no remaining stale cache symbols, OpenAPI quality gate, and API vocabulary
  inventory validation passed with no drift.
- Follow-up: keep pruning exported compatibility state only when search and tests prove it is no
  longer part of a supported public or test contract.
- Wiki decision: no wiki source change required; this removes internal stale compatibility state
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-243: Async analyze submit helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_async_submission.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `submit_and_optionally_execute_async_analysis` still mixed support-service submission,
  correlation-conflict mapping, async submit telemetry, and execution telemetry with feature
  gating and inline/accept-only execution flow. This kept async intake side effects coupled to the
  larger orchestration function.
- Action: extracted support-service submit handling into `rebalance_async_submission.py`, including
  accepted/conflict telemetry and `DpmRebalanceAsyncOperationConflictError` mapping. The main
  async orchestration now builds the persisted payload, submits through the helper, and then only
  decides whether to execute inline. Public routes, OpenAPI output, accepted response shape,
  conflict detail, and telemetry labels were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the async
  submission and simulation services, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: continue narrowing `rebalance_simulation_service.py` around synchronous simulate
  orchestration and manual async execution only.
- Wiki decision: no wiki source change required; this is internal async intake modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-244: Manual async execution helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_async_manual_execution.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `execute_dpm_async_operation` still mixed manual execution gating with operation
  execution, not-found/not-executable mapping, async telemetry, and final operation-status lookup.
  This kept manual operation lifecycle edge behavior coupled to the remaining rebalance
  orchestration module.
- Action: extracted manual async execution into `rebalance_async_manual_execution.py`, preserving
  manual execution telemetry, `DPM_ASYNC_OPERATION_NOT_FOUND` mapping, non-executable mapping, and
  final status lookup. The public service wrapper still owns feature/manual gate checks.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the manual
  async execution and simulation services, OpenAPI quality gate, and API vocabulary inventory
  validation passed with no drift.
- Follow-up: continue reducing `rebalance_simulation_service.py` around synchronous simulate
  orchestration and compatibility exports only.
- Wiki decision: no wiki source change required; this is internal manual async execution
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-245: Synchronous simulate execution helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_sync_execution.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `simulate_rebalance` still owned policy application to engine options, idempotency
  replay lookup, engine invocation, source-lineage stamping, supportability persistence,
  blocked-run warning, and execution telemetry. That kept the main service wrapper broad even
  after policy and source-context extraction.
- Action: extracted the synchronous simulate execution flow into `rebalance_sync_execution.py`,
  passing support-service, engine, and supportability recorder dependencies explicitly so existing
  `src.api.main` patch seams remain intact. The wrapper now resolves request hash, correlation id,
  and policy context before delegating execution. Public routes, OpenAPI output, replay behavior,
  supportability write behavior, lineage stamping, and telemetry labels were preserved.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the
  synchronous execution and simulation services, OpenAPI quality gate, and API vocabulary
  inventory validation passed with no drift.
- Follow-up: review remaining compatibility exports and main override seams to remove only those
  proven unused by repository search and regression coverage.
- Wiki decision: no wiki source change required; this is internal synchronous execution modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-246: Rebalance policy-pack execution context consolidation

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_policy_pack_execution.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: synchronous simulate, synchronous analyze, and async analyze submission each repeated
  policy-pack resolution, policy telemetry recording, selected-definition loading, and debug
  logging setup in the main rebalance orchestration service. That made the remaining service
  wrapper broader than necessary and increased the chance that async submission would accidentally
  drift from its existing deferred catalog-lookup behavior.
- Action: introduced a reusable `DpmExecutionPolicyPackContext` helper that resolves policy-pack
  selection, records policy resolution telemetry, and optionally loads the selected definition.
  Synchronous simulate and analyze now use the loaded definition path, while async submission uses
  the explicit deferred-definition path so accept-only semantics do not force policy-catalog
  access earlier than before. Added focused unit coverage for both loaded and deferred modes.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over policy-pack
  execution and simulation services, OpenAPI quality gate, API vocabulary inventory validation,
  diff check, and service-layer HTTP leakage scan passed with no behavioral or contract drift.
- Follow-up: continue narrowing remaining `rebalance_simulation_service.py` compatibility seams
  only where search and regression tests prove existing callers no longer depend on them.
- Wiki decision: no wiki source change required; this is internal policy-pack orchestration
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-247: Async analyze operation runner extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_async_operation_runner.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: `run_analyze_async_operation` still mixed stored-operation payload retrieval,
  current/legacy async payload parsing, batch execution dispatch, completion writes, and
  failure-state mapping inside the main rebalance orchestration service. That kept async lifecycle
  behavior harder to test directly and made the remaining compatibility wrapper broader than
  needed.
- Action: extracted the stored async analyze operation lifecycle into
  `rebalance_async_operation_runner.py`, with an explicit typed batch-execution dependency and
  logger dependency. The public service function now preserves the existing `src.api.main`
  override behavior and delegates to the runner. Added focused coverage proving current async
  payload policy context is passed through to batch execution and completion is recorded.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the async
  operation runner and simulation service, OpenAPI quality gate, API vocabulary inventory
  validation, diff check, and service-layer HTTP leakage scan passed with no behavioral or
  contract drift.
- Follow-up: review whether remaining `src.api.main` patch seams can be replaced with a
  dedicated dependency override module after route and test callers are aligned.
- Wiki decision: no wiki source change required; this is internal async lifecycle modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-248: Rebalance runtime override helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_runtime_overrides.py`,
  `src/api/services/rebalance_simulation_service.py`, and
  `tests/unit/api/test_runtime_request_model_and_service_edges.py`.
- Finding: the remaining rebalance service compatibility seams still performed ad hoc dynamic
  lookups into `src.api.main` for logger, core resolver factory, engine invocation,
  supportability recording, and async batch execution overrides. The behavior was required for
  existing route/test compatibility, but the mechanism was hidden inside the broad orchestration
  module.
- Action: introduced `rebalance_runtime_overrides.py` to centralize main-module override lookup,
  callable fallback resolution, and logger fallback resolution. The rebalance service now consumes
  that helper for all remaining compatibility override paths. Added focused coverage for missing
  main-export fallback behavior while preserving existing `src.api.main` patch-seam regression
  tests.
- Status: hardened
- Evidence: runtime request-model/service edge and rebalance API regressions
  (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over runtime
  overrides and simulation service, OpenAPI quality gate, API vocabulary inventory validation,
  diff check, and service-layer HTTP leakage scan passed with no behavioral or contract drift.
- Follow-up: migrate route tests toward explicit dependency injection before deleting legacy
  `src.api.main` compatibility exports.
- Wiki decision: no wiki source change required; this is internal compatibility-boundary
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-249: Stale rebalance compatibility alias removal

- Date: 2026-06-01
- Scope:
  `src/api/services/rebalance_simulation_service.py` and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: after the policy-pack, source-lineage, and runtime-override extractions, the rebalance
  simulation service still carried stale private aliases for selected policy-pack definition
  resolution and source-lineage helpers. Repository search showed no route, service, or test
  callers for those aliases, while active env/core aliases still had callers and were left intact.
- Action: removed the unused service-local selected-policy wrapper and the stale source-lineage
  alias exports/imports. This keeps the remaining compatibility surface limited to paths that are
  still exercised by routes, `src.api.main`, or regression tests.
- Status: hardened
- Evidence: repository search for the removed aliases, runtime request-model/service edge and
  rebalance API regressions (`tests/unit/api/test_runtime_request_model_and_service_edges.py` and
  `tests/unit/dpm/api/test_api_rebalance.py`), focused Ruff checks, focused mypy over the
  simulation service, OpenAPI quality gate, API vocabulary inventory validation, diff check, and
  service-layer HTTP leakage scan passed with no behavioral or contract drift.
- Follow-up: continue pruning compatibility aliases only with search evidence and focused
  regression coverage; do not remove the remaining env/core exports until their callers migrate.
- Wiki decision: no wiki source change required; this is internal stale-alias cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-250: Construction idempotency helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_idempotency.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_construction_idempotency.py`.
- Finding: construction alternative-set generation embedded canonical request-hash construction,
  method/source-context participation, idempotency replay lookup, and conflict detection directly
  in the large construction service. That made a production-critical replay/audit boundary harder
  to test without running the full construction generation path.
- Action: extracted construction request-hash construction and existing alternative-set replay
  resolution into `construction_idempotency.py`. The generation service now delegates this
  idempotency boundary before executing methods. Added focused tests proving methods and stateful
  source context participate in the hash and that replay/conflict behavior is enforced directly.
- Status: hardened
- Evidence: focused construction idempotency and construction API regressions
  (`tests/unit/dpm/construction/test_construction_idempotency.py` and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 27 tests, focused Ruff checks,
  focused mypy over construction idempotency and construction service, OpenAPI quality gate, API
  vocabulary inventory validation, diff check, and service-layer HTTP leakage scan passed with no
  behavioral or contract drift.
- Follow-up: continue extracting construction source-product authority context and method-specific
  supportability in small compatibility-preserving slices; keep tests direct at the helper layer
  where the behavior is not inherently route-level.
- Wiki decision: no wiki source change required; this is internal idempotency-boundary modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-251: Construction transaction-cost supportability extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_transaction_cost_supportability.py`,
  `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_transaction_cost_supportability.py`, and
  `tests/unit/dpm/construction/test_enrichment.py`.
- Finding: observed transaction-cost supportability logic was embedded in the large construction
  service, including source-owned curve coverage checks, estimated-cost objective/constraint
  trace composition, reason-code derivation, and local cost estimation from candidate trade
  notionals. This made a source-authority boundary hard to test independently and kept
  transaction-cost behavior coupled to unrelated ESG/liquidity/currency-overlay helpers.
- Action: extracted transaction-cost supportability into
  `construction_transaction_cost_supportability.py`, kept thin service compatibility wrappers for
  existing private-helper tests, and added direct helper coverage for applied observed curves and
  degraded missing-security coverage. Also updated a stale enrichment test to assert construction
  HTTP exception mapping through `src.api.routers.construction_http` instead of reintroducing HTTP
  translation into the service layer.
- Status: hardened
- Evidence: focused transaction-cost supportability, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_transaction_cost_supportability.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 52 tests, focused Ruff checks,
  focused mypy over transaction-cost supportability and construction service, OpenAPI quality
  gate, API vocabulary inventory validation, diff check, and service-layer HTTP leakage scan
  passed with no API contract drift.
- Follow-up: continue extracting ESG/restriction and source-product authority-context helpers into
  dedicated service modules while keeping business logic outside routers and HTTP mapping outside
  services.
- Wiki decision: no wiki source change required; this is internal source-evidence supportability
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-252: Construction ESG supportability extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_esg_supportability.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_esg_supportability.py`.
- Finding: client-restriction and sustainability-preference supportability logic was still
  embedded in the broad construction service, including source-owned restriction scope matching,
  buy/sell applicability, missing-data reason codes, sustainability allocation checks, and
  classification review posture. That kept ESG/client-preference behavior coupled to unrelated
  transaction-cost, liquidity, currency-overlay, and source-context code.
- Action: extracted ESG/restriction supportability into `construction_esg_supportability.py` and
  left thin compatibility wrappers in the construction service for existing private-helper
  coverage. Added direct helper tests for active client restriction blocking, asset/issuer/country
  scope matching, sustainability allocation review, and classification-evidence review posture.
- Status: hardened
- Evidence: focused ESG supportability, construction enrichment, and construction API regressions
  (`tests/unit/dpm/construction/test_esg_supportability.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests, focused Ruff checks,
  focused mypy over ESG supportability and construction service, OpenAPI quality gate, API
  vocabulary inventory validation, diff check, and service-layer HTTP leakage scan passed with no
  API contract drift.
- Follow-up: continue extracting liquidity/currency-overlay/regime-stress supportability and
  source-product authority-context assembly in small slices with direct helper coverage.
- Wiki decision: no wiki source change required; this is internal source-evidence supportability
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-253: Construction method supportability extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_method_supportability.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_method_supportability.py`.
- Finding: liquidity, cashflow projection, currency-overlay, and regime-stress supportability
  decisions remained embedded in the large construction service after transaction-cost and ESG
  extraction. These helpers encode private-banking method-readiness behavior and source-evidence
  posture, but were still coupled to construction orchestration and authority-context assembly.
- Action: extracted method supportability decisions into
  `construction_method_supportability.py`, including liquidity status/reason codes, derived
  manage liquidity policy context, currency-overlay missing-pair handling, derived FX overlay
  context, and regime-stress threshold posture. The construction service now keeps thin
  compatibility wrappers for existing private-helper coverage. Added direct helper tests for
  derived liquidity policy, missing FX pair blocking, and regime-stress threshold breach review.
- Status: hardened
- Evidence: focused method supportability, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_method_supportability.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests, focused Ruff checks,
  focused mypy over method supportability and construction service, OpenAPI quality gate, API
  vocabulary inventory validation, diff check, and service-layer HTTP leakage scan passed with no
  API contract drift.
- Follow-up: continue extracting construction authority-context source-product assembly and method
  orchestration in small slices; keep source-owner non-claim boundaries explicit in tests and docs
  when behavior changes.
- Wiki decision: no wiki source change required; this is internal method-supportability
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-254: Construction method execution helper extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_method_execution.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_method_execution.py`.
- Finding: construction method execution mechanics still lived inside the construction service,
  including method-specific engine option mutation, method-specific correlation-id construction,
  engine invocation, and optional run-support recording. This kept execution mechanics coupled to
  alternative-set orchestration and source-authority supportability code.
- Action: extracted method execution into `construction_method_execution.py`, including
  `options_for_construction_method` and `run_construction_method`. The construction service now
  delegates through thin compatibility wrappers. Added direct tests for bounded method option
  overrides and method-specific correlation/support recording.
- Status: hardened
- Evidence: focused method execution, construction enrichment, and construction API regressions
  (`tests/unit/dpm/construction/test_method_execution.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 52 tests, focused Ruff checks,
  focused mypy over method execution and construction service, OpenAPI quality gate, API
  vocabulary inventory validation, diff check, and service-layer HTTP leakage scan passed with no
  API contract drift.
- Follow-up: continue extracting construction alternative orchestration and source-product
  authority-context assembly; keep patch seams explicit only where tests or routes still rely on
  them.
- Wiki decision: no wiki source change required; this is internal execution-boundary modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-255: Construction solver supportability extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_solver_supportability.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_solver_supportability.py`.
- Finding: solver-constrained readiness logic and method reason-code merging still lived inside
  the broad construction service. That kept solver warning classification and enrichment
  diagnostics coupled to orchestration, even though they are bounded method-supportability
  decisions that can be tested independently.
- Action: extracted solver warning posture and method reason-code merging into
  `construction_solver_supportability.py`. The construction service now delegates through thin
  compatibility wrappers. Added direct helper tests for deterministic reason-code merging, ready
  solver posture without solver warnings, and lowest-posture selection when solver diagnostics
  include non-optimal and infeasible warnings.
- Status: hardened
- Evidence: focused solver supportability, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_solver_supportability.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests, focused Ruff checks, and
  focused mypy over solver supportability and construction service passed.
- Follow-up: continue extracting construction source-product authority-context assembly and the
  remaining supportability application orchestration in small, behavior-preserving slices.
- Wiki decision: no wiki source change required; this is internal solver-supportability
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-256: Construction method readiness extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_method_readiness.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_method_readiness.py`.
- Finding: method-specific readiness and reason-code assembly still lived inside the top-level
  construction service after source-specific supportability helpers were extracted. This kept
  solver diagnostics, risk-authority missing evidence, liquidity settlement posture, transaction
  cost evidence, ESG restrictions, currency-overlay evidence, and regime scenario posture coupled
  to alternative-set orchestration.
- Action: extracted method-specific readiness and reason-code assembly into
  `construction_method_readiness.py`, reusing the already extracted supportability helpers. The
  construction service now delegates through thin compatibility wrappers. Added direct tests for
  solver reason-code evidence and risk-aware missing-authority posture.
- Status: hardened
- Evidence: focused method readiness, construction enrichment, and construction API regressions
  (`tests/unit/dpm/construction/test_method_readiness.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 52 tests, focused Ruff checks, and
  focused mypy over method readiness and construction service passed.
- Follow-up: extract source-product authority-context assembly and source-analytics posture while
  preserving Manage's non-claim boundary over risk, performance, treasury, execution, and core
  source products.
- Wiki decision: no wiki source change required; this is internal method-readiness modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-257: Construction source analytics posture extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_analytics_posture.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_source_analytics_posture.py`.
- Finding: the construction service still embedded the risk/performance source-analytics posture
  map, including required source products and blocked local methodology claims. This posture is
  durable product evidence and should be independently testable instead of hidden in orchestration.
- Action: extracted source-analytics posture into
  `construction_source_analytics_posture.py` and left the construction service as a thin delegate.
  Added direct tests that keep `RiskMetricsReport:v1` required for risk-aware readiness,
  `RegimeScenarioPackEvaluation:v1` required for regime-stress readiness, performance products
  non-required, and local risk/performance methodology calculations explicitly blocked.
- Status: hardened
- Evidence: focused source-analytics posture, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_source_analytics_posture.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 52 tests, focused Ruff checks, and
  focused mypy over source-analytics posture and construction service passed.
- Follow-up: continue extracting source-product authority-context assembly for lotus-core treasury,
  execution acknowledgement, client restriction, sustainability, liquidity, and risk context
  inputs.
- Wiki decision: no wiki source change required; this is internal source-posture modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-258: Construction method authority-context extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_method_authority.py`,
  `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_method_authority.py`, and
  `tests/unit/dpm/construction/test_enrichment.py`.
- Finding: per-method authority-context resolution still lived inside the construction service,
  including risk concentration fetches, fail-closed risk-unavailable behavior, derived liquidity
  and currency-overlay contexts, and regime scenario fetches using the governed construction
  as-of date. That kept source-boundary behavior embedded in orchestration.
- Action: extracted method authority-context resolution into
  `construction_method_authority.py`. The construction service now delegates with the resolved
  construction as-of date. Added direct tests for risk-authority context fetch, fail-closed risk
  unavailability, and governed as-of-date propagation to regime scenario context. Updated
  enrichment tests to import the risk-authority exception from the infrastructure boundary rather
  than via the construction service.
- Status: hardened
- Evidence: focused method authority, construction enrichment, and construction API regressions
  (`tests/unit/dpm/construction/test_method_authority.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests, focused Ruff checks, and
  focused mypy over method authority and construction service passed.
- Follow-up: continue extracting source-product authority-context assembly for lotus-core external
  treasury and order-execution acknowledgement contexts.
- Wiki decision: no wiki source change required; this is internal authority-context modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-259: External execution acknowledgement context extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_source_product_context.py`.
- Finding: external OMS order-execution acknowledgement context construction remained embedded in
  the construction service together with general source-status mapping. This fail-closed boundary
  is an enterprise control: Manage may preserve source acknowledgement evidence but must not claim
  order, fill, settlement, or OMS truth locally.
- Action: extracted external order-execution acknowledgement context construction and source
  supportability status mapping into `construction_source_product_context.py`. Added direct tests
  for absent source response, fail-closed unavailable acknowledgement posture, source lineage
  preservation, blocked execution/fill/settlement capabilities, and non-ready source status mapping
  to blocked method posture.
- Status: hardened
- Evidence: focused source-product context, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests, focused Ruff checks, and
  focused mypy over source-product context and construction service passed.
- Follow-up: continue extracting external treasury currency-overlay context and the remaining
  source-product authority-context assembly by source family.
- Wiki decision: no wiki source change required; this is internal source-product context
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-260: External treasury currency-overlay context extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_source_product_context.py`.
- Finding: external treasury currency-overlay context construction remained embedded in the
  construction service. The logic preserves fail-closed source evidence for hedge execution
  readiness, currency exposure, hedge policy, eligible hedge instruments, and FX forward curves,
  but does not authorize local treasury, OMS, execution, or forward-pricing claims. Keeping this
  source-product boundary inside orchestration made it harder to audit.
- Action: moved external treasury currency-overlay context construction into
  `construction_source_product_context.py`, alongside the extracted external execution
  acknowledgement boundary. Added direct tests for absent source response and fail-closed hedge
  execution readiness evidence, including lineage preservation, blocked treasury/OMS/execution
  capabilities, zero hedge-ratio defaults, eligible-currency preservation, and reason-code
  propagation.
- Status: hardened
- Evidence: focused source-product context, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 55 tests, focused Ruff checks, and
  focused mypy over source-product context and construction service passed.
- Follow-up: extract remaining source-product authority-context assembly by source family,
  starting with transaction cost and liquidity source products.
- Wiki decision: no wiki source change required; this is internal source-product context
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-261: Transaction-cost source curve context extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_source_product_context.py`.
- Finding: lotus-core `TransactionCostCurve:v1` mapping into Manage's authoritative
  transaction-cost context remained embedded in construction orchestration. This mapping controls
  lineage, completeness posture, evidence-window dates, missing securities, and bounded sample
  transaction evidence for cost-aware alternatives.
- Action: extracted transaction-cost curve mapping into
  `transaction_cost_context_from_curve`. Added direct tests that preserve source lineage, degraded
  supportability, returned/missing-security evidence, and the five-transaction sample bound.
- Status: hardened
- Evidence: focused source-product context, transaction-cost supportability, construction
  enrichment, and construction API regressions
  (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_transaction_cost_supportability.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 58 tests, focused Ruff checks, and
  focused mypy over source-product context and construction service passed.
- Follow-up: extract remaining source-product authority-context assembly for liquidity,
  restriction, and sustainability source products.
- Wiki decision: no wiki source change required; this is internal source-product context
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-262: Liquidity cashflow source context extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_source_product_context.py`.
- Finding: lotus-core `PortfolioCashflowProjection:v1` mapping into Manage's liquidity context
  still lived inside construction orchestration. The mapping preserves source lineage, projection
  window, projected-cashflow inclusion, currency, amount, and data-quality posture for
  liquidity-aware construction alternatives.
- Action: extracted cashflow projection mapping into
  `liquidity_cashflow_projection_context`. Added direct tests that preserve source lineage,
  degraded data-quality posture, money currency/amount, projected inclusion, and reason-code
  evidence.
- Status: hardened
- Evidence: focused source-product context, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 57 tests, focused Ruff checks, and
  focused mypy over source-product context and construction service passed.
- Follow-up: extract remaining liquidity source products for client income needs, reserve
  requirements, and planned withdrawals.
- Wiki decision: no wiki source change required; this is internal source-product context
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-263: Client income-needs source context extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_source_product_context.py`.
- Finding: lotus-core `ClientIncomeNeedsSchedule:v1` mapping into Manage's liquidity context
  still lived inside construction orchestration. The mapping preserves client income-needs lineage,
  schedule count, represented currencies, priority posture, and supportability state for
  liquidity-aware construction without turning Manage into a financial-planning source owner.
- Action: extracted client income-needs mapping into
  `client_income_needs_schedule_context`. Added direct tests that preserve source lineage,
  currency aggregation, highest-priority selection, incomplete-source fail-closed posture, and
  reason-code evidence.
- Status: hardened
- Evidence: focused source-product context, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 58 tests, focused Ruff checks, and
  focused mypy over source-product context and construction service passed.
- Follow-up: extract remaining liquidity source products for reserve requirements and planned
  withdrawals.
- Wiki decision: no wiki source change required; this is internal source-product context
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-264: Remaining source-product context extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_source_product_context.py`.
- Finding: liquidity reserve requirements, planned withdrawal schedules, client restriction
  profiles, and sustainability preference profiles still mapped lotus-core source products inside
  construction orchestration. These mappings preserve lineage, content hashes, supportability
  states, represented currencies, horizons, restriction rules, and sustainability preferences, but
  they are pure source-boundary assembly rather than orchestration.
- Action: extracted the four remaining source-product mappings into
  `construction_source_product_context.py`, keeping `_authority_context_with_source_products`
  responsible only for deciding when to attach source-derived contexts. Added direct helper tests
  for reserve requirement, planned withdrawal, client restriction, and sustainability preference
  source evidence.
- Status: hardened
- Evidence: focused source-product context, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 62 tests. Focused Ruff checks,
  focused mypy over source-product context and construction service, OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue shrinking `construction_service.py` by extracting larger source-family
  attachment orchestration only when it can be done without hiding method-specific behavior.
- Wiki decision: no wiki source change required; this is internal source-product context
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-265: Liquidity source-family context assembly extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`, and
  `tests/unit/dpm/construction/test_enrichment.py`.
- Finding: after individual liquidity source-product mappings were extracted, the construction
  service still assembled the composite liquidity authority context and policy reason codes
  inline. The service also kept thin pass-through wrappers for external treasury and execution
  acknowledgement source-context helpers. This left pure source-boundary assembly mixed with
  construction orchestration.
- Action: added `source_liquidity_context` to assemble the liquidity source family from
  cashflow projection, client income-needs, liquidity reserve, and planned-withdrawal source
  products. Updated construction orchestration to attach the returned liquidity context when
  present and removed thin pass-through wrapper functions. Added direct helper tests for complete
  liquidity source-family assembly and absent-source behavior.
- Status: hardened
- Evidence: focused source-product context, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 64 tests. Focused Ruff checks,
  focused mypy over source-product context and construction service, OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue shrinking `construction_service.py` by extracting the remaining
  source-family attachment decisions only where the extracted boundary remains directly testable.
- Wiki decision: no wiki source change required; this is internal source-product context
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-266: Source-product authority update extraction

- Date: 2026-06-01
- Scope:
  `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`, and
  `tests/unit/dpm/construction/test_source_product_context.py`.
- Finding: construction orchestration still contained the full source-product authority-context
  update matrix for transaction cost, liquidity, currency-overlay, execution acknowledgement,
  client restrictions, and sustainability preferences. The mapping was pure source-boundary
  assembly with existing-context preservation rules, not method orchestration.
- Action: added `source_product_authority_context_updates` to compute source-derived authority
  context updates in the helper module. Reduced `_authority_context_with_source_products` to a
  null-source guard, helper call, and model-copy application. Added direct tests proving all source
  families are lifted and caller-supplied existing contexts are not overwritten.
- Status: hardened
- Evidence: focused source-product context, construction enrichment, and construction API
  regressions (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 66 tests. Focused Ruff checks,
  focused mypy over source-product context and construction service, OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue reviewing `construction_service.py` for pass-through supportability wrappers
  that can move to domain-specific helper modules without weakening method-level readability.
- Wiki decision: no wiki source change required; this is internal source-product context
  modularity cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-267: Construction supportability wrapper pruning

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py` and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: construction orchestration retained thin pass-through wrappers for method-specific
  status, enrichment reason-code attachment, source analytics posture, and an unused construction
  options wrapper. These wrappers added private indirection without preserving domain ownership or
  isolating behavior.
- Action: removed the unused options wrapper and replaced private pass-through calls with direct
  calls to the established domain helper modules. Kept the remaining wrappers where existing
  tests still document supportability behavior through the current service boundary.
- Status: hardened
- Evidence: focused construction enrichment and construction API regressions
  (`tests/unit/dpm/construction/test_enrichment.py` and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 50 tests. Focused Ruff checks,
  focused mypy over construction service, OpenAPI quality, API vocabulary validation, service
  leakage scan, and `git diff --check` passed.
- Follow-up: continue moving supportability tests toward their owning helper modules so additional
  pass-through wrappers can be removed without reducing behavioral coverage.
- Wiki decision: no wiki source change required; this is internal orchestration cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-268: Supportability wrapper ownership cleanup

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: construction-service private wrappers still exposed liquidity, currency-overlay, and
  solver supportability helpers even though the behavior is owned by
  `construction_method_supportability.py` and `construction_solver_supportability.py`. The tests
  were reaching through the orchestration service for helper-owned behavior, which preserved
  unnecessary service indirection.
- Action: moved the affected tests to call the owning supportability helpers directly and removed
  the service pass-through wrappers plus their now-unused imports. `construction_service.py` now
  calls `solver_method_status` directly where solver-constrained orchestration needs it.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over `construction_service.py`, and focused
  construction supportability regressions (`tests/unit/dpm/construction/test_enrichment.py`,
  `tests/unit/dpm/construction/test_method_supportability.py`, and
  `tests/unit/dpm/construction/test_solver_supportability.py`) passed with 31 tests.
- Follow-up: continue migrating transaction-cost and ESG supportability wrapper tests to their
  owning helper modules before pruning the next set of private pass-through wrappers.
- Wiki decision: no wiki source change required; this is internal service/helper ownership cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-269: Transaction-cost wrapper ownership cleanup

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: transaction-cost supportability tests still reached through construction-service
  private wrappers for observed cost estimate, transaction-cost status, and reason-code assembly,
  even though those behaviors are owned by `construction_transaction_cost_supportability.py`.
  The service also used a private pass-through wrapper to attach observed transaction-cost
  estimates to COST_AWARE alternatives.
- Action: moved the transaction-cost tests to call the owning helper module directly, removed the
  service pass-through wrappers and unused imports, and had construction orchestration call
  `with_observed_transaction_cost_estimate` directly when COST_AWARE supportability is applied.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over `construction_service.py`, focused
  construction transaction-cost and API regressions (`tests/unit/dpm/construction/test_enrichment.py`,
  `tests/unit/dpm/construction/test_transaction_cost_supportability.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 52 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue migrating ESG supportability wrapper tests to their owning helper module
  before pruning the next private pass-through group.
- Wiki decision: no wiki source change required; this is internal service/helper ownership cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-270: ESG wrapper ownership cleanup

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: ESG, client-restriction, and sustainability supportability tests still depended on
  construction-service private wrappers, while the actual behavior is owned by
  `construction_esg_supportability.py`. The service also retained a pass-through wrapper for
  applying ESG restriction constraints to ESG_AWARE alternatives.
- Action: moved the affected tests to call the ESG supportability helper module directly, removed
  the service pass-through wrappers and unused domain-type imports, and had construction
  orchestration call `with_esg_restriction_constraints` directly where ESG_AWARE supportability is
  applied.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over `construction_service.py`, focused ESG and API
  regressions (`tests/unit/dpm/construction/test_enrichment.py`,
  `tests/unit/dpm/construction/test_esg_supportability.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue reviewing remaining construction-service private wrappers for real
  orchestration value before pruning or moving tests to owner modules.
- Wiki decision: no wiki source change required; this is internal service/helper ownership cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-271: Shared construction status ordering

- Date: 2026-06-01
- Scope: `src/core/construction/status.py`, construction core helpers, construction supportability
  services, `tests/unit/dpm/construction/test_status.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: construction method status ordering was duplicated across orchestration, supportability,
  solver, enrichment, transaction-cost, ESG, and alternative-set aggregation helpers. Each copy
  encoded the same conservative ordering from BLOCKED through READY, creating drift risk for
  future supportability changes.
- Action: added `lowest_construction_status` and `construction_status_rank` in core construction
  status helpers, exported them from `src.core.construction`, and replaced local duplicated
  `_lowest_status` implementations and status-order maps across the affected modules. Added direct
  status helper tests for conservative ordering and empty-input default behavior.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over touched source files, and focused construction
  regressions (`tests/unit/dpm/construction/test_status.py`,
  `tests/unit/dpm/construction/test_enrichment.py`,
  `tests/unit/dpm/construction/test_method_supportability.py`,
  `tests/unit/dpm/construction/test_esg_supportability.py`,
  `tests/unit/dpm/construction/test_transaction_cost_supportability.py`,
  `tests/unit/dpm/construction/test_solver_supportability.py`,
  `tests/unit/dpm/construction/test_alternative_engine.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 67 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue reducing construction-service orchestration size without introducing new
  helper-level duplication.
- Wiki decision: no wiki source change required; this is internal supportability primitive cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-272: Construction request date extraction

- Date: 2026-06-01
- Scope: `src/api/services/construction_request_dates.py`,
  `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: construction-service orchestration still owned request snapshot date parsing for
  authority-context as-of dates. The logic is pure request metadata interpretation rather than
  alternative construction orchestration.
- Action: extracted `construction_as_of_date` into `construction_request_dates.py`, updated
  authority-context orchestration to call the helper, and pointed the existing snapshot-id date
  regression test at the extracted helper.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over construction request-date and service modules,
  focused construction authority/API regressions (`tests/unit/dpm/construction/test_enrichment.py`,
  `tests/unit/dpm/construction/test_method_authority.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue keeping `construction_service.py` focused on orchestration and move pure
  request/diagnostic assembly into direct helper modules when the boundary is clear.
- Wiki decision: no wiki source change required; this is internal service/helper ownership cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-273: Method reason-code wrapper pruning

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: construction-service orchestration still had a private wrapper for method-specific
  reason-code assembly. The wrapper only forwarded to `construction_method_readiness.py` and kept
  an unused enrichment parameter, adding indirection without isolating behavior.
- Action: updated construction orchestration and the remaining regression test to call
  `method_specific_reason_codes` directly, then removed the private wrapper and its unused type
  import from `construction_service.py`.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over construction service and method-readiness
  modules, focused construction readiness/API regressions
  (`tests/unit/dpm/construction/test_enrichment.py`,
  `tests/unit/dpm/construction/test_method_readiness.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 52 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: keep the remaining private service helpers only where they express orchestration
  boundaries, not pass-through behavior.
- Wiki decision: no wiki source change required; this is internal service/helper ownership cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-274: Source-product authority attachment extraction

- Date: 2026-06-01
- Scope: `src/api/services/construction_source_product_context.py`,
  `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: after source-product authority update assembly was extracted, construction-service
  orchestration still owned the final null-source guard and authority-context model-copy
  application. Several tests continued to reach through the service private wrapper for
  source-boundary behavior.
- Action: added `authority_context_with_source_products` to the source-product context helper,
  updated construction orchestration to call it directly, moved remaining tests to the owning
  helper module, and removed the service private wrapper.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over construction source-product context and service
  modules, focused source-product/enrichment/API regressions
  (`tests/unit/dpm/construction/test_source_product_context.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 66 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue shrinking construction orchestration only where the extracted boundary has a
  clear owning module and direct tests.
- Wiki decision: no wiki source change required; this is internal source-boundary ownership cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-275: Method execution wrapper pruning

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py` and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: construction-service orchestration still kept a private `_run_method` wrapper that only
  forwarded to `run_construction_method`. It added no domain boundary beyond the existing
  construction method execution module and obscured the two actual orchestration call sites.
- Action: removed the pass-through wrapper and called `run_construction_method` directly for the
  heuristic base run and non-heuristic effective method runs.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over `construction_service.py`, focused method
  execution/enrichment/API regressions (`tests/unit/dpm/construction/test_enrichment.py`,
  `tests/unit/dpm/construction/test_method_execution.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 52 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: keep remaining private helpers for true construction orchestration only.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-276: Request-aware method authority adapter extraction

- Date: 2026-06-01
- Scope: `src/api/services/construction_method_authority.py`,
  `src/api/services/construction_service.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: construction-service orchestration still owned a private request-aware adapter around
  method authority context enrichment. The adapter only supplied the governed request as-of date
  before delegating to `construction_method_authority.py`, so tests reached through service
  internals for method-authority behavior.
- Action: added `authority_context_for_request_method` to the method authority module, updated
  construction orchestration and tests to call it directly, and removed the service private
  adapter.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over construction method-authority and service
  modules, focused method-authority/enrichment/API regressions
  (`tests/unit/dpm/construction/test_method_authority.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: leave `construction_service.py` focused on alternative-set orchestration and
  supportability application.
- Wiki decision: no wiki source change required; this is internal service/helper ownership cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-277: Construction supportability application extraction

- Date: 2026-06-01
- Scope: `src/api/services/construction_supportability_application.py`,
  `src/api/services/construction_service.py`, and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: `construction_service.py` still owned the full method supportability application block,
  including enrichment posture assembly, cost/ESG constraint application, method reason-code
  attachment, method status roll-up, and diagnostic payload construction. That block is a coherent
  supportability application boundary rather than alternative-set orchestration.
- Action: extracted `apply_construction_supportability` into
  `construction_supportability_application.py` and updated construction alternative orchestration
  to delegate to it. Removed now-unused supportability, readiness, enrichment, source-analytics,
  and status imports from `construction_service.py`.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over construction supportability application and
  service modules, focused construction enrichment/API regressions
  (`tests/unit/dpm/construction/test_enrichment.py` and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 50 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: add direct supportability-application tests before making further changes inside the
  extracted method-status roll-up behavior.
- Wiki decision: no wiki source change required; this is internal construction-service modularity
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-278: Supportability application direct coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_supportability_application.py` and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: the extracted `construction_supportability_application.py` helper was covered through
  construction service and API regressions, but it did not yet have direct helper-level coverage
  proving diagnostic assembly and COST_AWARE transaction-cost evidence attachment.
- Action: added a focused unit test that applies COST_AWARE supportability directly, asserts the
  method status remains READY when authoritative cost evidence is complete, verifies observed
  transaction-cost evidence is attached to comparison metrics, and checks the diagnostics payload
  includes method plan, enrichment reason codes, and authority context source provenance.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over `construction_supportability_application.py`,
  focused supportability-application/enrichment/API regressions
  (`tests/unit/dpm/construction/test_supportability_application.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 51 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: add direct supportability-application tests for ESG and liquidity-aware status
  overlays before changing those branches.
- Wiki decision: no wiki source change required; this is internal test hardening with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-279: Supportability application ESG and liquidity coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_supportability_application.py` and
  `docs/architecture/CODEBASE-REVIEW-LEDGER.md`.
- Finding: the extracted supportability application helper had direct coverage for COST_AWARE
  transaction-cost evidence, but ESG_AWARE restriction constraints and LIQUIDITY_AWARE status
  overlays were still only covered indirectly through broader construction service/API tests.
- Action: added direct supportability-application tests for ESG client-restriction blocking and
  liquidity policy pending-review overlay. The tests verify method status roll-up, constraint
  trace evidence, enrichment reason-code propagation, and authority-context diagnostic provenance.
- Status: hardened
- Evidence: focused Ruff checks, focused mypy over `construction_supportability_application.py`,
  focused supportability-application/enrichment/API regressions
  (`tests/unit/dpm/construction/test_supportability_application.py`,
  `tests/unit/dpm/construction/test_enrichment.py`, and
  `tests/unit/dpm/api/test_construction_api.py`) passed with 53 tests. OpenAPI quality, API
  vocabulary validation, service leakage scan, and `git diff --check` passed.
- Follow-up: continue adding direct branch-level coverage before modifying status roll-up or
  diagnostic assembly internals.
- Wiki decision: no wiki source change required; this is internal test hardening with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-280: Liquidity source-product mapper split

- Date: 2026-06-01
- Scope: `src/api/services/construction_liquidity_source_context.py`,
  `src/api/services/construction_source_product_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`, and this ledger.
- Finding: liquidity-family source-product mapping had been correctly extracted from construction
  orchestration but remained embedded in the broader source-product context helper alongside
  transaction-cost, external treasury, client restriction, sustainability, and execution evidence.
- Action: moved the liquidity cashflow, income-needs, reserve-requirement, planned-withdrawal, and
  source-status mapping helpers into a dedicated liquidity source-context module. The broader helper
  now imports and re-exports those functions while retaining authority-context composition, keeping
  existing callers stable and making the pure liquidity mapping boundary easier to review directly.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_liquidity_source_context.py` and
  `construction_source_product_context.py`; focused source-product/enrichment regressions passed
  with 41 tests.
- Follow-up: continue splitting non-liquidity source-product families when the next slice touches
  their mapping logic, while preserving the authority-context facade for call-site stability.
- Wiki decision: no wiki source change required; this is internal module factoring with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-281: Client profile source-product mapper split

- Date: 2026-06-01
- Scope: `src/api/services/construction_client_profile_source_context.py`,
  `src/api/services/construction_source_product_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`, and this ledger.
- Finding: client restriction and sustainability preference source-product mapping was pure
  source-boundary assembly, but it still lived in the broad construction source-product facade after
  the liquidity family was separated.
- Action: moved client restriction profile and sustainability preference profile mapping into a
  dedicated client-profile source-context helper. The construction source-product facade imports and
  re-exports the functions so existing authority-context composition remains stable while direct
  tests target the narrower source-family module.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_client_profile_source_context.py` and
  `construction_source_product_context.py`; focused source-product/enrichment regressions passed
  with 41 tests.
- Follow-up: continue decomposing the remaining transaction-cost, external treasury, and execution
  acknowledgement mapping families as independent slices.
- Wiki decision: no wiki source change required; this is internal module factoring with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-282: Transaction-cost source-product mapper split

- Date: 2026-06-01
- Scope: `src/api/services/construction_transaction_cost_source_context.py`,
  `src/api/services/construction_source_product_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`, and this ledger.
- Finding: transaction-cost curve source-product mapping was direct source-boundary evidence
  assembly, but it remained in the mixed construction source-product facade after the liquidity and
  client-profile families were separated.
- Action: moved transaction-cost curve mapping into a dedicated transaction-cost source-context
  helper. The facade continues importing and re-exporting the function for authority-context
  composition stability, while direct tests now import the narrower source-family helper.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_transaction_cost_source_context.py` and
  `construction_source_product_context.py`; focused source-product/enrichment regressions passed
  with 41 tests.
- Follow-up: split external treasury and execution acknowledgement mapping into their own helpers
  before changing their fail-closed source-boundary behavior.
- Wiki decision: no wiki source change required; this is internal module factoring with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-283: Execution acknowledgement source-product mapper split

- Date: 2026-06-01
- Scope: `src/api/services/construction_execution_source_context.py`,
  `src/api/services/construction_source_product_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`, and this ledger.
- Finding: external order execution acknowledgement mapping was fail-closed source-boundary
  evidence assembly, but it still lived in the mixed construction source-product facade.
- Action: moved external order execution acknowledgement mapping into a dedicated execution
  source-context helper. The facade continues importing and re-exporting the helper for
  authority-context composition stability, and direct tests now import the narrower module.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_execution_source_context.py` and
  `construction_source_product_context.py`; focused source-product/enrichment regressions passed
  with 41 tests.
- Follow-up: isolate the remaining external treasury currency-overlay source mapper as its own
  fail-closed source-boundary helper.
- Wiki decision: no wiki source change required; this is internal module factoring with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-284: Treasury currency-overlay source-product mapper split

- Date: 2026-06-01
- Scope: `src/api/services/construction_treasury_source_context.py`,
  `src/api/services/construction_source_product_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`, and this ledger.
- Finding: the external treasury currency-overlay source mapper was the last large pure
  source-product assembly block in the construction source-product facade, mixing fail-closed
  treasury evidence handling with authority-context composition.
- Action: moved the external hedge readiness, exposure, hedge policy, eligible instrument, and FX
  forward-curve mapping into a dedicated treasury source-context helper. The source-product facade
  now imports and re-exports the helper while retaining only authority-context composition and
  call-site compatibility.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py` and
  `construction_source_product_context.py`; focused source-product/enrichment regressions passed
  with 41 tests.
- Follow-up: keep subsequent changes to treasury fail-closed behavior inside the dedicated helper
  with direct branch coverage for each external source family.
- Wiki decision: no wiki source change required; this is internal module factoring with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-285: Neutral source-product status mapper

- Date: 2026-06-01
- Scope: `src/api/services/construction_source_product_status.py`,
  source-product mapper helpers, `tests/unit/dpm/construction/test_source_product_context.py`, and
  this ledger.
- Finding: after splitting source-product mapping families, non-liquidity mappers still imported the
  source supportability status translator from the liquidity helper, creating an avoidable
  cross-family dependency.
- Action: moved `source_status_to_method_status` into a neutral source-product status helper and
  updated liquidity, client-profile, transaction-cost, execution, treasury, facade, and direct test
  imports to use the shared boundary module.
- Status: hardened
- Evidence: focused Ruff and format checks passed for all touched source/test files; focused mypy
  passed for seven touched source files; focused source-product/enrichment regressions passed with
  41 tests.
- Follow-up: keep cross-family source-boundary utilities in neutral helpers rather than anchoring
  them to one source family.
- Wiki decision: no wiki source change required; this is internal dependency factoring with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-286: Treasury source-context branch coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_source_product_context.py`,
  `src/api/services/construction_treasury_source_context.py`, and this ledger.
- Finding: the dedicated treasury source-context helper had direct coverage for hedge-readiness-only
  fail-closed mapping, but not for fallback source selection or aggregation across all external
  treasury source families.
- Action: added direct tests for currency-exposure fallback behavior and combined external treasury
  evidence aggregation across hedge readiness, currency exposure, hedge policy, eligible hedge
  instruments, and FX forward curves. Assertions cover source ids, row preservation, reason-code
  propagation, and sorted missing-data/blocked-capability evidence.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py`; focused source-product/enrichment
  regressions passed with 43 tests.
- Follow-up: use the new branch tests as guardrails before changing fail-closed treasury behavior or
  adding source-family-specific treasury normalization.
- Wiki decision: no wiki source change required; this is internal test hardening with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-287: Supportability application currency and regime coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_supportability_application.py`,
  `src/api/services/construction_supportability_application.py`, and this ledger.
- Finding: the extracted supportability application helper had direct branch tests for transaction
  costs, ESG restrictions, and liquidity, but currency-overlay and regime-stress context status
  overlays still relied on broader enrichment/API coverage.
- Action: added direct supportability-application tests for blocked currency-overlay authority
  context and blocked regime-stress authority context. The tests assert method status roll-up,
  source reason-code propagation, and authority-context diagnostic provenance.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_supportability_application.py`; focused supportability/enrichment/API
  regressions passed with 55 tests.
- Follow-up: use direct branch tests before refactoring remaining supportability status-rollup or
  diagnostic assembly internals.
- Wiki decision: no wiki source change required; this is internal test hardening with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-288: Supportability status roll-up helper

- Date: 2026-06-01
- Scope: `src/api/services/construction_supportability_application.py`,
  `tests/unit/dpm/construction/test_supportability_application.py`, and this ledger.
- Finding: after extracting supportability application orchestration, method status roll-up still
  lived inline as a sequence of method-specific conditional overlays, making the main helper harder
  to scan and riskier to change.
- Action: moved status roll-up into private helpers for base method status, method enrichment
  statuses, and authority-context status overlays. The public application helper now reads as
  enrichment, method-specific evidence attachment, reason-code collection, status roll-up, and
  diagnostic assembly.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_supportability_application.py`; focused supportability/enrichment/API
  regressions passed with 55 tests.
- Follow-up: keep additional supportability branches behind direct tests before changing roll-up
  semantics.
- Wiki decision: no wiki source change required; this is internal service factoring with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-289: Source-context test import boundary

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_enrichment.py`,
  `src/api/services/construction_source_product_context.py`, and this ledger.
- Finding: enrichment tests still imported treasury source mapping and source-product status mapping
  through the broad source-product facade after those helpers had been split into focused modules.
  That kept direct tests coupled to a compatibility facade instead of the modules they prove.
- Action: moved enrichment test imports for treasury source mapping and source-product status mapping
  to their focused modules, leaving the facade import only for authority-context composition.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test/source files; focused mypy
  passed for `construction_source_product_context.py`,
  `construction_source_product_status.py`, and `construction_treasury_source_context.py`; focused
  enrichment/source-product regressions passed with 43 tests.
- Follow-up: avoid adding new tests for split mapper modules through the source-product facade unless
  the facade composition behavior itself is under test.
- Wiki decision: no wiki source change required; this is internal test-boundary cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-290: Source-product facade export narrowing

- Date: 2026-06-01
- Scope: `src/api/services/construction_source_product_context.py`,
  source-product/enrichment tests, and this ledger.
- Finding: after mapper-family extraction and test import realignment, the source-product facade
  still re-exported individual mapper helpers. That kept the broad module's surface larger than its
  remaining responsibility: authority-context composition from source products.
- Action: narrowed the facade exports to `authority_context_with_source_products` and
  `source_product_authority_context_updates`, and removed unused re-export-only imports. Split
  mapper helpers remain available from their family-specific modules.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_source_product_context.py`; focused source-product/enrichment
  regressions passed with 43 tests.
- Follow-up: keep the facade limited to composition; import source-family mappers directly in tests
  or code that exercises those mapping contracts.
- Wiki decision: no wiki source change required; this is internal API-surface narrowing for services
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-291: Source-product status test split

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_source_product_status.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`,
  `src/api/services/construction_source_product_status.py`, and this ledger.
- Finding: the neutral source-product status mapper test still lived in the broader source-product
  context test module after the mapper moved to its own helper.
- Action: moved the fail-closed status mapping test into a focused status test module and removed
  the now-unneeded status import from the source-product context tests.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_source_product_status.py`; focused source-product status/context
  regressions passed with 18 tests.
- Follow-up: continue splitting source-product test coverage by source family as the next mapper
  areas are touched.
- Wiki decision: no wiki source change required; this is internal test modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-292: Execution source-context test split

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_execution_source_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`,
  `src/api/services/construction_execution_source_context.py`, and this ledger.
- Finding: direct external order execution acknowledgement mapper coverage still lived in the broad
  source-product context test module after the execution mapper had been extracted.
- Action: moved direct execution acknowledgement fail-closed tests into a focused execution
  source-context test module, leaving the broad source-product context tests to cover
  authority-context composition.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_execution_source_context.py`; focused execution/context regressions
  passed with 17 tests.
- Follow-up: continue splitting direct source-family mapper tests away from the source-product
  composition suite.
- Wiki decision: no wiki source change required; this is internal test modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-293: Transaction-cost source-context test split

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_transaction_cost_source_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`,
  `src/api/services/construction_transaction_cost_source_context.py`, and this ledger.
- Finding: direct transaction-cost curve mapper coverage still lived in the broad source-product
  context test module after transaction-cost mapping had been extracted.
- Action: moved transaction-cost source mapper tests into a focused transaction-cost source-context
  test module, keeping the broad source-product context tests focused on authority-context
  composition behavior.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_transaction_cost_source_context.py`; focused transaction-cost/context
  regressions passed with 15 tests.
- Follow-up: continue splitting direct source-family mapper tests by liquidity, client profile, and
  treasury families.
- Wiki decision: no wiki source change required; this is internal test modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-294: Client-profile source-context test split

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_client_profile_source_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`,
  `src/api/services/construction_client_profile_source_context.py`, and this ledger.
- Finding: direct client restriction and sustainability preference mapper coverage still lived in
  the broad source-product context test module after client-profile mapping had been extracted.
- Action: moved client-profile source mapper tests into a focused client-profile source-context test
  module and removed now-stale imports from the composition test.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_client_profile_source_context.py`; focused client-profile/context
  regressions passed with 14 tests.
- Follow-up: continue splitting liquidity and treasury direct source-family tests out of the
  composition suite.
- Wiki decision: no wiki source change required; this is internal test modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-295: Liquidity source-context test split

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_liquidity_source_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`,
  `src/api/services/construction_liquidity_source_context.py`, and this ledger.
- Finding: direct liquidity-family mapper coverage still lived in the broad source-product context
  test module after liquidity mapping had been extracted.
- Action: moved cashflow projection, client income-needs, liquidity reserve, planned withdrawal, and
  source liquidity policy tests into a focused liquidity source-context test module, leaving the
  broad source-product context tests focused on authority-context composition.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_liquidity_source_context.py`; focused liquidity/context regressions
  passed with 12 tests.
- Follow-up: split treasury direct source-family tests out of the composition suite next.
- Wiki decision: no wiki source change required; this is internal test modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-296: Treasury source-context test split

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_treasury_source_context.py`,
  `tests/unit/dpm/construction/test_source_product_context.py`,
  `src/api/services/construction_treasury_source_context.py`, and this ledger.
- Finding: direct external treasury mapper coverage still lived in the broad source-product context
  test module after treasury mapping had been extracted.
- Action: moved hedge-readiness, exposure fallback, combined treasury source evidence, and absent
  source tests into a focused treasury source-context test module. The source-product context suite
  now covers facade composition only.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py`; focused treasury/context regressions passed
  with 6 tests.
- Follow-up: use the smaller source-product context suite as the guardrail for composition-only
  changes and keep source-family contract tests in their focused modules.
- Wiki decision: no wiki source change required; this is internal test modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-297: Shared execution and transaction source fixtures

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/source_product_context_fixtures.py`,
  execution, transaction-cost, and source-product context tests, and this ledger.
- Finding: after splitting source-family tests, the execution acknowledgement and transaction-cost
  source response builders were duplicated between focused mapper tests and the facade composition
  tests.
- Action: extracted shared source-product fixture builders for external order acknowledgement and
  transaction-cost curve responses, then updated the focused tests and composition tests to reuse
  them.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test files; focused mypy passed
  for the related source modules; focused execution/transaction/source-product context regressions
  passed with 5 tests.
- Follow-up: continue moving remaining liquidity, client-profile, and treasury source response
  builders into shared fixtures as those test modules are touched.
- Wiki decision: no wiki source change required; this is internal test duplication cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-298: Shared liquidity source fixtures

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/source_product_context_fixtures.py`,
  liquidity and source-product context tests, and this ledger.
- Finding: liquidity source response builders were duplicated between focused liquidity mapper tests
  and the source-product composition tests.
- Action: moved cashflow projection, client income-needs, liquidity reserve, and planned withdrawal
  source response builders into shared source-product fixtures and updated both test modules to use
  them.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test files; focused mypy passed
  for the related liquidity/source-product source modules; focused liquidity/source-product context
  regressions passed with 8 tests.
- Follow-up: continue extracting client-profile and treasury response builders from duplicated test
  modules.
- Wiki decision: no wiki source change required; this is internal test duplication cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-299: Shared client-profile source fixtures

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/source_product_context_fixtures.py`,
  client-profile and source-product context tests, and this ledger.
- Finding: client restriction and sustainability preference source response builders were duplicated
  between focused client-profile mapper tests and the source-product composition tests.
- Action: moved the client restriction profile and sustainability preference profile response
  builders into shared source-product fixtures and updated both test modules to reuse them.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test files; focused mypy passed
  for the related client-profile/source-product source modules; focused client-profile/source-product
  context regressions passed with 4 tests.
- Follow-up: extract treasury source response builders from duplicated test modules next.
- Wiki decision: no wiki source change required; this is internal test duplication cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-300: Shared treasury source fixtures

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/source_product_context_fixtures.py`,
  treasury and source-product context tests, and this ledger.
- Finding: external treasury source response builders were duplicated between the focused treasury
  mapper tests and the source-product composition tests.
- Action: moved hedge-readiness, currency exposure, hedge policy, eligible hedge instrument, and FX
  forward-curve source response builders into shared source-product fixtures and updated both test
  modules to reuse them.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test files; focused mypy passed
  for the related treasury/source-product source modules; focused treasury/source-product context
  regressions passed with 6 tests.
- Follow-up: continue shrinking construction test support by keeping shared fixtures in the fixture
  module and source-family assertions in focused mapper suites.
- Wiki decision: no wiki source change required; this is internal test duplication cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-301: Treasury source payload hashing helpers

- Date: 2026-06-01
- Scope: `src/api/services/construction_treasury_source_context.py`, treasury source-context tests,
  and this ledger.
- Finding: treasury source mapping repeated optional `model_dump` and source-hash handling for each
  external treasury source family, making the mapper longer without adding domain meaning.
- Action: introduced small internal helpers for optional source payload extraction and content-hash
  derivation, then reused them across the treasury mapper.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py`; focused treasury source-context regressions
  passed with 4 tests.
- Follow-up: continue reducing treasury mapper repetition around supportability evidence while
  preserving explicit source-family fields.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-302: Treasury supportability evidence helpers

- Date: 2026-06-01
- Scope: `src/api/services/construction_treasury_source_context.py`, treasury source-context tests,
  and this ledger.
- Finding: treasury source mapping repeated optional missing-data and blocked-capability extraction
  for each external treasury source family.
- Action: added small internal helpers for optional supportability evidence access and reused them
  in the aggregate missing-data and blocked-capability rollups.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py`; focused treasury source-context regressions
  passed with 4 tests.
- Follow-up: keep explicit source-family field mapping in place while extracting only repeated
  mechanics that do not encode separate treasury business rules.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-303: Treasury aggregate supportability rollups

- Date: 2026-06-01
- Scope: `src/api/services/construction_treasury_source_context.py`, treasury source-context tests,
  and this ledger.
- Finding: the treasury mapper still carried temporary per-source missing-data and
  blocked-capability variables solely to build sorted aggregate supportability rollups.
- Action: introduced internal aggregate helpers for merged missing-data families and blocked
  capabilities, then used them directly in the currency-overlay context construction.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py`; focused treasury source-context regressions
  passed with 4 tests.
- Follow-up: continue improving treasury source mapping readability without hiding product-specific
  source lineage and count fields.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-304: Treasury fail-closed reason assembly

- Date: 2026-06-01
- Scope: `src/api/services/construction_treasury_source_context.py`, treasury source-context tests,
  and this ledger.
- Finding: fail-closed reason-code assembly in the treasury mapper repeated one presence check per
  external treasury source family.
- Action: extracted ordered fail-closed reason-code assembly into a small internal helper while
  preserving the existing primary reason and source-family reason order.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py`; focused treasury source-context regressions
  passed with 4 tests.
- Follow-up: keep source-family fail-closed reasons explicit and ordered because they are observable
  supportability evidence.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-305: Treasury source id fallback helper

- Date: 2026-06-01
- Scope: `src/api/services/construction_treasury_source_context.py`, treasury source-context tests,
  and this ledger.
- Finding: treasury source-id selection repeated the same source-batch, lineage, and content-hash
  fallback chain across multiple source-family fields.
- Action: extracted source-id fallback selection into a shared internal helper and reused it for the
  primary hedge-readiness source and optional treasury family source IDs.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py`; focused treasury source-context regressions
  passed with 4 tests.
- Follow-up: keep product-specific source-id output fields explicit while sharing the common
  canonical fallback rule.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-306: Liquidity source id fallback helper

- Date: 2026-06-01
- Scope: `src/api/services/construction_liquidity_source_context.py`, liquidity source-context
  tests, and this ledger.
- Finding: liquidity source-family mappers repeated canonical payload hashing and the same
  source-batch, lineage, and content-hash source-id fallback rule.
- Action: added internal liquidity source payload, hash, and source-id helpers and reused them
  across cashflow, income-needs, reserve requirement, and planned withdrawal context mapping.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_liquidity_source_context.py`; focused liquidity source-context
  regressions passed with 6 tests.
- Follow-up: continue consolidating repeated source-product mechanics in mapper helpers without
  changing source-family domain fields.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-307: Liquidity parent reason-code assembly

- Date: 2026-06-01
- Scope: `src/api/services/construction_liquidity_source_context.py`, liquidity source-context
  tests, and this ledger.
- Finding: parent liquidity context construction mixed child-context orchestration with reason-code
  list assembly for optional source families.
- Action: extracted parent liquidity reason-code assembly into a small internal helper keyed by
  income-needs, reserve-requirement, and planned-withdrawal presence.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_liquidity_source_context.py`; focused liquidity source-context
  regressions passed with 6 tests.
- Follow-up: keep the parent liquidity mapper focused on child context construction and governed
  policy fields.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-308: Client-profile source id fallback helper

- Date: 2026-06-01
- Scope: `src/api/services/construction_client_profile_source_context.py`, client-profile
  source-context tests, and this ledger.
- Finding: client restriction and sustainability preference mappers repeated canonical payload
  hashing and source-batch, lineage, and content-hash source-id fallback selection.
- Action: added internal client-profile source payload, hash, and source-id helpers and reused them
  across restriction and sustainability preference profile mapping.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_client_profile_source_context.py`; focused client-profile source-context
  regressions passed with 2 tests.
- Follow-up: use the same explicit source-id fallback helper pattern for remaining source-context
  helpers where repetition appears.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-309: Transaction-cost point mapper

- Date: 2026-06-01
- Scope: `src/api/services/construction_transaction_cost_source_context.py`,
  transaction-cost source-context tests, and this ledger.
- Finding: transaction-cost context mapping embedded per-point row shaping inside the parent context
  constructor, mixing source metadata assembly with bounded curve-point transformation.
- Action: extracted transaction-cost point mapping into a private helper while preserving the
  existing limits of 10 curve points and 5 sample transaction IDs per point.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_transaction_cost_source_context.py`; focused transaction-cost
  source-context regression passed with 1 test.
- Follow-up: keep bounded row shaping close to source-context helpers and covered by direct mapper
  tests.
- Wiki decision: no wiki source change required; this is internal service helper cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-310: Transaction-cost source-id fallback coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_transaction_cost_source_context.py`,
  transaction-cost source-context mapping, and this ledger.
- Finding: transaction-cost source context tests covered lineage source IDs but did not prove the
  page request-scope fingerprint fallback used when source-batch and lineage fingerprints are
  absent.
- Action: added a direct transaction-cost mapper regression asserting fallback to
  `request_scope_fingerprint` as the source ID.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused
  transaction-cost source-context regressions passed with 2 tests.
- Follow-up: add similarly focused fallback tests where source-boundary identity has non-lineage
  fallback behavior.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-311: Execution acknowledgement source-id fallback coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_execution_source_context.py`, execution acknowledgement
  source-context mapping, and this ledger.
- Finding: external order acknowledgement tests covered lineage source IDs but did not prove the
  content-hash fallback used when source-batch and lineage fingerprints are absent.
- Action: added a direct mapper regression asserting source ID fallback to the acknowledgement
  context content hash.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused execution
  source-context regressions passed with 3 tests.
- Follow-up: keep fallback coverage aligned with source-boundary proof for every external source
  family mapper.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-312: Liquidity source-id fallback coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_liquidity_source_context.py`, liquidity source-family
  mapping, and this ledger.
- Finding: liquidity source-family tests covered lineage source IDs but did not prove content-hash
  fallback behavior when source-batch and lineage fingerprints are absent.
- Action: added direct fallback regressions for income needs, reserve requirements, planned
  withdrawals, and cashflow projection source IDs.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused liquidity
  source-context regressions passed with 10 tests.
- Follow-up: keep source-boundary identity fallback coverage close to each source-family mapper.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-313: Client-profile source-id fallback coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_client_profile_source_context.py`, client-profile
  source-family mapping, and this ledger.
- Finding: client-profile source-family tests covered lineage source IDs but did not prove
  content-hash fallback behavior when source-batch and lineage fingerprints are absent.
- Action: added direct fallback regressions for client restriction and sustainability preference
  source IDs.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused client-profile
  source-context regressions passed with 4 tests.
- Follow-up: keep source-boundary fallback coverage aligned with shared source-id helper behavior.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-314: Treasury source-id fallback coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_treasury_source_context.py`, external treasury
  source-family mapping, and this ledger.
- Finding: treasury source-family tests covered lineage source IDs but did not prove content-hash
  fallback behavior when source-batch and lineage fingerprints are absent.
- Action: added a direct fallback regression covering the aggregate hedge-readiness source ID and
  each optional treasury source-family source ID.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused treasury
  source-context regressions passed with 5 tests.
- Follow-up: keep the aggregate treasury hash fallback explicit because the primary context source
  ID intentionally represents the combined source-family payload when hedge-readiness lineage is
  absent.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-315: Source status fail-closed coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_source_product_status.py`, source-product status
  mapping, and this ledger.
- Finding: source status tests proved known non-ready states were blocked but did not explicitly
  cover unknown upstream status values.
- Action: converted the mapper test to a parameterized matrix and added an unknown upstream state
  case that must fail closed to `BLOCKED`.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused source-product
  status regressions passed with 5 tests.
- Follow-up: keep source-supportability translation intentionally conservative as upstream source
  products evolve.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-316: Source-product facade stateless pass-through coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_source_product_context.py`, source-product authority
  context facade behavior, and this ledger.
- Finding: source-product composition tests covered source-family updates but did not directly guard
  the stateless path where no resolved source context is supplied.
- Action: added a direct facade regression asserting the existing authority context is returned
  unchanged when source context is absent.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused
  source-product facade regressions passed with 3 tests.
- Follow-up: keep facade tests focused on orchestration behavior while source-family tests own
  mapper detail.
- Wiki decision: no wiki source change required; this is internal source-composition test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-317: Source-product facade empty-source coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_source_product_context.py`, source-product authority
  context facade behavior, and this ledger.
- Finding: source-product composition tests did not directly guard the empty source-products path
  where a source context object is present but carries no source-family products.
- Action: added a direct facade regression asserting no authority-context updates are produced when
  all source-family products are absent.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused
  source-product facade regressions passed with 4 tests.
- Follow-up: keep facade composition tests focused on update/no-update orchestration boundaries.
- Wiki decision: no wiki source change required; this is internal source-composition test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-318: Client restriction supportability module split

- Date: 2026-06-01
- Scope: `src/api/services/construction_esg_supportability.py`,
  `src/api/services/construction_client_restriction_supportability.py`, ESG supportability tests,
  and this ledger.
- Finding: ESG supportability combined client-restriction rule matching and sustainability
  preference supportability in one service helper, making the module harder to scan and reuse.
- Action: extracted client-restriction supportability status, reason-code, violation, and matching
  helpers into a focused module while preserving the existing ESG facade imports.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the ESG and client-restriction supportability source modules; focused ESG
  supportability regressions passed with 3 tests.
- Follow-up: consider the same split for sustainability preference supportability once the
  client-restriction boundary is stable.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-319: Sustainability supportability module split

- Date: 2026-06-01
- Scope: `src/api/services/construction_esg_supportability.py`,
  `src/api/services/construction_sustainability_supportability.py`, ESG supportability tests, and
  this ledger.
- Finding: after the client-restriction split, sustainability preference allocation, classification,
  status, and reason-code handling still lived inside the ESG facade.
- Action: extracted sustainability preference supportability helpers into a focused module while
  keeping the existing ESG facade import surface stable for callers.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the ESG, client-restriction, and sustainability supportability source modules; focused
  ESG supportability regressions passed with 3 tests.
- Follow-up: add direct tests around sustainability helper edge cases now that the boundary is
  separately reusable.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-320: Direct client restriction supportability tests

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_client_restriction_supportability.py`,
  `tests/unit/dpm/construction/test_esg_supportability.py`, client-restriction supportability, and
  this ledger.
- Finding: after extracting client-restriction supportability into its own helper module, the
  focused behavioral tests still lived in the broader ESG supportability test file.
- Action: moved direct client-restriction supportability and matching tests into a dedicated test
  module and left the ESG supportability test focused on sustainability preference behavior.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the client-restriction and sustainability supportability source modules; focused
  client-restriction and ESG/sustainability regressions passed with 3 tests.
- Follow-up: add a dedicated sustainability supportability test module if additional edge cases
  make the current ESG test filename misleading.
- Wiki decision: no wiki source change required; this is internal test modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-321: Sustainability supportability test rename

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_sustainability_supportability.py`, removed
  `tests/unit/dpm/construction/test_esg_supportability.py`, sustainability supportability tests,
  and this ledger.
- Finding: after direct client-restriction tests were split out, the remaining ESG supportability
  test module only covered sustainability preference supportability behavior.
- Action: renamed the test module to match the extracted sustainability supportability helper
  boundary.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_sustainability_supportability.py`; focused sustainability
  supportability regression passed with 1 test.
- Follow-up: keep the ESG facade covered by higher-level construction supportability tests and
  direct helper modules for domain-specific behavior.
- Wiki decision: no wiki source change required; this is internal test navigation cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-322: Client restriction supportability edge coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_client_restriction_supportability.py`,
  client-restriction supportability, and this ledger.
- Finding: direct client-restriction supportability tests covered a blocking active buy rule but did
  not prove fail-soft absence handling or inactive/non-applicable rule handling.
- Action: added direct regressions for missing source profile degradation and for inactive or
  non-buy-applicable restrictions applying no block while still recording profile-applied evidence.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused
  client-restriction supportability regressions passed with 4 tests.
- Follow-up: keep rule applicability tests explicit so client mandate restrictions remain auditable
  as supported scopes expand.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-323: Sustainability supportability edge coverage

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_sustainability_supportability.py`,
  sustainability supportability, and this ledger.
- Finding: direct sustainability supportability tests covered review-triggering active preferences
  but did not prove missing source-profile degradation or inactive preference handling.
- Action: added direct regressions for unavailable source profile degradation and inactive
  sustainability preferences applying no allocation/classification review findings.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test file; focused
  sustainability supportability regressions passed with 3 tests.
- Follow-up: keep preference-status handling explicit as sustainability preference schemas expand.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-324: Liquidity supportability module split

- Date: 2026-06-01
- Scope: `src/api/services/construction_method_supportability.py`,
  `src/api/services/construction_liquidity_supportability.py`, construction method supportability
  tests, and this ledger.
- Finding: construction method supportability combined liquidity policy, currency overlay, and
  regime-stress supportability in one helper module.
- Action: extracted liquidity status, reason-code, cashflow projection, cash-weight, and derived
  liquidity policy helpers into a focused module while preserving the existing method-supportability
  facade imports.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the method and liquidity supportability source modules; focused method supportability
  regressions passed with 3 tests.
- Follow-up: split currency overlay and regime-stress supportability into focused modules if the
  method-supportability facade continues to carry mixed domain logic.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-325: Direct liquidity supportability tests

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_liquidity_supportability.py`,
  `tests/unit/dpm/construction/test_method_supportability.py`, liquidity supportability, and this
  ledger.
- Finding: after extracting liquidity supportability into a focused module, the direct liquidity
  policy test still lived in the broader method-supportability test module.
- Action: moved the liquidity policy supportability regression into a dedicated test module and
  trimmed now-unused method-supportability fixtures/imports.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the liquidity and method supportability source modules; focused liquidity and method
  supportability regressions passed with 3 tests.
- Follow-up: keep method-supportability facade tests focused on the remaining non-liquidity
  supportability functions until those are split.
- Wiki decision: no wiki source change required; this is internal test modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-326: Currency overlay supportability module split

- Date: 2026-06-01
- Scope: `src/api/services/construction_method_supportability.py`,
  `src/api/services/construction_currency_overlay_supportability.py`, construction method
  supportability tests, and this ledger.
- Finding: after the liquidity split, construction method supportability still mixed
  currency-overlay policy derivation, missing-pair detection, and status handling with the
  regime-stress facade.
- Action: extracted currency-overlay supportability into a focused helper module while preserving
  the existing method-supportability facade imports for callers.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the method and currency-overlay supportability source modules; focused method
  supportability regressions passed with 2 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: move direct currency-overlay tests into a dedicated test module, then split
  regime-stress supportability out of the method facade.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-327: Direct currency overlay supportability tests

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_currency_overlay_supportability.py`,
  `tests/unit/dpm/construction/test_method_supportability.py`, currency-overlay supportability, and
  this ledger.
- Finding: after extracting currency-overlay supportability into a focused module, the direct
  missing-FX-pair regression still lived in the broader method-supportability test module and did
  not cover missing context or unsupported-currency review behavior.
- Action: moved currency-overlay regressions into a dedicated test module and added focused coverage
  for missing source context degradation and unsupported currency pending-review handling.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the currency-overlay supportability source module; focused currency-overlay and method
  supportability regressions passed with 4 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: keep `test_method_supportability.py` narrowed to regime-stress behavior until
  regime-stress supportability is extracted into its own helper.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-328: Regime stress supportability module split

- Date: 2026-06-01
- Scope: `src/api/services/construction_method_supportability.py`,
  `src/api/services/construction_regime_stress_supportability.py`, construction method
  supportability tests, and this ledger.
- Finding: after liquidity and currency-overlay extraction, the method-supportability facade still
  owned the regime-stress threshold evaluation directly.
- Action: extracted regime-stress supportability status handling into a focused helper module while
  preserving the existing method-supportability facade export for callers.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the method and regime-stress supportability source modules; focused method
  supportability regression passed with 1 test; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: move direct regime-stress tests into a dedicated test module and leave
  `construction_method_supportability.py` as a compatibility facade only.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-329: Direct regime stress supportability tests

- Date: 2026-06-01
- Scope: `tests/unit/dpm/construction/test_regime_stress_supportability.py`,
  `tests/unit/dpm/construction/test_method_supportability.py`, regime-stress supportability, and
  this ledger.
- Finding: after extracting regime-stress supportability, the direct threshold-breach regression
  still lived in the broader method-supportability test module and did not prove missing source
  context or non-breach source-status preservation.
- Action: moved regime-stress supportability regressions into a dedicated test module, added
  missing-context and no-threshold-breach cases, and narrowed the method-supportability test to the
  facade export contract.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for the method and regime-stress supportability source modules; focused regime-stress and
  method supportability regressions passed with 4 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue shrinking `construction_service.py` and keep compatibility facades thin,
  covered, and explicit.
- Wiki decision: no wiki source change required; this is internal source-boundary test hardening
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-330: Construction alternative set lineage helper

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py`,
  `src/api/services/construction_alternative_set_lineage.py`,
  `tests/unit/dpm/construction/test_alternative_set_lineage.py`, construction API regressions, and
  this ledger.
- Finding: `construction_service.py` still assembled alternative-set request hash, input mode, and
  source-supportability lineage inline inside the generation orchestration path.
- Action: extracted alternative-set lineage field assembly into a focused helper that reuses the
  existing rebalance source-lineage input-mode convention, with direct stateless and stateful
  coverage.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_service.py` and `construction_alternative_set_lineage.py`; direct
  alternative-set lineage tests passed with 2 tests; selected construction API regressions for
  first-wave replay and stateful source behavior passed with 2 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: keep pure metadata/source-boundary assembly out of `construction_service.py` while
  preserving method orchestration there.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-331: Persistable construction alternative set assembly

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py`,
  `src/api/services/construction_alternative_set_assembly.py`,
  `tests/unit/dpm/construction/test_alternative_set_assembly.py`, construction API regressions, and
  this ledger.
- Finding: construction generation orchestration still owned pure alternative-set assembly details:
  generated alternative-set identity, business as-of date, request hash, input mode, and
  source-supportability lineage fields.
- Action: extracted persistable alternative-set assembly into a focused helper with deterministic
  identity/as-of injection for direct tests while leaving method execution orchestration in
  `construction_service.py`.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_service.py`, `construction_alternative_set_assembly.py`, and
  `construction_alternative_set_lineage.py`; direct alternative-set assembly and lineage tests
  passed with 3 tests; selected construction API regressions for first-wave replay and stateful
  source behavior passed with 2 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue keeping construction generation orchestration readable by extracting only pure
  assembly or source-boundary helpers.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-332: Construction selection assembly helper

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py`,
  `src/api/services/construction_selection.py`,
  `tests/unit/dpm/construction/test_construction_selection.py`, construction API selection
  regressions, and this ledger.
- Finding: construction selection orchestration still mixed repository lookup/save with pure
  alternative membership validation and selection model assembly.
- Action: extracted construction selection validation and model assembly into a focused helper with
  deterministic selection-id injection for direct tests, leaving repository orchestration in
  `construction_service.py`.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_service.py` and `construction_selection.py`; direct construction
  selection tests passed with 2 tests; selected construction API selection regression passed with 1
  test; OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: keep service-level selection behavior covered by API tests while direct helper tests
  own deterministic validation and model assembly.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-333: Construction alternative builder extraction

- Date: 2026-06-01
- Scope: `src/api/services/construction_service.py`,
  `src/api/services/construction_alternative_builder.py`,
  `tests/unit/dpm/construction/test_alternative_builder.py`, construction API generation
  regressions, and this ledger.
- Finding: construction generation orchestration still embedded the method loop that resolved
  method plans, ran non-heuristic effective methods, wrapped rebalance results as alternatives, and
  applied supportability.
- Action: extracted alternative construction into a dedicated builder module with direct coverage
  for method ordering, baseline handling, effective-method execution, method-plan diagnostics, and
  request-hash suffix preservation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_service.py` and `construction_alternative_builder.py`; direct
  alternative-builder regression passed with 1 test; selected construction API generation
  regressions for first-wave replay and turnover-budget pending review passed with 2 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: keep `construction_service.py` limited to request hashing, idempotency, persistence,
  and high-level orchestration while method execution/build policy lives in focused helpers.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-334: Shared construction source identity helpers

- Date: 2026-06-01
- Scope: `src/api/services/construction_source_identity.py`,
  `src/api/services/construction_liquidity_source_context.py`,
  `src/api/services/construction_client_profile_source_context.py`,
  `tests/unit/dpm/construction/test_source_identity.py`, liquidity/client profile source-context
  tests, and this ledger.
- Finding: liquidity and client-profile source-context mappers duplicated canonical payload
  extraction, source content hashing, and top-level/lineage source-batch fingerprint fallback logic.
- Action: extracted shared source identity helpers for canonical source payloads, content hashes,
  and source-id fallback ordering, then rewired liquidity and client-profile source mappers to use
  them.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_source_identity.py`, `construction_liquidity_source_context.py`, and
  `construction_client_profile_source_context.py`; direct source identity, liquidity source-context,
  and client-profile source-context regressions passed with 17 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: consider migrating treasury, execution acknowledgement, and transaction-cost
  source-context mappers to the same helper where their source-id fallback semantics match.
- Wiki decision: no wiki source change required; this is internal source-boundary modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-335: Source identity reuse for cost and execution evidence

- Date: 2026-06-01
- Scope: `src/api/services/construction_transaction_cost_source_context.py`,
  `src/api/services/construction_execution_source_context.py`,
  `src/api/services/construction_source_identity.py`, transaction-cost/execution source-context
  tests, and this ledger.
- Finding: transaction-cost and external execution acknowledgement source-context mappers still
  duplicated canonical payload hashing and source-batch fingerprint fallback logic after the shared
  source identity helper was introduced.
- Action: rewired transaction-cost and external execution acknowledgement mappers to reuse the
  shared source identity helper while preserving transaction-cost page-fingerprint fallback and
  execution acknowledgement content-hash fallback semantics.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_source_identity.py`,
  `construction_transaction_cost_source_context.py`, and
  `construction_execution_source_context.py`; direct transaction-cost source-context, execution
  source-context, and source-identity regressions passed with 8 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: migrate treasury source-context identity helpers only if aggregate hash and per-source
  fallback behavior can be preserved without weakening source-boundary proof.
- Wiki decision: no wiki source change required; this is internal source-boundary modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-336: Treasury source identity helper reuse

- Date: 2026-06-01
- Scope: `src/api/services/construction_treasury_source_context.py`,
  `src/api/services/construction_source_identity.py`, treasury source-context tests, and this
  ledger.
- Finding: treasury source-context mapping retained local optional payload, per-source hash, and
  source-id fallback helpers after shared construction source identity helpers were introduced.
- Action: rewired optional treasury source payload/hash/source-id handling through the shared
  source identity helpers while preserving the aggregate currency-overlay content hash and
  fail-closed per-source fallback semantics.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py` and `construction_source_identity.py`;
  treasury source-context and source-identity regressions passed with 8 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: keep aggregate source-boundary hash behavior explicit when consolidating additional
  source-product mapper utilities.
- Wiki decision: no wiki source change required; this is internal source-boundary modularity cleanup
  with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-337: Liquidity source-context export surface cleanup

- Date: 2026-06-01
- Scope: `src/api/services/construction_liquidity_source_context.py`,
  `tests/unit/dpm/construction/test_liquidity_source_context.py`, and this ledger.
- Finding: the liquidity source-context mapper still re-exported
  `source_status_to_method_status`, even though status mapping now lives in the dedicated source
  product status helper and no callers import it through the liquidity module.
- Action: removed the stale liquidity-module export and added a direct module-surface regression so
  the mapper publicly exposes only liquidity source-context functions.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_liquidity_source_context.py`; direct liquidity source-context
  regressions passed with 11 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: keep source mapper `__all__` surfaces narrow as helper modules are consolidated.
- Wiki decision: no wiki source change required; this is internal source-boundary module-surface
  cleanup with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-338: Source-context export surface coverage

- Date: 2026-06-01
- Scope: client-profile, transaction-cost, execution acknowledgement, and treasury source-context
  unit tests plus this ledger.
- Finding: after source-identity helper consolidation, most source-context mappers had explicit
  `__all__` surfaces but only liquidity source context had direct module-surface coverage.
- Action: added focused export-surface regressions for client-profile, transaction-cost, execution
  acknowledgement, and treasury source-context modules so their public mapper boundaries remain
  intentional.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched test files; source-context
  regression set passed with 18 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: add module-surface coverage alongside future source-context mapper extractions when
  helper consolidation changes public imports.
- Wiki decision: no wiki source change required; this is internal test hardening for mapper module
  boundaries with no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-339: Wave supportability diagnostics extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_supportability_diagnostics.py`,
  `tests/unit/dpm/waves/test_wave_supportability_diagnostics.py`, wave supportability API
  regressions, and this ledger.
- Finding: `wave_service.py` still owned pure supportability diagnostics policy for issue
  filtering, severity, source-owner classification, remediation routing, and operator action
  selection.
- Action: extracted wave supportability diagnostics into a focused helper module, preserved the
  existing wave service private helper alias for compatibility, and added direct tests for
  completed-item filtering, explicit owner/action preservation, and sorted remediation routes.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_supportability_diagnostics.py`; direct wave
  supportability diagnostics and selected wave supportability API regressions passed with 7 tests;
  OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue shrinking `wave_service.py` by extracting additional pure clusters while
  keeping repository orchestration and router concerns separate.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-340: Wave boundary evidence extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_boundary_evidence.py`,
  `tests/unit/dpm/waves/test_wave_boundary_evidence.py`, proof-pack posture boundary regressions,
  and this ledger.
- Finding: `wave_service.py` still assembled external-execution and client-communication boundary
  evidence directly inside the service module.
- Action: extracted wave boundary evidence builders into a focused module with direct tests for
  no-execution-owner, unsafe execution claim, and no-client-communication-owner cases while
  preserving the existing wave service private aliases.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_boundary_evidence.py`; direct wave boundary evidence and
  selected proof-pack posture boundary regressions passed with 7 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue moving pure wave evidence assembly out of `wave_service.py` while retaining
  workflow orchestration and repository access in the service layer.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-341: Wave proof-pack posture extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_proof_pack_posture.py`,
  `tests/unit/dpm/waves/test_wave_proof_pack_posture.py`, selected wave proof-pack API
  regressions, and this ledger.
- Finding: `wave_service.py` still assembled proof-pack posture directly, mixing evidence summary
  assembly with workflow service orchestration.
- Action: extracted proof-pack posture assembly into a focused helper module backed by the wave
  boundary evidence builders, preserved the `wave_service.proof_pack_posture_for_wave` import
  surface for existing callers, and added direct tests for proof-pack counting, boundary evidence,
  unlinked item filtering, and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_proof_pack_posture.py`; direct wave proof-pack posture
  tests and selected proof-pack API regressions passed with 7 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: continue extracting pure wave evidence and handoff assembly clusters from
  `wave_service.py` while leaving repository orchestration in the service layer.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-342: Wave handoff evidence extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_handoff_evidence.py`,
  `tests/unit/dpm/waves/test_wave_handoff_evidence.py`, selected wave handoff API regressions, and
  this ledger.
- Finding: `wave_service.py` still owned internal operations handoff reference assembly and hashing,
  even though the logic is pure evidence construction rather than workflow orchestration.
- Action: extracted handoff reference and content-hash builders into a focused helper module,
  preserved the existing wave service private alias for orchestration, and added direct tests for
  internal handoff boundary metadata, optional comments, stable hash canonicalization, and the module
  export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_handoff_evidence.py`; direct wave handoff evidence tests
  and selected handoff API regressions passed with 7 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue extracting pure wave item-transition assembly from `wave_service.py` while
  keeping repository writes, version conflict handling, and route-facing lookup behavior in the
  service layer.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-343: Wave item transition extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_item_transitions.py`,
  `tests/unit/dpm/waves/test_wave_item_transitions.py`, selected wave approve/stage/handoff/cancel
  API regressions, and this ledger.
- Finding: `wave_service.py` still owned item-level approve, stage, handoff, and cancel model-copy
  assembly even though those transformations are deterministic item transitions rather than
  repository orchestration.
- Action: extracted item transition builders into a focused helper module, preserved existing
  private aliases in the wave service orchestration, and added direct tests for transition
  diagnostics, no-external-execution markers, no-op states, handoff-ready cancellation preservation,
  and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_item_transitions.py`; direct wave item transition tests and
  selected approve/stage/handoff/cancel API regressions passed with 9 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue shrinking `wave_service.py` by extracting pure wave trigger, source-ref, and
  diagnostics assembly while keeping state-machine orchestration in the service layer.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-344: Wave portfolio source extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_portfolio_sources.py`,
  `tests/unit/dpm/waves/test_wave_portfolio_sources.py`, selected wave create/search/source helper
  API regressions, and this ledger.
- Finding: `wave_service.py` still owned source-ref flattening, portfolio diagnostics normalization,
  and optional string normalization for affected portfolio payloads, increasing the service module's
  non-orchestration surface.
- Action: extracted portfolio source helpers into a focused module, preserved existing private
  aliases in `wave_service.py`, and added direct tests for source-ref validation, trigger-level
  flattening, diagnostics filtering, optional string normalization, and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_portfolio_sources.py`; full direct portfolio-source tests
  passed with 7 tests; selected wave create/search/source helper API regressions passed with 19
  tests; OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue extracting pure wave aggregate and event assembly from `wave_service.py`
  while leaving state transitions and repository conflict handling in the service layer.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-345: Wave aggregate metrics extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_aggregate_metrics.py`,
  `tests/unit/dpm/waves/test_wave_aggregate_metrics.py`, selected wave simulation/create aggregate
  API regressions, and this ledger.
- Finding: `wave_service.py` still calculated aggregate metrics and simulation result state directly,
  keeping deterministic state-counting logic inside the orchestration module.
- Action: extracted aggregate metric and simulation result classifiers into a focused helper module,
  preserved the existing private aliases in `wave_service.py`, and added direct tests for ready,
  blocked, review, degraded, full simulation, partial simulation, failed simulation, and export
  surfaces.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_aggregate_metrics.py`; direct wave aggregate metric tests
  and selected simulation/create API regressions passed with 19 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: continue extracting pure event and validation helpers from `wave_service.py` while
  preserving repository orchestration and state-machine boundaries.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-346: Wave event evidence extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_event_evidence.py`,
  `tests/unit/dpm/waves/test_wave_event_evidence.py`, selected wave create/idempotency/append-event
  API regressions, and this ledger.
- Finding: `wave_service.py` still built wave audit events and canonical request/idempotency hashes
  directly, keeping deterministic evidence construction inside the orchestration module.
- Action: extracted wave event construction, canonical request hashing, and idempotency-key hashing
  into a focused helper module, preserved existing private aliases in `wave_service.py`, and added
  direct tests for audit fields, custom event types, canonical hash stability, idempotency hash
  shape, and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_event_evidence.py`; full direct wave event evidence tests
  passed with 5 tests; selected wave create/idempotency/append-event API regressions passed with 13
  tests; OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: keep `_append_event` in the service layer until validation-error ownership can be moved
  without coupling helper modules back to service exceptions; continue extracting remaining pure
  wave item construction and trigger-validation logic.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-347: Wave item builder extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_item_builder.py`,
  `tests/unit/dpm/waves/test_wave_item_builder.py`, selected wave preview/create/source API
  regressions, and this ledger.
- Finding: `wave_service.py` still assembled affected-portfolio wave items directly, including
  portfolio source evidence, mandate digital-twin source refs, candidate diagnostics, and
  source-blocked diagnostics.
- Action: extracted affected-portfolio item construction into a focused helper module, preserved
  service-private compatibility aliases for existing source helper tests, and added direct tests for
  source-ready item construction, mandate twin enrichment, source-blocked construction, and the
  module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_item_builder.py`; full direct wave item builder tests
  passed with 4 tests; selected wave preview/create/source API regressions passed with 84 tests;
  OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue extracting trigger validation and construction/proof-pack item selection
  helpers while keeping repository orchestration and version-conflict handling in `wave_service.py`.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-348: Wave trigger validation extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_trigger_validation.py`,
  `tests/unit/dpm/waves/test_wave_trigger_validation.py`, selected wave trigger/create API
  regressions, and this ledger.
- Finding: `wave_service.py` still owned supported trigger policy and affected-portfolio set
  validation directly, mixing trigger contract policy with preview/create orchestration.
- Action: extracted trigger validation policy into a focused helper that returns bounded validation
  failures, kept service-local translation to `DpmWaveValidationError`, and added direct tests for
  supported private-banking trigger types, unsupported trigger failures, empty portfolio failures,
  and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_trigger_validation.py`; direct trigger validation tests and
  selected trigger/create API regressions passed with 34 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue extracting construction/proof-pack item selection helpers while preserving
  workflow orchestration and repository error handling in `wave_service.py`.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-349: Wave construction diagnostics extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_construction_diagnostics.py`,
  `tests/unit/dpm/waves/test_wave_construction_diagnostics.py`, selected wave simulation API
  regressions, and this ledger.
- Finding: `wave_service.py` still parsed proposed changes from construction alternative diagnostics
  directly, keeping pure construction-diagnostic normalization inside the wave orchestration module.
- Action: extracted proposed-change normalization into a focused helper module and added direct tests
  for first-populated alternative selection, non-dict filtering, missing/non-list diagnostics, and
  the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_construction_diagnostics.py`; full direct construction
  diagnostics tests passed with 3 tests; selected wave simulation regressions passed with 8 tests;
  OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue extracting source-readiness lookup and selection/proof-pack item update
  helpers where dependency boundaries remain clean.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-350: Wave source-readiness lookup extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_source_readiness.py`,
  `tests/unit/dpm/waves/test_wave_source_readiness.py`, selected wave source-check/source-readiness
  API regressions, and this ledger.
- Finding: `wave_service.py` still owned mandate twin resolution and mandate health lookup before
  invoking the core source-readiness classifier, mixing repository lookup details into the wave
  orchestration module.
- Action: extracted source-readiness lookup into a focused helper module that resolves mandate twins,
  loads mandate health, and delegates classification to the core wave source-readiness policy; added
  direct tests for mandate-id lookup, portfolio fallback, ready classification, missing-twin blocking,
  and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_source_readiness.py`; full direct source-readiness helper
  tests passed with 5 tests; selected source-check/source-readiness API regressions passed with 43
  tests; OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue evaluating the remaining construction/proof-pack item update path, but keep
  external service calls in `wave_service.py` unless a clean dependency boundary emerges.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-351: Wave supportability payload extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_supportability_payload.py`,
  `tests/unit/dpm/waves/test_wave_supportability_payload.py`, selected wave supportability API
  regressions, and this ledger.
- Finding: after extracting supportability diagnostics, `wave_service.py` still assembled the
  aggregate supportability payload, issue counts, state reason, and operator actions directly.
- Action: extracted supportability payload assembly into a focused helper module backed by the
  supportability diagnostics helper, preserved the existing service-private `_supportability_issue`
  alias for compatibility tests, and added direct tests for ready, blocked, degraded, issue-count,
  operator-action, and export-surface behavior.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_supportability_payload.py`; direct supportability payload
  tests and selected supportability API regressions passed with 8 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by isolating selection/proof-pack update branches
  only where dependency flow remains explicit and testable.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-352: Wave simulation item extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_simulation_item.py`,
  `tests/unit/dpm/waves/test_wave_simulation_item.py`, selected wave simulation API regressions, and
  this ledger.
- Finding: `wave_service.py` still owned per-item simulation execution, construction alternative-set
  generation calls, missing-input diagnostics, generation-failure diagnostics, and the simulation
  input dataclass.
- Action: extracted per-item simulation execution and `DpmWaveSimulationInput` into a focused helper
  module, preserved `wave_service.DpmWaveSimulationInput` as an imported compatibility surface for
  routers, and added direct tests for non-source-ready no-op behavior, missing input blocking,
  successful construction alternative linkage, generation failure handling, and the module export
  surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_simulation_item.py`; full direct simulation item tests
  passed with 5 tests; selected wave simulation API regressions passed with 11 tests; OpenAPI quality
  gate passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: evaluate whether selection/proof-pack item update can be split into a similarly focused
  helper without hiding external proof-pack service dependency flow.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-353: Wave selection item extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_selection_item.py`,
  `tests/unit/dpm/waves/test_wave_selection_item.py`, selected wave selection/proof-pack API
  regressions, and this ledger.
- Finding: `wave_service.py` still owned per-item selection and proof-pack linkage, including
  selection diagnostics, no-proof-pack degraded posture, proof-pack generation calls, and failure
  diagnostics.
- Action: extracted per-item selection/proof-pack update logic into a focused helper module while
  keeping the wave-level selection orchestration and construction alternative selection call in
  `wave_service.py`; added direct tests for no-proof-pack degraded state, successful proof-pack
  linkage, proof-pack generation failure, and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_selection_item.py`; full direct selection item tests passed
  with 4 tests; selected wave selection/proof-pack API regressions passed with 23 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing the remaining wave orchestration surface for validation/error
  helper extraction, but keep durable repository writes and state-machine transitions central.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-354: Wave service private helper alias cleanup

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `tests/unit/dpm/api/test_waves_api.py`,
  `tests/unit/dpm/waves/test_wave_portfolio_sources.py`,
  `tests/unit/dpm/waves/test_wave_supportability_diagnostics.py`, and this ledger.
- Finding: after extracting portfolio source helpers and supportability diagnostics, `wave_service.py`
  still exposed private compatibility aliases that were used only by legacy API tests, widening the
  service module surface without serving route-facing orchestration.
- Action: removed stale private helper aliases from `wave_service.py`, narrowed the API supportability
  regression to public service behavior, and relied on direct helper tests for source-ref,
  optional-string, excluded-item, and operator-action coverage.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py`; selected public supportability API regressions plus direct portfolio
  source and supportability diagnostics tests passed with 7 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue trimming compatibility surfaces as helper modules gain direct tests.
- Wiki decision: no wiki source change required; this is internal service module-surface cleanup with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-355: Wave search projection extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_search.py`,
  `tests/unit/dpm/waves/test_wave_search.py`, selected wave search API regressions, and this ledger.
- Finding: `wave_service.py` still owned read-only wave search summary projection and supportability
  filtering, even though it is presentation assembly rather than workflow orchestration.
- Action: extracted wave search summary projection into a focused helper module and made
  `wave_service.search_waves` delegate to it; added direct tests for repository filter forwarding,
  summary field projection, supportability-state filtering, and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_search.py`; direct wave search tests and selected search API
  regressions passed with 4 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue moving read-only response projection helpers out of `wave_service.py` while
  keeping lookup errors and repository mutation workflows centralized.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-356: Wave detail projection extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_detail_projection.py`,
  `tests/unit/dpm/waves/test_wave_detail_projection.py`, selected wave detail/items/proof-pack API
  regressions, and this ledger.
- Finding: `wave_service.py` still assembled read-only detail and item-list payloads directly,
  including supportability and proof-pack posture projections.
- Action: extracted wave detail and item-list payload builders into a focused helper module and made
  `retrieve_wave_detail` and `list_wave_items` delegate to it; added direct tests for supportability,
  proof-pack posture, item payload projection, and the module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_detail_projection.py`; direct detail projection tests and
  selected detail/items/proof-pack API regressions passed with 7 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: continue isolating read-only report-input and portfolio-memory context projection where
  doing so does not obscure boundary-error translation.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-357: Wave report context extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_report_context.py`,
  `tests/unit/dpm/waves/test_wave_report_context.py`, selected wave report-input API regressions,
  and this ledger.
- Finding: `wave_service.py` still resolved bounded portfolio-memory context for report input
  directly, even though the logic is a read-only supportability projection around repository
  availability and first-item portfolio identity.
- Action: extracted portfolio-memory report-context resolution into a focused helper module and made
  report-input assembly delegate to it while preserving service-local boundary-error translation;
  added direct tests for no-context cases, first-item portfolio routing, and the module export
  surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_report_context.py`; direct report-context tests and selected
  report-input API regressions passed with 14 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: keep report-input boundary exception translation in `wave_service.py`; continue
  reviewing remaining lookup and event-append helpers for clean extraction opportunities.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-358: Wave service error extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_errors.py`,
  `tests/unit/dpm/waves/test_wave_errors.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` still defined reusable wave service exception carrier classes directly,
  keeping shared error vocabulary embedded in the orchestration module.
- Action: extracted wave validation and lookup error classes into a focused service error module,
  preserved the existing `wave_service` import surface for routers and tests, and added direct tests
  for code/message preservation, string representation, export surface, and compatibility aliases.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_errors.py`; direct wave error tests and selected wave API
  regressions passed with 136 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue reviewing remaining wave lookup and event-append helpers for clean extraction
  opportunities now that shared wave service error types are independently owned.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-359: Wave lookup helper extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_lookup.py`,
  `tests/unit/dpm/waves/test_wave_lookup.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` still owned the repeated repository lookup plus governed
  not-found-error boundary used by both read and workflow commands.
- Action: extracted wave lookup-to-governed-error translation into a focused helper module,
  preserved the existing private service alias for compatibility inside orchestration code, and
  added direct tests for loaded-wave return, missing-wave error details, alias preservation, and the
  module export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_lookup.py`; direct wave lookup tests and selected wave API
  regressions passed with 136 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue reviewing non-transition helper boundaries, especially same-state event
  append validation, for extraction without weakening orchestration clarity.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-360: Wave event append helper extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_event_append.py`,
  `tests/unit/dpm/waves/test_wave_event_append.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` still owned same-state event append validation and version increment
  logic used by item-level workflow evidence, even though it is a reusable service-support helper.
- Action: extracted same-state event append validation into a focused helper module, preserved the
  existing private service alias for orchestration compatibility, removed the now-unused event model
  import from `wave_service.py`, and added direct tests for success, identity mismatch, state
  mismatch, alias preservation, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_event_append.py`; direct wave event append tests and
  selected wave API regressions passed with 137 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by moving pure validation/supportability helpers
  while keeping state-transition orchestration readable and centralized.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-361: Wave trigger validation wrapper extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_trigger_validation.py`,
  `tests/unit/dpm/waves/test_wave_trigger_validation.py`, selected wave API regressions, and this
  ledger.
- Finding: `wave_service.py` still owned the thin trigger validation raise wrapper even though the
  underlying trigger support matrix and failure classification already lived in the trigger
  validation helper module.
- Action: moved governed trigger validation error raising into `wave_trigger_validation.py`,
  preserved the existing private service alias for preview/create orchestration compatibility, and
  added direct tests for success, governed error details, alias preservation, and the expanded module
  export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_trigger_validation.py`; direct trigger validation tests and
  selected wave API regressions passed with 140 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: keep state-changing wave orchestration in `wave_service.py`; continue extracting pure
  support helpers only when direct tests can pin the service contract.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-362: Wave update persistence conflict extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_persistence.py`,
  `tests/unit/dpm/waves/test_wave_persistence.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` repeated the same optimistic-concurrency update call and
  `DPM_WAVE_VERSION_CONFLICT` translation across source-check, simulation, selection, approval,
  stage, handoff, and cancellation commands.
- Action: extracted update persistence and version-conflict translation into a focused service
  helper, replaced repeated try/except blocks in wave orchestration with the shared helper, removed
  the now-unused conflict import from `wave_service.py`, and added direct tests for successful
  update forwarding, governed conflict translation, service alias use, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_persistence.py`; direct wave persistence tests and selected
  wave API regressions passed with 136 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: review create-wave save/idempotency conflict translation separately so the create path
  remains explicit and idempotency behavior stays directly tested.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-363: Wave create persistence conflict extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_persistence.py`,
  `tests/unit/dpm/waves/test_wave_persistence.py`, selected wave API regressions, and this ledger.
- Finding: after update conflict extraction, the create-wave path still translated repository
  save/idempotency conflicts directly in `wave_service.py`, leaving write-boundary error mapping
  split across orchestration and persistence helper code.
- Action: extended the wave persistence helper with create/save conflict translation, replaced the
  create path try/except with the shared helper while keeping idempotency replay orchestration in
  `wave_service.py`, removed now-unused create-conflict imports from the service, and expanded
  direct persistence tests for save forwarding, duplicate-wave and idempotency conflict translation,
  helper aliases, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_persistence.py`; direct wave persistence tests and selected
  wave API regressions passed with 139 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue reviewing wave creation assembly separately; persistence translation is now
  centralized, but request hashing and preview-to-create promotion remain orchestration concerns.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-364: Wave creation assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_creation.py`,
  `tests/unit/dpm/waves/test_wave_creation.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` still mixed create-request hash assembly and preview-to-created wave
  promotion into the create orchestration path, making idempotency evidence and event re-keying
  harder to test directly.
- Action: extracted canonical create request hashing and preview-to-created promotion into a focused
  creation helper, kept idempotency replay and persistence orchestration in `wave_service.py`, and
  added direct tests for hash field coverage, preview event re-keying, created transition evidence,
  idempotency hash metadata, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_creation.py`; direct wave creation tests and selected wave
  API regressions passed with 135 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue keeping workflow orchestration explicit while moving deterministic assembly
  helpers into directly tested modules.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-365: Wave preview assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_preview.py`,
  `tests/unit/dpm/waves/test_wave_preview.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` still assembled preview waves directly, including trigger validation,
  item construction, trigger source lineage, aggregate metrics, and preview transition evidence.
- Action: extracted preview wave assembly into a focused helper module, made
  `wave_service.preview_wave` delegate to it, removed now-unused service imports, and added direct
  tests for source-backed preview construction, governed empty-set validation, transition evidence,
  trigger lineage, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_preview.py`; direct wave preview tests and selected wave
  API regressions passed with 135 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue shrinking wave command functions only where helper extraction keeps workflow
  state transitions and repository interactions readable.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-366: Wave source-check assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_source_check.py`,
  `tests/unit/dpm/waves/test_wave_source_check.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` still assembled source-check item classification, aggregate metrics,
  and transition evidence directly inside the command function, even though the repository/state
  guard and persistence update are the orchestration concerns.
- Action: extracted source-check transition assembly into a focused helper, kept idempotent state
  guard and repository update in `wave_service.py`, removed the now-unused source-readiness import
  from the service, and added direct tests for item classification, aggregate rollup evidence,
  transition metadata, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_source_check.py`; direct wave source-check tests and
  selected wave API regressions passed with 134 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue extracting deterministic transition assembly from simulation or later workflow
  commands only when it reduces duplication without hiding command-state policy.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-367: Wave simulation assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_simulation.py`,
  `tests/unit/dpm/waves/test_wave_simulation.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` still assembled simulation-start transition evidence, per-item
  simulation results, aggregate rollup, and completion transition evidence directly inside the
  command function, blending deterministic assembly with state-policy and persistence orchestration.
- Action: extracted simulation transition assembly into a focused helper, kept idempotent state guard
  and repository update in `wave_service.py`, removed the now-unused simulation result import from
  the service, and added direct tests for missing-input degradation, simulation event sequence,
  aggregate rollup metadata, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_simulation.py`; direct wave simulation tests and selected
  wave API regressions passed with 134 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: pause additional feature-branch growth at the 50-commit checkpoint and run the full
  PR pre-merge gate before opening the PR.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-368: Wave service compatibility re-export fix

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, selected wave router mypy checks, and this ledger.
- Finding: after extracting wave error and simulation input helpers, runtime compatibility remained
  intact but full-repo mypy required `wave_service` compatibility imports to be explicit re-exports
  for routers that still type-check against the existing service surface.
- Action: marked `DpmWaveValidationError`, `DpmWaveLookupError`, and `DpmWaveSimulationInput` as
  explicit same-name imports in `wave_service.py` so existing router references remain both runtime
  and type-check compatible while helper modules own the implementations.
- Status: hardened
- Evidence: focused Ruff and format checks passed for `wave_service.py`; targeted mypy passed for
  `wave_service.py`, `wave_simulation_http.py`, and `wave_http_errors.py`.
- Follow-up: rerun full `make check` before PR creation to verify the full router surface.
- Wiki decision: no wiki source change required; this is an internal typing compatibility fix with
  no route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-369: Extracted helper compatibility alias fix-forward

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/construction_service.py`, `src/api/services/construction_alternative_builder.py`,
  focused construction and wave regression tests, and this ledger.
- Finding: full `make check` surfaced compatibility gaps from helper extraction: existing tests
  still patch `construction_service.has_solver_dependencies`, and existing wave tests still assert
  private compatibility aliases for trigger validation and simulation-result classification.
- Action: restored the construction solver capability hook through `construction_service.py` and
  passed the resolved value into the extracted alternative builder; restored wave private aliases as
  explicit assignments while keeping the helper modules as the implementation owners.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source files; focused mypy passed
  for the touched source files; the five previously failing focused construction/wave tests passed;
  `git diff --check` passed.
- Follow-up: rerun full `make check` before PR creation to prove there are no additional
  compatibility gaps.
- Wiki decision: no wiki source change required; this is an internal compatibility fix with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-370: Mandate service error extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_errors.py`,
  `tests/unit/dpm/mandates/test_mandate_errors.py`, selected mandate API regressions, and this
  ledger.
- Finding: `mandate_service.py` still defined reusable mandate service exception carrier classes
  directly, keeping shared service error vocabulary embedded in a large orchestration module.
- Action: extracted mandate lookup, diff, source-availability, health, and monitoring-run error
  types into a focused service error module, preserved the existing `mandate_service` import surface
  for routers and tests, and added direct tests for compatibility aliases, exception families, and
  export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_errors.py`; direct mandate error tests and selected
  mandate API regressions passed with 26 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue shrinking `mandate_service.py` by moving pure diff, command-center, and
  source-resolution support helpers into directly tested modules while preserving route-facing
  service compatibility.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-371: Mandate command-center projection extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_command_center.py`,
  `tests/unit/dpm/mandates/test_mandate_command_center.py`, selected mandate API regressions, and
  this ledger.
- Finding: `mandate_service.py` still owned pure command-center projection helpers for
  supportability-state classification, monitoring-run filter matching, attention-bucket rollups,
  recommended-action rollups, and severity ordering.
- Action: extracted the command-center helper cluster into a focused module, preserved existing
  private service aliases for compatibility, removed now-unused enum imports from the service, and
  added direct tests for source-readiness supportability mapping, bounded filter matching, bucket
  sorting and reason ranking, recommended-action ordering, alias preservation, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_command_center.py`; direct command-center helper
  tests and selected mandate API regressions passed with 29 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue extracting pure mandate diff and source-resolution helpers while keeping
  repository orchestration in `mandate_service.py`.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-372: Mandate diff projection extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_diff.py`,
  `tests/unit/dpm/mandates/test_mandate_diff.py`, selected mandate API regressions, and this
  ledger.
- Finding: `mandate_service.py` still owned mandate diff DTOs, recursive payload comparison, and
  materiality classification even though the service method only needs to orchestrate repository
  version selection.
- Action: extracted the mandate diff DTO and pure diff projection helpers into a focused module,
  kept repository version selection in `mandate_service.py`, preserved the existing service import
  and private-helper compatibility surface, and added direct helper tests for recursive comparison,
  lineage-ignore behavior, deterministic sorting, materiality classification, diff projection, and
  export aliases.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_diff.py`; direct mandate diff helper tests and
  selected mandate API regressions passed with 29 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue extracting optional mandate source-resolution helpers while keeping
  core-resolver orchestration in `mandate_service.py`.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-373: Mandate optional-source readiness extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_optional_sources.py`,
  `tests/unit/dpm/mandates/test_mandate_optional_sources.py`, selected mandate API regressions, and
  this ledger.
- Finding: `mandate_service.py` still owned reusable optional core-source resolver and readiness
  screening logic for missing resolver methods, resolver errors, supportability states, data-quality
  statuses, and benchmark-assignment lifecycle status.
- Action: extracted optional source resolution and readiness helpers into a focused service helper
  module, kept refresh orchestration and hard failure handling in `mandate_service.py`, preserved
  existing private service helper aliases for compatibility, and added direct tests for resolver
  dispatch, absent optional methods, resolver error family mapping, ready/degraded/stale source
  screening, benchmark assignment status screening, alias preservation, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_optional_sources.py`; direct optional-source helper
  tests and selected mandate API regressions passed with 33 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue shrinking mandate refresh orchestration by grouping source-family resolution
  calls without moving router or HTTP concerns into services.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-374: Mandate optional-source bundle extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_optional_sources.py`,
  `tests/unit/dpm/mandates/test_mandate_optional_sources.py`, selected mandate API regressions, and
  this ledger.
- Finding: even after the readiness helpers were extracted, `refresh_mandate_from_core` still
  contained a long repeated sequence for resolving each optional source family and assembling the
  unavailable-source list, making the service harder to scan as orchestration.
- Action: added a typed `DpmMandateOptionalSources` bundle and moved source-family resolution
  assembly into `resolve_mandate_optional_sources`; the service now obtains the bundle and passes it
  into mandate twin and health-input builders while preserving private helper compatibility aliases.
  Direct tests now verify bundle typing, source-family request parameters, degraded-family
  filtering, and alias/export surfaces.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_optional_sources.py`; direct optional-source helper
  tests and selected mandate API regressions passed with 34 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing `mandate_service.py` by extracting monitoring-run assembly and
  portfolio-manager book membership helpers where they remain pure service support logic.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-375: Mandate monitoring-run support extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_monitoring_run.py`,
  `tests/unit/dpm/mandates/test_mandate_monitoring_run.py`, selected monitoring API regressions,
  and this ledger.
- Finding: `run_mandate_monitoring_once` still mixed repository orchestration with reusable
  monitoring-run support logic for run-id generation, distribution counting, exception run-id
  attachment, and terminal run projection.
- Action: extracted the pure monitoring-run support functions into a focused service helper module,
  kept mandate lookup, health recalculation, persistence, and error propagation in
  `mandate_service.py`, preserved private service helper aliases for compatibility, and added
  direct tests for deterministic run ids, distribution counts, immutable exception run-id
  attachment, terminal run projection, aliases, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_monitoring_run.py`; direct monitoring-run helper
  tests and selected monitoring API regressions passed with 16 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: continue shrinking `mandate_service.py` by extracting portfolio-manager book
  membership mandate-id resolution and monitoring command-center assembly where they remain pure
  support logic.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-376: Mandate PM-book membership helper extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_pm_book.py`,
  `tests/unit/dpm/mandates/test_mandate_pm_book.py`, selected monitoring API regressions, and this
  ledger.
- Finding: `mandate_service.py` still owned portfolio-manager book membership mandate-id resolution
  even though the logic is reusable support code for resolving source-owned PM book membership
  products into locally persisted mandate snapshots.
- Action: extracted PM-book membership mandate-id resolution into a focused service helper module,
  preserved the existing `mandate_service.mandate_ids_from_pm_book_membership` router import
  surface, and added direct tests for successful member resolution, missing mandate snapshots,
  empty membership payloads, service import compatibility, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_pm_book.py`; direct PM-book helper tests and selected
  monitoring API regressions passed with 15 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue extracting command-center summary assembly and health recalculation support
  where repository orchestration can remain in `mandate_service.py`.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-377: Mandate command-center summary extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_command_center.py`,
  `tests/unit/dpm/mandates/test_mandate_command_center.py`, selected monitoring API regressions,
  and this ledger.
- Finding: `get_command_center_summary` still mixed repository reads with DTO projection,
  health-state filtering, partial-readiness reason assembly, supportability classification, and
  attention/recommended-action aggregation.
- Action: moved command-center summary projection into `build_command_center_summary` in the
  existing command-center helper module, kept repository reads and monitoring-run selection in
  `mandate_service.py`, preserved private compatibility aliases, and added direct tests for
  populated and empty summary projection, selected health-state filtering, source-run provenance,
  partial reasons, limit handling, supportability, aliases, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_command_center.py`; direct command-center helper
  tests and selected monitoring API regressions passed with 18 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: continue extracting health recalculation support and repository lookup wrappers where
  they can be made directly testable without hiding orchestration.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-378: Mandate health-result helper extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_health_result.py`,
  `tests/unit/dpm/mandates/test_mandate_health_result.py`, selected mandate API regressions, and
  this ledger.
- Finding: mandate refresh and recalculation paths both performed the same health snapshot
  calculation followed by monitoring-exception derivation from the mandate twin source lineage.
- Action: extracted the repeated health-calculation result assembly into a focused helper returning
  a typed `DpmMandateHealthCalculationResult`, kept persistence and mismatch validation in
  `mandate_service.py`, preserved the service compatibility alias, and added direct tests for
  snapshot/exception projection, service import compatibility, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_health_result.py`; direct health-result helper tests
  and selected mandate API regressions passed with 26 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue extracting small repository lookup wrappers or move to another service hotspot
  once the remaining `mandate_service.py` orchestration is sufficiently lean.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-379: Wave item collection update extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_item_collection.py`,
  `tests/unit/dpm/waves/test_wave_item_collection.py`, selected wave API regressions, and this
  ledger.
- Finding: `wave_service.py` repeated the same item-list replacement plus aggregate-metric
  recalculation block across selection, approval, staging, handoff, and cancellation workflows.
- Action: extracted `wave_with_items_and_aggregate` into a focused wave helper module, replaced the
  repeated model-copy blocks in `wave_service.py`, preserved a private service alias for
  compatibility, and added direct tests for metric recomputation, handoff-ref extra updates, alias
  preservation, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_item_collection.py`; direct wave item collection tests and
  selected wave API regressions passed with 136 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting wave state guard/idempotent replay
  checks or workflow persistence patterns where behavior can be directly tested.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-380: Wave state guard extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_state_guard.py`,
  `tests/unit/dpm/waves/test_wave_state_guard.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` repeated idempotent replay checks and invalid-state validation error
  construction across source-check, simulation, selection, approval, staging, handoff, and
  cancellation workflows.
- Action: extracted wave state replay and allowed-state guard helpers into a focused module,
  replaced inline workflow guard checks in `wave_service.py`, preserved private service aliases, and
  added direct tests for replay-state matching, allowed-state acceptance, governed error code/message
  construction, alias preservation, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_state_guard.py`; direct wave state guard tests and selected
  wave API regressions passed with 137 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting persisted transition update helpers
  or selection workflow support where behavior can be directly covered.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-381: Wave selection guard extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_selection_guard.py`,
  `tests/unit/dpm/waves/test_wave_selection_guard.py`, selected wave API regressions, and this
  ledger.
- Finding: `select_wave_item_alternative` still embedded wave-item lookup and alternative-set
  availability validation inside the larger selection orchestration flow.
- Action: extracted selectable wave-item validation into a focused helper that returns the governed
  wave item or raises the existing bounded lookup/validation errors, kept construction selection and
  proof-pack orchestration in `wave_service.py`, preserved a private service alias, and added direct
  tests for successful lookup, missing items, missing alternatives, alias preservation, and export
  surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_selection_guard.py`; direct wave selection guard tests and
  selected wave API regressions passed with 137 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting workflow event metadata builders or
  persisted transition update support where it improves readability without hiding domain behavior.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-382: Wave workflow metadata extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_workflow_metadata.py`,
  `tests/unit/dpm/waves/test_wave_workflow_metadata.py`, selected wave API regressions, and this
  ledger.
- Finding: approval, staging, handoff, and cancellation workflows still built audit/event metadata
  inline, duplicating optional-comment handling and no-external-execution boundary fields.
- Action: extracted workflow event metadata builders into a focused helper module, replaced inline
  metadata dictionaries in `wave_service.py`, preserved private service aliases, and added direct
  tests for approval exception counts, stage comments, handoff no-external-execution evidence,
  cancellation no-external-execution evidence, alias preservation, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_workflow_metadata.py`; direct workflow metadata tests and
  selected wave API regressions passed with 138 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting persisted transition update support
  or construction-selection orchestration helpers where they stay domain-specific and testable.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-383: Wave selection metadata extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_workflow_metadata.py`,
  `tests/unit/dpm/waves/test_wave_workflow_metadata.py`, selected wave API regressions, and this
  ledger.
- Finding: item-selection still built its audit event metadata inline while other wave workflow
  event metadata had already moved into a directly tested helper module.
- Action: added `selection_event_metadata` to the wave workflow metadata helper, replaced the inline
  selection metadata dictionary in `wave_service.py`, preserved the private service alias, and
  expanded direct metadata tests to cover selected alternative, alternative set, proof-pack id, and
  proof-pack state evidence.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_workflow_metadata.py`; direct workflow metadata tests and
  selected wave API regressions passed with 139 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting persisted transition update support
  or construction-selection orchestration helpers where the service can remain workflow-oriented.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-384: Wave construction-selection adapter extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_construction_selection.py`,
  `tests/unit/dpm/waves/test_wave_construction_selection.py`, selected wave API regressions, and
  this ledger.
- Finding: `wave_service.py` still imported `construction_service` directly to select a construction
  alternative and translate construction lookup failures into bounded wave errors.
- Action: extracted the construction selection call and wave-specific error mapping into a focused
  adapter module, removed the direct construction-service import from `wave_service.py`, preserved a
  private service alias for compatibility, and added direct tests for delegation arguments, bounded
  lookup-error mapping, alias preservation, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_construction_selection.py`; direct wave construction
  selection tests and selected wave API regressions passed with 136 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting persisted transition update support
  or moving to the next largest service hotspot once wave orchestration is sufficiently lean.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-385: Wave created-id helper extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_creation.py`,
  `tests/unit/dpm/waves/test_wave_creation.py`, selected wave API regressions, and this ledger.
- Finding: `wave_service.py` still generated durable wave identifiers directly with `uuid`, while
  the rest of the create-wave request hashing and preview-promotion mechanics already lived in
  `wave_creation.py`.
- Action: moved created-wave id generation into `create_created_wave_id`, removed the direct `uuid`
  dependency from `wave_service.py`, and added a deterministic direct test for the governed
  `dwv_` identifier prefix and 12-character entropy slice.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_creation.py`; direct wave creation tests and selected wave
  API regressions passed with 136 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting persisted transition update support
  or move to the next largest service hotspot once wave orchestration is sufficiently lean.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-386: Proof pack handoff-ref helper extraction

- Date: 2026-06-01
- Scope: `src/api/services/proof_pack_service.py`,
  `src/api/services/proof_pack_handoff_refs.py`,
  `tests/unit/dpm/proof_packs/test_proof_pack_handoff_refs.py`, selected proof-pack service
  regressions, and this ledger.
- Finding: `proof_pack_service.py` still embedded append-only handoff reference lookup, hydration,
  and idempotent append mechanics inside the public proof-pack orchestration service.
- Action: extracted handoff reference support into a focused helper module, kept public proof-pack
  not-generated error translation in `proof_pack_service.py`, and added direct tests for latest
  append-only reference selection, immutable hydration overlay, idempotent handoff reference
  generation, and stored-ref to evidence-ref identity preservation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `proof_pack_service.py` and `proof_pack_handoff_refs.py`; direct handoff-ref tests and
  selected proof-pack service regressions passed with 16 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing `proof_pack_service.py` by extracting selected-alternative source
  resolution or mandate-evidence resolution where the service can remain orchestration-focused.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-387: Proof pack selected-source extraction

- Date: 2026-06-01
- Scope: `src/api/services/proof_pack_service.py`,
  `src/api/services/proof_pack_selected_source.py`,
  `tests/unit/dpm/proof_packs/test_proof_pack_selected_source.py`, selected proof-pack service
  regressions, and this ledger.
- Finding: selected-alternative proof-pack generation still performed source lookup, selected
  alternative validation, optional selection lookup, and linked-run degradation inline in the public
  service function.
- Action: extracted selected-alternative source resolution into a focused helper that returns the
  alternative set, persisted selection, optional linked run, and workflow decisions while preserving
  existing missing-source validation and missing-run degradation behavior; updated service
  regressions to import the source validation error from the core proof-pack owner.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `proof_pack_service.py` and `proof_pack_selected_source.py`; direct selected-source
  tests and selected proof-pack service regressions passed with 16 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reducing `proof_pack_service.py` by extracting mandate evidence resolution or
  proof-pack persistence/idempotency replay support where direct coverage remains clear.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-388: Proof pack mandate-evidence extraction

- Date: 2026-06-01
- Scope: `src/api/services/proof_pack_service.py`,
  `src/api/services/proof_pack_mandate_evidence.py`,
  `tests/unit/dpm/proof_packs/test_proof_pack_mandate_evidence.py`, selected proof-pack service
  regressions, and this ledger.
- Finding: proof-pack generation still resolved mandate twin and health evidence inline, mixing
  portfolio-ownership validation and evidence-gap construction into the orchestration service.
- Action: extracted mandate evidence resolution into a focused helper that returns the optional
  twin, optional health snapshot, and bounded evidence gap codes; updated run-based and
  selected-alternative proof-pack paths to consume the helper result directly.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `proof_pack_service.py` and `proof_pack_mandate_evidence.py`; direct mandate-evidence
  tests and selected proof-pack service regressions passed with 16 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reducing `proof_pack_service.py` by extracting proof-pack idempotency replay
  or portfolio-memory handoff context support where behavior remains directly testable.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-389: Proof pack replay lookup extraction

- Date: 2026-06-01
- Scope: `src/api/services/proof_pack_service.py`, `src/api/services/proof_pack_replay.py`,
  `tests/unit/dpm/proof_packs/test_proof_pack_replay.py`, selected proof-pack service regressions,
  and this ledger.
- Finding: run-based and selected-alternative proof-pack generation duplicated replay lookup logic
  for idempotency-key matches and immutable source-identity matches.
- Action: extracted replay lookup into a focused helper that preserves idempotency precedence before
  falling back to proof-pack source identity; updated both generation paths to use the helper and
  added direct tests for idempotency replay, source-identity fallback, and no-match behavior.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `proof_pack_service.py` and `proof_pack_replay.py`; direct replay tests and selected
  proof-pack service regressions passed with 15 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue reducing proof-pack and other service hotspots by extracting only reusable
  support logic with direct tests; keep proof-pack generation orchestration in the service.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-390: Outcome review source-search extraction

- Date: 2026-06-01
- Scope: `src/api/services/outcome_review_service.py`,
  `src/api/services/outcome_review_search.py`,
  `tests/unit/dpm/outcomes/test_outcome_review_search.py`, selected outcome-review API
  regressions, and this ledger.
- Finding: outcome-review source-lineage search normalization, filtering, facet counting, bounded
  scan behavior, and pagination were embedded in `outcome_review_service.py`, making source-boundary
  search behavior harder to test directly.
- Action: extracted source-lineage search into a focused helper returning a typed search page,
  preserved the public service tuple contract for existing routers, and added direct tests for
  blank-filter normalization, conjunctive source-owner/source-type matching, sorted facet counts,
  pagination, bounded source-scan behavior, and current latest-first repository ordering.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `outcome_review_service.py` and `outcome_review_search.py`; direct outcome-review
  search tests and selected API regressions passed with 9 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing outcome-review or wave service hotspots by extracting creation event
  assembly, content-hash support, or transition support only where direct tests can pin behavior.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-391: Outcome review creation-support extraction

- Date: 2026-06-01
- Scope: `src/api/services/outcome_review_service.py`,
  `src/api/services/outcome_review_creation.py`,
  `tests/unit/dpm/outcomes/test_outcome_review_creation.py`, selected outcome-review API
  regressions, and this ledger.
- Finding: outcome-review creation still embedded canonical content hashing and created-event
  type/source-lineage assembly inside the orchestration service.
- Action: extracted review content-hash generation, bounded created-event type mapping, and created
  event assembly into a focused helper while keeping idempotency, review construction, and
  persistence in `outcome_review_service.py`; added direct tests for state-to-event mapping,
  expected/realized source-lineage projection, stable hashing, and hash drift when source evidence
  changes.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `outcome_review_service.py` and `outcome_review_creation.py`; direct creation-support
  tests and selected outcome-review API regressions passed with 8 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reducing service hotspots by extracting dimension-input validation or
  refresh-event support where tests can pin validation and event semantics directly.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-392: Outcome review refresh-event extraction

- Date: 2026-06-01
- Scope: `src/api/services/outcome_review_service.py`,
  `src/api/services/outcome_review_refresh.py`,
  `tests/unit/dpm/outcomes/test_outcome_review_refresh.py`, selected outcome-review API
  regressions, and this ledger.
- Finding: source-refresh event identity, bounded event type, state/reason projection, and
  expected-plus-realized source lineage assembly were embedded in the refresh orchestration path.
- Action: extracted source-refresh event assembly into a focused helper while preserving lookup,
  comparison, persistence append, and return orchestration in `outcome_review_service.py`; added a
  direct deterministic test for event identity, timestamp, actor, state, reason codes, and source
  lineage projection.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `outcome_review_service.py` and `outcome_review_refresh.py`; direct refresh-event tests
  and selected outcome-review API regressions passed with 6 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing service hotspots; evaluate whether dimension-input validation should
  move only after preserving router-owned validation-error imports cleanly.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-393: Rebalance operation identity extraction

- Date: 2026-06-01
- Scope: `src/api/services/rebalance_simulation_service.py`,
  `src/api/services/rebalance_operation_identity.py`,
  `tests/unit/api/test_rebalance_operation_identity.py`, selected runtime/service edge regressions,
  and this ledger.
- Finding: rebalance simulation orchestration directly formatted generated correlation ids and
  batch analysis ids with inline UUID slicing, leaving identifier conventions untested outside
  broad endpoint flows.
- Action: extracted generated operation identity helpers for rebalance correlation ids and batch
  analysis ids, preserved caller-supplied correlation ids, removed the direct UUID dependency from
  the orchestration service, and added direct deterministic tests for each identifier convention.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `rebalance_simulation_service.py` and `rebalance_operation_identity.py`; direct
  identity tests and selected runtime/service edge regressions passed with 33 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reducing rebalance or wave service hotspots where extraction removes
  duplicated orchestration support or directly testable boundary behavior.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-394: Wave approval-transition extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_approval_transition.py`,
  `tests/unit/dpm/waves/test_wave_approval_transition.py`, selected wave workflow/API
  regressions, and this ledger.
- Finding: `approve_wave` still embedded item approval mapping, eligible-item validation,
  aggregate refresh, target-state selection, and approval event assembly inside the public workflow
  orchestration function.
- Action: extracted approval transition assembly into a focused helper that returns the approved
  wave or raises the existing bounded validation error, preserved the private workflow metadata
  alias expected by existing tests, and added direct tests for full approval, approval with
  exceptions, no eligible items, approval metadata, aggregate refresh, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_approval_transition.py`; direct approval-transition tests
  and selected wave workflow/API regressions passed with 122 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting stage, handoff, or cancel transition
  assembly using the same directly tested pattern.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-395: Wave stage-transition extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_stage_transition.py`,
  `tests/unit/dpm/waves/test_wave_stage_transition.py`, selected wave workflow/API regressions, and
  this ledger.
- Finding: `stage_wave` still embedded item staging, no-external-execution diagnostics, eligible
  item validation, aggregate refresh, and stage event assembly inside the public workflow
  orchestration function.
- Action: extracted stage transition assembly into a focused helper that returns the staged wave or
  raises the existing bounded validation error, preserved the private workflow metadata alias
  expected by existing tests, and added direct tests for staging approved items, preserving
  unapproved exception items, no eligible items, stage metadata, aggregate refresh, and export
  surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_stage_transition.py`; direct stage-transition tests and
  selected wave workflow/API regressions passed with 122 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting handoff or cancel transition
  assembly using the same directly tested pattern.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-396: Wave handoff-transition extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_handoff_transition.py`,
  `tests/unit/dpm/waves/test_wave_handoff_transition.py`, selected wave workflow/API regressions,
  and this ledger.
- Finding: `handoff_wave` still embedded handoff item transition mapping, operations handoff-ref
  construction, no-external-execution boundary evidence, aggregate refresh, and handoff event
  assembly inside the public workflow orchestration function.
- Action: extracted handoff transition assembly into a focused helper that returns the
  handoff-ready wave or raises the existing bounded validation error, preserved the private
  workflow metadata alias expected by existing tests, and added direct tests for handoff ref
  creation, partial handoff, no eligible items, no external execution claim, handoff metadata,
  aggregate refresh, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_handoff_transition.py`; direct handoff-transition tests
  and selected wave workflow/API regressions passed with 122 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` by extracting cancel transition assembly or other
  remaining workflow support that can be directly tested.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-397: Wave cancel-transition extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_cancel_transition.py`,
  `tests/unit/dpm/waves/test_wave_cancel_transition.py`, selected wave workflow/API regressions, and
  this ledger.
- Finding: `cancel_wave` still embedded item cancellation, no-external-execution diagnostics,
  aggregate refresh, cancel event assembly, and invalid transition mapping inside the public
  workflow orchestration function.
- Action: extracted cancel transition assembly into a focused helper that returns the cancelled wave
  or maps invalid domain transitions to the existing bounded validation error, preserved the private
  workflow metadata alias expected by existing tests, and added direct tests for cancellation
  metadata, handoff-ready item preservation, invalid transition mapping, aggregate refresh, and
  export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_cancel_transition.py`; direct cancel-transition tests and
  selected wave workflow/API regressions passed with 122 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` around remaining orchestration support or move to
  the next service hotspot once workflow transition assembly is sufficiently lean.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-398: Wave item-selection transition extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_item_selection_transition.py`,
  `tests/unit/dpm/waves/test_wave_item_selection_transition.py`, selected wave workflow/API
  regressions, and this ledger.
- Finding: `select_wave_item_alternative` still embedded selected-item mutation, proof-pack state
  projection, aggregate refresh, and item-selection audit event assembly inside the public workflow
  orchestration function after performing lookup, state guarding, construction selection, and
  persistence.
- Action: extracted item-selection transition assembly into a focused helper while keeping lookup,
  state guards, construction repository selection, and persistence in the service; preserved the
  private workflow metadata alias expected by existing tests; and added direct tests for selected
  item replacement, retained-item preservation, aggregate refresh, degraded proof-pack metadata,
  generated proof-pack metadata, selection event evidence, and export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_item_selection_transition.py`; direct item-selection
  transition tests and selected wave workflow/API regressions passed with 147 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` only where remaining orchestration support has a
  directly testable boundary; otherwise move to the next service hotspot.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-399: Wave report-input assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `src/api/services/wave_report_input.py`,
  `tests/unit/dpm/waves/test_wave_report_input.py`, selected wave report/API regressions, and this
  ledger.
- Finding: `get_report_input` still assembled supportability, proof-pack posture, portfolio-memory
  context, and external-execution boundary error mapping inside the public service function instead
  of keeping the service focused on lookup and orchestration.
- Action: extracted report-input assembly into a focused helper that builds supportability and
  proof-pack posture, resolves optional portfolio-memory report context, maps core boundary
  failures to the existing bounded service error, and leaves `wave_service.py` responsible only for
  wave lookup and delegation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_report_input.py`; direct report-input tests and selected
  wave report/API regressions passed with 145 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue reducing `wave_service.py` only where remaining workflow functions still mix
  orchestration with directly testable domain assembly; otherwise shift to the next service hotspot.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-400: Mandate monitoring run item calculation extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`,
  `src/api/services/mandate_monitoring_run.py`,
  `tests/unit/dpm/mandates/test_mandate_monitoring_run.py`, selected mandate monitoring
  regressions, and this ledger.
- Finding: `run_mandate_monitoring_once` still mixed repository writes with per-mandate health
  recalculation, exception derivation, requested as-of-date projection, and monitoring-run id
  attachment inside the service loop.
- Action: extracted per-mandate monitoring calculation into a focused result helper that returns
  the health snapshot and run-scoped exceptions, preserving service ownership of repository reads,
  writes, run summary distribution, and monitoring-run persistence.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_monitoring_run.py`; direct monitoring-run helper
  tests and selected mandate API regressions passed with 33 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue shrinking `mandate_service.py` where source resolution, persistence, or
  command-center orchestration can be separated without hiding repository ownership.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-401: Mandate refresh assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_refresh.py`,
  `tests/unit/dpm/mandates/test_mandate_refresh.py`, selected mandate refresh/API regressions, and
  this ledger.
- Finding: `refresh_mandate_from_core` still mixed core source resolution, model-target fallback,
  optional source assembly, market-data coverage resolution, twin compilation, health input
  assembly, source error mapping, health calculation, and repository persistence in a single
  service function.
- Action: extracted source-backed refresh result assembly into a focused helper that resolves core
  inputs, maps core source errors to bounded mandate service errors, builds the digital twin and
  health result, and returns a refresh result for the service to persist.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_refresh.py`; direct mandate-refresh tests and
  selected mandate API regressions passed with 32 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing mandate service persistence/orchestration seams where helper
  extraction produces directly testable private-banking source-boundary behavior.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-402: Mandate diff version resolution extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`, `src/api/services/mandate_diff.py`,
  `tests/unit/dpm/mandates/test_mandate_diff.py`, selected mandate API regressions, and this
  ledger.
- Finding: `diff_mandate_versions` still embedded requested version-pair validation, latest-two
  fallback selection, unknown-version error mapping, and diff construction inside the service
  function even though this is mandate-diff domain behavior.
- Action: moved version resolution into `build_mandate_diff_for_versions`, preserving repository
  lookup and missing-mandate handling in the service while adding direct tests for explicit version
  pairs, default latest-two comparison, incomplete version pairs, unknown versions, helper export,
  and service alias compatibility.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_diff.py`; direct mandate-diff tests and selected
  mandate API regressions passed with 33 tests; OpenAPI quality gate passed; API vocabulary
  inventory validate-only gate passed; `git diff --check` passed; service leakage scan found no
  router/HTTP imports in service modules.
- Follow-up: continue moving domain-specific selection and validation rules out of
  `mandate_service.py` while keeping repository access and API-facing orchestration there.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-403: Rebalance simulation execution-context extraction

- Date: 2026-06-01
- Scope: `src/api/services/rebalance_simulation_service.py`,
  `src/api/services/rebalance_simulation_execution_context.py`,
  `tests/unit/api/test_rebalance_simulation_execution_context.py`, selected rebalance API/runtime
  regressions, and this ledger.
- Finding: `simulate_rebalance` still assembled request hash, resolved correlation id, policy-pack
  context, policy-pack replay flag, and policy-resolution observability fields inline before
  delegating to sync execution.
- Action: extracted simulation execution-context assembly into a focused helper that returns the
  request hash, resolved correlation id, selected policy definition, replay flag, and policy
  resolution metadata, keeping `simulate_rebalance` focused on logging and sync execution
  delegation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `rebalance_simulation_service.py` and
  `rebalance_simulation_execution_context.py`; direct execution-context tests and selected
  rebalance API/runtime regressions passed with 140 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reducing rebalance orchestration around async submission and batch execution
  where extracted helpers improve auditability without hiding runtime gates.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-404: Rebalance batch execution-context extraction

- Date: 2026-06-01
- Scope: `src/api/services/rebalance_simulation_service.py`,
  `src/api/services/rebalance_batch_execution_context.py`,
  `tests/unit/api/test_rebalance_batch_execution_context.py`, selected rebalance API/runtime
  regressions, and this ledger.
- Finding: `execute_batch_analysis` still assembled generated batch id, analyze policy-pack
  context, and policy-resolution observability fields inline before delegating to batch scenario
  execution.
- Action: extracted batch execution-context assembly into a focused helper that returns the batch
  id, selected policy definition, and policy resolution metadata, keeping batch analysis focused on
  logging and execution delegation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `rebalance_simulation_service.py` and `rebalance_batch_execution_context.py`; direct
  batch execution-context tests and selected rebalance API/runtime regressions passed with 140
  tests; OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing rebalance async submission and manual execution paths for
  similarly testable context assembly or supportability-boundary extraction.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-405: Rebalance async submission-context extraction

- Date: 2026-06-01
- Scope: `src/api/services/rebalance_simulation_service.py`,
  `src/api/services/rebalance_async_submission_context.py`,
  `tests/unit/api/test_rebalance_async_submission_context.py`, selected rebalance API/runtime
  regressions, and this ledger.
- Finding: `submit_and_optionally_execute_async_analysis` still mixed async support-service
  resolution, supportability-store unavailable mapping, analyze-async policy resolution,
  execution-mode resolution, and request-json assembly inside the public orchestration function.
- Action: extracted async submission-context assembly into a focused helper that returns the
  support service, persisted request payload, execution mode, and policy resolution metadata while
  preserving service-level support-service factory injection for test and runtime override
  compatibility.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `rebalance_simulation_service.py`,
  `rebalance_async_submission_context.py`, and the related rebalance execution-context helpers;
  direct async submission-context tests and selected rebalance API/runtime regressions passed with
  144 tests; OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git
  diff --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing rebalance manual execution and async runner seams for directly
  testable supportability and operation-lifecycle boundaries.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-406: Outcome review dimension-input extraction

- Date: 2026-06-01
- Scope: `src/api/services/outcome_review_service.py`,
  `src/api/services/outcome_review_dimensions.py`,
  `tests/unit/dpm/outcomes/test_outcome_review_dimensions.py`, selected outcome review/API
  regressions, and this ledger.
- Finding: outcome review preview and refresh flows still depended on a private service function
  for expected-versus-realized dimension input assembly and missing-evidence validation, leaving a
  domain validation boundary embedded inside orchestration.
- Action: extracted dimension configuration, validation error, and dimension input assembly into a
  focused helper module with direct tests for configured dimension projection, missing expected
  evidence, missing realized evidence, helper export surface, and service import compatibility.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `outcome_review_service.py` and `outcome_review_dimensions.py`; direct outcome
  dimension tests and selected outcome/proof-pack regressions passed with 107 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue extracting outcome review report/AI input context assembly or creation
  support where it produces directly testable source-boundary behavior.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-407: Outcome review report-input context extraction

- Date: 2026-06-01
- Scope: `src/api/services/outcome_review_service.py`,
  `src/api/services/outcome_review_report_inputs.py`,
  `tests/unit/dpm/outcomes/test_outcome_review_report_inputs.py`, selected outcome/proof-pack
  regressions, and this ledger.
- Finding: outcome review report-input and AI-evidence input accessors duplicated
  portfolio-memory context assembly inside the service, keeping downstream handoff context
  construction embedded in lookup orchestration.
- Action: extracted outcome report/AI evidence input builders and portfolio-memory context
  assembly into a focused helper module, preserving service ownership of review lookup while adding
  direct tests for missing repository gating, portfolio id propagation, report input context
  passing, AI evidence context passing, export surface, and service alias compatibility.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `outcome_review_service.py` and `outcome_review_report_inputs.py`; direct outcome
  report-input tests and selected outcome/proof-pack regressions passed with 113 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing proof-pack report/AI input helpers for the same handoff-context
  duplication pattern.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-408: Proof-pack report-input context extraction

- Date: 2026-06-01
- Scope: `src/api/services/proof_pack_service.py`,
  `src/api/services/proof_pack_report_inputs.py`,
  `tests/unit/dpm/proof_packs/test_proof_pack_report_inputs.py`, selected proof-pack/API
  regressions, and this ledger.
- Finding: proof-pack report-input and AI-evidence input accessors duplicated portfolio-memory
  context assembly inside the service, mirroring the outcome-review handoff-context duplication and
  leaving downstream handoff context construction embedded in lookup orchestration.
- Action: extracted proof-pack report/AI evidence input builders and portfolio-memory context
  assembly into a focused helper module, preserving service ownership of proof-pack lookup while
  adding direct tests for missing repository gating, portfolio id propagation, report input context
  passing, AI evidence context passing, export surface, and service alias compatibility.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `proof_pack_service.py` and `proof_pack_report_inputs.py`; direct proof-pack
  report-input tests and selected proof-pack/outcome regressions passed with 119 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing proof-pack generation flows for source/replay assembly that can be
  directly tested without hiding persistence ownership.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-409: Proof-pack persistence retention extraction

- Date: 2026-06-01
- Scope: `src/api/services/proof_pack_service.py`,
  `src/api/services/proof_pack_persistence.py`,
  `tests/unit/dpm/proof_packs/test_proof_pack_persistence.py`, selected proof-pack regressions,
  and this ledger.
- Finding: proof-pack generation orchestration still owned the append-only persistence retention
  calculation directly, leaving the seven-year evidence-retention policy hidden in the service
  rather than in a small supportability helper with direct tests.
- Action: extracted proof-pack persistence and retention-expiry calculation into a focused helper,
  kept proof-pack generation orchestration in the service, and added direct tests for deterministic
  seven-year retention expiry and the helper export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `proof_pack_service.py` and `proof_pack_persistence.py`; direct proof-pack
  persistence tests and selected proof-pack service/repository regressions passed with 19 tests;
  OpenAPI quality gate passed; API vocabulary inventory validate-only gate passed; `git diff
  --check` passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing proof-pack generation flow for source-resolution and builder-input
  assembly that can be separated without moving repository lookup ownership out of the service.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-410: Proof-pack handoff-ref lookup extraction

- Date: 2026-06-01
- Scope: `src/api/services/proof_pack_service.py`,
  `src/api/services/proof_pack_handoff_refs.py`,
  `tests/unit/dpm/proof_packs/test_proof_pack_handoff_refs.py`, selected proof-pack regressions,
  and this ledger.
- Finding: proof-pack report-input and AI-evidence ref accessors repeated the hydrated-ref,
  append-only stored-ref, and missing-generated-ref decision path inside the service, making the
  supportability fallback harder to test directly.
- Action: extracted the common handoff-ref resolution decision into the handoff-ref helper,
  preserving service-specific generated-ref exceptions while adding direct tests for hydrated-ref
  preference, latest stored-ref fallback, and missing-ref return behavior.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `proof_pack_service.py` and `proof_pack_handoff_refs.py`; direct proof-pack
  handoff-ref tests and selected proof-pack service regressions passed with 19 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing proof-pack generation flow for builder-input assembly that can be
  separated without moving source lookup or exception ownership out of the service.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-411: Outcome review persistence retention extraction

- Date: 2026-06-01
- Scope: `src/api/services/outcome_review_service.py`,
  `src/api/services/outcome_review_persistence.py`,
  `tests/unit/dpm/outcomes/test_outcome_review_persistence.py`, selected outcome-review
  regressions, and this ledger.
- Finding: outcome review creation orchestration still owned the seven-year evidence-retention
  calculation directly, duplicating the persistence-policy pattern found in proof-pack generation.
- Action: extracted outcome-review persistence and retention-expiry calculation into a focused
  helper, kept review creation orchestration in the service, and added direct tests for
  deterministic seven-year retention expiry and the helper export surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `outcome_review_service.py` and `outcome_review_persistence.py`; direct outcome
  review persistence tests and selected outcome/API regressions passed with 40 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing outcome-review creation for event/content assembly boundaries that
  can be tested directly without moving repository idempotency ownership.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-412: Outcome review creation assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/outcome_review_service.py`,
  `src/api/services/outcome_review_creation.py`,
  `tests/unit/dpm/outcomes/test_outcome_review_creation.py`, selected outcome-review regressions,
  and this ledger.
- Finding: outcome review creation orchestration still assembled the full persisted review object
  directly after idempotency validation, mixing repository control flow with pure review/event
  payload assembly already partially owned by `outcome_review_creation.py`.
- Action: extracted persisted outcome-review assembly into the creation helper, kept idempotency,
  clock/id generation, and persistence in the service, and added direct tests for source lineage,
  identity, event, hash, actor, correlation, and idempotency propagation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `outcome_review_service.py` and `outcome_review_creation.py`; direct outcome review
  creation tests and selected outcome/API regressions passed with 41 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing outcome refresh and proof-pack generation for pure event/input
  assembly that can move out of orchestration services with direct tests.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-413: Outcome review refresh assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/outcome_review_service.py`,
  `src/api/services/outcome_review_refresh.py`,
  `tests/unit/dpm/outcomes/test_outcome_review_refresh.py`, selected outcome-review regressions,
  and this ledger.
- Finding: outcome review source-refresh orchestration still performed dimension comparison and
  refreshed-event assembly inline, mixing repository lookup/append control flow with pure refresh
  payload assembly.
- Action: extracted source-refresh comparison and event assembly into the refresh helper, kept
  review lookup, clock/suffix generation, and append persistence in the service, and added direct
  tests that prove snapshot comparison output drives refreshed-event state, reason codes, and
  source lineage.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `outcome_review_service.py` and `outcome_review_refresh.py`; direct outcome review
  refresh tests and selected outcome/API regressions passed with 42 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing proof-pack generation and rebalance orchestration for pure
  builder-input assembly that can move behind direct helper tests.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-414: Proof-pack generation assembly extraction

- Date: 2026-06-01
- Scope: `src/api/services/proof_pack_service.py`,
  `src/api/services/proof_pack_generation.py`,
  `tests/unit/dpm/proof_packs/test_proof_pack_generation.py`, selected proof-pack regressions,
  and this ledger.
- Finding: proof-pack generation orchestration still mapped resolved run, selected-alternative,
  mandate-evidence, workflow-decision, and regime-stress inputs directly into core proof-pack
  builders, mixing source lookup/replay/persistence control flow with pure builder-input assembly.
- Action: extracted run and selected-alternative proof-pack assembly into a focused helper, kept
  replay, source lookup, mandate evidence lookup, and persistence in the service, and added direct
  tests for resolved source/evidence propagation into the core builders.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `proof_pack_service.py` and `proof_pack_generation.py`; direct proof-pack generation
  tests and selected proof-pack service/builder regressions passed with 43 tests; OpenAPI quality
  gate passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed;
  service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing generation services for remaining source lookup and persistence
  seams that can be clarified without hiding ownership or idempotency behavior.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-415: Mandate health persistence extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`,
  `src/api/services/mandate_health_persistence.py`,
  `tests/unit/dpm/mandates/test_mandate_health_persistence.py`, selected mandate regressions, and
  this ledger.
- Finding: mandate refresh, recalculation, and monitoring flows repeated health-snapshot and
  monitoring-exception persistence loops in the orchestration service, making evidence persistence
  behavior harder to test directly.
- Action: extracted mandate health evidence persistence into a focused helper, kept source
  resolution, health calculation, monitoring-run aggregation, and repository lookup ownership in
  the service, and added direct tests for twin-backed and health-only persistence paths plus the
  service compatibility alias.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_health_persistence.py`; direct mandate health
  persistence tests and selected mandate refresh/API regressions passed with 36 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing mandate monitoring orchestration for aggregation boundaries that
  can be isolated without hiding lookup or run lifecycle ownership.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-416: Mandate monitoring aggregation extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`,
  `src/api/services/mandate_monitoring_run.py`,
  `tests/unit/dpm/mandates/test_mandate_monitoring_run.py`, selected mandate regressions, and this
  ledger.
- Finding: mandate monitoring orchestration still owned mutable health-distribution,
  source-readiness, and exception-count aggregation inside the service loop, mixing run accounting
  with mandate lookup, health calculation, and persistence flow.
- Action: introduced a monitoring-run accumulator in the monitoring helper, kept repository lookup
  and run lifecycle orchestration in the service, and added direct tests proving repeated mandate
  results update health distribution, source-readiness summary, and exception count consistently.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_monitoring_run.py`; direct mandate monitoring
  helper tests and selected mandate API regressions passed with 31 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing mandate service read-model and command-center assembly boundaries
  for directly testable extraction opportunities.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-417: Mandate command-center run selection extraction

- Date: 2026-06-01
- Scope: `src/api/services/mandate_service.py`,
  `src/api/services/mandate_command_center.py`,
  `tests/unit/dpm/mandates/test_mandate_command_center.py`, selected mandate regressions, and this
  ledger.
- Finding: command-center summary orchestration still embedded latest monitoring-run selection in
  the service, while the command-center helper already owned filter semantics and summary
  projection.
- Action: extracted latest command-center run selection into the command-center helper, kept
  repository reads and active-exception lookup in the service, and added direct tests for first
  matching run selection, missing-match behavior, export surface, and service compatibility alias.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `mandate_service.py` and `mandate_command_center.py`; direct mandate command-center
  helper tests and selected mandate API regressions passed with 32 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing command-center service orchestration for active-exception query
  and summary-input boundaries that can be clarified without hiding repository ownership.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-418: Wave transition execution extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_transition_execution.py`,
  `tests/unit/dpm/waves/test_wave_transition_execution.py`, selected wave regressions, and this
  ledger.
- Finding: wave source-check, simulation, approval, staging, and handoff orchestration repeated
  the same lookup, idempotent replay, state guard, and optimistic update flow, increasing the
  chance of inconsistent transition enforcement across DPM wave lifecycle endpoints.
- Action: extracted common wave transition preparation and persistence into a focused helper,
  preserved transition-specific builder logic in the service, and added direct tests for replay
  handling, required-state validation, expected-version update behavior, export surface, and
  service compatibility aliases.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_transition_execution.py`; direct wave transition
  execution tests and selected wave lifecycle/API regressions passed with 154 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing wave cancellation and selection flows for transition semantics that
  can be normalized without hiding route-level business decisions.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-419: Wave cancellation transition normalization

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_transition_execution.py`,
  `tests/unit/dpm/waves/test_wave_transition_execution.py`, selected wave cancellation/API
  regressions, and this ledger.
- Finding: wave cancellation still repeated load, replay, and optimistic update behavior outside
  the shared transition execution helper because cancellation is intentionally available without a
  required source state guard.
- Action: extended the transition helper to model explicitly unguarded transitions with
  `allowed_states=None`, routed cancellation through the same preparation and persistence helpers,
  and added direct tests proving unguarded transitions still load the wave and report non-replay
  state without applying a state guard.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_transition_execution.py`; direct wave transition
  execution tests and selected wave cancellation/API regressions passed with 143 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing wave selection flow for remaining lifecycle orchestration that can
  share transition persistence without obscuring selection-specific source validation.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-420: Wave selection transition execution normalization

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_transition_execution.py`,
  `tests/unit/dpm/waves/test_wave_transition_execution.py`, selected wave selection/API
  regressions, and this ledger.
- Finding: wave alternative selection still performed lookup, state guard, and optimistic update
  directly in the orchestration service after the common transition helper existed, while the
  selection flow has no idempotent replay state and should model that explicitly.
- Action: routed selection through the transition helper with `replay_states=set()`, kept
  selection-specific source validation and proof-pack builder logic in the service, and added direct
  helper tests proving empty replay-state transitions still enforce the allowed source state.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_transition_execution.py`; direct wave transition
  execution tests and selected wave selection/API regressions passed with 149 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing wave selection source-validation and proof-pack generation
  boundaries for smaller directly tested helper seams.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-421: Wave read-model query extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_read_model_queries.py`,
  `tests/unit/dpm/waves/test_wave_read_model_queries.py`, selected wave read/API regressions, and
  this ledger.
- Finding: wave supportability, detail, item listing, proof-pack posture, and report-input read
  functions repeated wave lookup and projection wiring in `wave_service.py`, keeping read-model
  assembly mechanics mixed into the lifecycle command facade.
- Action: extracted wave-id read-model query helpers that load the governed wave once and delegate
  to the existing projection/report builders, kept the service API as a thin facade, and added
  direct tests for read-model loading, report-input assembly, export surface, and service
  delegation aliases.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_read_model_queries.py`; direct wave read-model query tests
  and selected wave read/API regressions passed with 149 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reviewing wave creation/idempotency orchestration for small support helpers
  that preserve repository ownership while reducing command-service branching.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-422: Wave create command extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_create_command.py`,
  `tests/unit/dpm/waves/test_wave_create_command.py`, selected wave create/API regressions, and
  this ledger.
- Finding: wave creation orchestration still embedded idempotent replay lookup, request-hash
  construction, preview promotion, and durable save wiring in `wave_service.py`, keeping command
  persistence mechanics mixed into the public service facade.
- Action: extracted the idempotent create command into a focused helper that owns replay lookup,
  preview construction, created-wave promotion, and durable persistence, kept the service API as a
  stable facade, and added direct tests for replay, persistence request hash, export surface, and
  service delegation alias.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_create_command.py`; direct wave create-command tests and
  selected wave create/API regressions passed with 150 tests; OpenAPI quality gate passed; API
  vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage scan
  found no router/HTTP imports in service modules.
- Follow-up: continue reviewing wave command orchestration for lifecycle-specific source and
  supportability boundaries that can be isolated without hiding domain decisions.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-423: Construction source-product identity extraction

- Date: 2026-06-01
- Scope: `src/api/services/construction_source_identity.py`,
  `src/api/services/construction_liquidity_source_context.py`,
  `src/api/services/construction_client_profile_source_context.py`,
  `tests/unit/dpm/construction/test_source_identity.py`, selected construction source-context
  regressions, and this ledger.
- Finding: construction source-product mappers repeated the same product name, product version,
  source system, source id, and content-hash assembly across liquidity reserve, planned
  withdrawal, income-needs, restriction, and sustainability contexts, increasing lineage drift risk.
- Action: introduced a reusable `SourceProductIdentity` bundle in the construction source identity
  helper, routed liquidity and client-profile source-product mappers through it, removed unused
  mapper-local source response aliases, and added direct tests proving product identity and lineage
  hashing are assembled consistently.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_source_identity.py`, `construction_liquidity_source_context.py`, and
  `construction_client_profile_source_context.py`; direct construction source identity tests and
  selected construction source-context/API regressions passed with 49 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue applying the source-product identity helper to treasury, transaction-cost,
  and execution acknowledgement mappers where it reduces duplication without weakening contract
  clarity.
- Wiki decision: no wiki source change required; this is internal mapper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-424: Construction execution source identity normalization

- Date: 2026-06-01
- Scope: `src/api/services/construction_source_identity.py`,
  `src/api/services/construction_transaction_cost_source_context.py`,
  `src/api/services/construction_execution_source_context.py`,
  `tests/unit/dpm/construction/test_source_identity.py`, selected construction transaction-cost and
  execution source-context regressions, and this ledger.
- Finding: transaction-cost and external execution acknowledgement mappers still assembled
  source-product identity fields locally after the shared identity helper existed; transaction-cost
  also needed its governed page fingerprint fallback preserved explicitly.
- Action: extended `source_product_identity` with an explicit fallback source-id parameter, routed
  transaction-cost and execution acknowledgement mappers through the shared helper, and added direct
  tests proving explicit fallback lineage remains available when source lineage is absent.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_source_identity.py`,
  `construction_transaction_cost_source_context.py`, and
  `construction_execution_source_context.py`; direct construction source identity tests and
  selected transaction-cost/execution source-context/API regressions passed with 41 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: review treasury currency-overlay source identity helpers separately because its
  multi-source aggregate hash and optional child-source fields require a narrower treatment than
  single-source mappers.
- Wiki decision: no wiki source change required; this is internal mapper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-425: Treasury currency-overlay source identity normalization

- Date: 2026-06-01
- Scope: `src/api/services/construction_treasury_source_context.py`, selected treasury
  source-context/API regressions, and this ledger.
- Finding: the treasury currency-overlay mapper retained bespoke optional source-id and content-hash
  assembly for hedge readiness, currency exposure, hedge policy, eligible instruments, and FX
  forward curves after the shared source-product identity helper existed.
- Action: introduced a treasury-local optional identity adapter backed by `source_product_identity`,
  preserved the aggregate currency-overlay content hash and hedge-readiness aggregate fallback, and
  routed all optional child source-product identity fields through the shared identity bundle.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `construction_treasury_source_context.py`; direct treasury source-context tests and
  selected construction source-context/API regressions passed with 35 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing construction service orchestration now that source-product lineage
  identity has a consistent helper across single-source and treasury multi-source mappers.
- Wiki decision: no wiki source change required; this is internal mapper modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-426: Wave lifecycle command extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_lifecycle_commands.py`,
  `tests/unit/dpm/waves/test_wave_lifecycle_commands.py`, selected wave lifecycle/API regressions,
  and this ledger.
- Finding: wave approval, staging, handoff, and cancellation repeated transition preparation,
  idempotent replay handling, transition builder invocation, and optimistic persistence directly in
  `wave_service.py`, even after shared transition execution helpers existed.
- Action: extracted persisted wave lifecycle command helpers for approval, staging, handoff, and
  cancellation, kept the public service API as a facade, preserved service compatibility aliases,
  and added direct tests for command persistence, expected-version handling, replay, export surface,
  and service delegation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_lifecycle_commands.py`; direct wave lifecycle command
  tests and selected wave lifecycle/API regressions passed with 162 tests; OpenAPI quality gate
  passed; API vocabulary inventory validate-only gate passed; `git diff --check` passed; service
  leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing source-check, simulation, and selection command boundaries for
  similarly narrow command extraction opportunities without obscuring domain-specific dependencies.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-427: Wave preparation command extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_preparation_commands.py`,
  `tests/unit/dpm/waves/test_wave_preparation_commands.py`, selected wave preparation/API
  regressions, and this ledger.
- Finding: wave source-check and simulation orchestration still repeated transition preparation,
  idempotent replay handling, domain builder invocation, and optimistic persistence directly in
  `wave_service.py`, leaving the facade responsible for command execution mechanics.
- Action: extracted persisted source-check and simulation command helpers, kept source-readiness and
  construction simulation builders unchanged, preserved service entry points as facades, and added
  direct tests for persistence, replay, expected-version handling, export surface, and service
  delegation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_preparation_commands.py`; direct wave preparation command
  tests and selected wave source-check/simulation/API regressions passed with 150 tests; OpenAPI
  quality gate passed; API vocabulary inventory validate-only gate passed; `git diff --check`
  passed; service leakage scan found no router/HTTP imports in service modules.
- Follow-up: continue reviewing wave alternative selection as the remaining command path with
  selection-specific repository side effects and proof-pack generation dependencies.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-428: Wave selection command extraction

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `src/api/services/wave_selection_command.py`,
  `tests/unit/dpm/waves/test_wave_selection_command.py`, selected wave selection/API regressions,
  and this ledger.
- Finding: wave alternative selection remained the last command body in `wave_service.py`, mixing
  transition preparation, selectable-item validation, construction alternative selection, proof-pack
  transition building, and optimistic persistence in the service facade.
- Action: extracted a persisted wave selection command helper, kept selection-specific side effects
  and proof-pack generation wiring together, preserved service compatibility aliases, and added
  direct tests for selection side-effect wiring, expected-version persistence, export surface, and
  service delegation.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py` and `wave_selection_command.py`; direct wave selection command tests
  and selected wave selection/API regressions passed with 148 tests; OpenAPI quality gate passed;
  API vocabulary inventory validate-only gate passed; `git diff --check` passed; service leakage
  scan found no router/HTTP imports in service modules.
- Follow-up: review `wave_service.py` compatibility aliases and remaining facade imports for stale
  test-only surface that can be retired safely in a later cleanup slice.
- Wiki decision: no wiki source change required; this is internal service modularity cleanup with no
  route, payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-429: Wave service stale alias removal

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, selected wave helper/facade regressions, and this
  ledger.
- Finding: after wave create, preparation, lifecycle, and selection command extraction,
  `wave_service.py` still imported and re-exported several private compatibility aliases that were
  no longer used by service code or direct helper tests.
- Action: removed stale private aliases and their imports for simulation result state, create helper
  internals, lifecycle transition builders, and event construction, moved remaining API tests to the
  owning helper modules, and preserved explicitly covered compatibility aliases that still document
  helper ownership boundaries.
- Status: hardened
- Evidence: focused Ruff and format checks passed for `wave_service.py` and the touched wave API
  regression file; focused mypy passed for `wave_service.py`; selected wave helper/facade tests and
  wave API regressions passed with 190 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue retiring remaining compatibility aliases only when their direct tests have
  moved to the owning helper module and no service facade contract depends on them.
- Wiki decision: no wiki source change required; this is internal dead-code cleanup with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-430: Wave workflow metadata alias retirement

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `tests/unit/dpm/waves/test_wave_workflow_metadata.py`, selected wave workflow metadata/API
  regressions, and this ledger.
- Finding: `wave_service.py` still retained private aliases for workflow metadata helpers even
  though the owning `wave_workflow_metadata` module has direct behavior and export-surface tests.
- Action: removed workflow metadata helper imports and private aliases from the service facade, and
  retired the service-alias assertion so tests verify the owning helper module instead of preserving
  stale facade surface.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py`; direct workflow metadata tests and selected wave command/API
  regressions passed with 146 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue retiring remaining service compatibility aliases in small batches when direct
  helper tests already prove ownership and no route or service API depends on the alias.
- Wiki decision: no wiki source change required; this is internal dead-code cleanup with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-431: Wave event collection alias retirement

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`,
  `tests/unit/dpm/waves/test_wave_event_append.py`,
  `tests/unit/dpm/waves/test_wave_item_collection.py`, selected wave event/item API regressions,
  and this ledger.
- Finding: `wave_service.py` still imported and exposed private compatibility aliases for wave event
  append and item collection helpers even though the owning helper modules already carry direct
  behavior and export-surface tests.
- Action: removed the stale event append and item collection imports and aliases from the service
  facade, and retired tests that pinned obsolete private facade surface while keeping direct helper
  behavior coverage.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py`; direct wave event append and item collection tests plus selected
  wave API regressions passed with 139 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue retiring lookup, persistence, state-guard, transition, and selection
  compatibility aliases in similarly narrow slices when their owning helper tests provide direct
  coverage.
- Wiki decision: no wiki source change required; this is internal dead-code cleanup with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-432: Wave lookup persistence alias retirement

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `tests/unit/dpm/waves/test_wave_lookup.py`,
  `tests/unit/dpm/waves/test_wave_persistence.py`, selected wave lookup/write API regressions, and
  this ledger.
- Finding: `wave_service.py` still exposed private lookup and persistence aliases after command
  extraction moved persisted wave reads and writes into owning helper modules.
- Action: removed the stale lookup, save, and update imports and aliases from the service facade,
  and retired alias-pinning assertions so tests verify `wave_lookup` and `wave_persistence`
  directly.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py`; direct wave lookup and persistence tests plus selected wave API
  regressions passed with 141 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue retiring the remaining state guard, trigger validation, transition execution,
  and selection helper aliases without changing public wave route behavior.
- Wiki decision: no wiki source change required; this is internal dead-code cleanup with no route,
  payload, supported-feature, or operator-contract change.

## BACKEND-REVIEW-20260601-433: Wave state trigger alias retirement

- Date: 2026-06-01
- Scope: `src/api/services/wave_service.py`, `tests/unit/dpm/waves/test_wave_state_guard.py`,
  `tests/unit/dpm/waves/test_wave_trigger_validation.py`, selected wave API regressions, and this
  ledger.
- Finding: `wave_service.py` still retained private state guard and trigger validation aliases even
  though wave command helpers own guard invocation and direct helper tests prove the validation
  behavior.
- Action: removed state guard and trigger validation imports and aliases from the service facade,
  and retired facade-alias assertions while preserving helper behavior and export-surface coverage.
- Status: hardened
- Evidence: focused Ruff and format checks passed for the touched source/test files; focused mypy
  passed for `wave_service.py`; direct wave state guard and trigger validation tests plus selected
  wave API regressions passed with 143 tests; OpenAPI quality gate passed; API vocabulary inventory
  validate-only gate passed; `git diff --check` passed; service leakage scan found no router/HTTP
  imports in service modules.
- Follow-up: continue retiring transition execution and selection helper aliases now that remaining
  service imports are concentrated around command facade delegation and public read/write entry
  points.
- Wiki decision: no wiki source change required; this is internal dead-code cleanup with no route,
  payload, supported-feature, or operator-contract change.
