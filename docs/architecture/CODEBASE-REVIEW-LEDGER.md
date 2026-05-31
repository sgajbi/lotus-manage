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
