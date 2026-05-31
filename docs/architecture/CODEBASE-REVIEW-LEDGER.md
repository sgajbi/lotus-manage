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
