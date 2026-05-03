# Endpoint Certification

This page records endpoint-by-endpoint certification evidence for `lotus-manage`. It is scoped to
implementation-backed API readiness before broader Gateway or Workbench integration is treated as
demo proof.

## Certification standard

An endpoint is complete only when these checks are true:

1. functional behavior is tested across supported options, flags, and output fields,
2. non-functional posture is clear: latency shape, statefulness, retry/idempotency behavior,
   supportability, and bounded failure modes,
3. upstream source-data authority is identified and any missing upstream integration is explicit,
4. downstream consumers are identified and stale or duplicate usage has a tracked remediation issue,
5. Swagger explains what the endpoint is for, when to use it, and documents every request and
   response attribute with examples; route-local examples are preferred for business-critical
   outcomes and schema-derived examples are used as a minimum guard for every JSON request and
   response contract; every documented `4xx`, `5xx`, and `default` response must also include a
   bounded JSON error example,
6. live API evidence has been captured against a running `lotus-manage` instance.

## Certified endpoint family: service health probes

Routes:

- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`

Purpose:

Operational probe surface for platform ingress, Docker health checks, and service monitoring. These
routes are platform/runtime endpoints, not discretionary mandate execution or advisory workflow
APIs.

Functional behavior:

- `/health` returns `{ "status": "ok" }` for lightweight service health.
- `/health/live` returns `{ "status": "live" }` and deliberately does not touch persistence
  dependencies; use it for process liveness probes.
- `/health/ready` returns `{ "status": "ready" }` only after persistence profile guardrails pass.
- In production profile, readiness also validates required cutover migrations before reporting
  ready.
- Health probes are infrastructure endpoints and intentionally remain unversioned.
- `/metrics` exposes Prometheus metrics for platform scraping and runtime monitoring. It is an
  infrastructure endpoint, not a business-data API.

```mermaid
flowchart LR
    Platform[Container, ingress, or monitor] --> Health[GET /health]
    Platform --> Live[GET /health/live]
    Platform --> Ready[GET /health/ready]
    Platform --> Metrics[GET /metrics]
    Health --> Ok[status ok]
    Live --> Process[process liveness only]
    Ready --> Guardrails[Persistence profile guardrails]
    Guardrails --> Profile{Production profile?}
    Profile -->|no| ReadyStatus[status ready]
    Profile -->|yes| Migrations[Cutover migration validation]
    Migrations --> ReadyStatus
    Metrics --> Prometheus[Prometheus scrape]
```

Non-functional posture:

- Liveness is intentionally low-latency and side-effect free.
- Readiness is stricter than liveness so orchestration does not route traffic to a runtime whose
  persistence profile or production migrations are invalid.
- The response model is intentionally small and typed: `status` is limited to `ok`, `live`, or
  `ready`.
- These endpoints perform no calls to `lotus-core`, `lotus-advise`, Gateway, or Workbench.
- Swagger documents `/metrics` as Prometheus text exposition, not JSON.
- Metrics labels must remain bounded and must not expose portfolio ids, client names, account ids,
  request hashes, idempotency keys, correlation ids, run ids, raw upstream errors, or diagnostics
  payloads.

Downstream consumers:

- Docker compose uses `/health/ready` for container health.
- Platform ingress and runtime monitors should use `/health/live` for process liveness and
  `/health/ready` for traffic readiness.
- Platform monitoring scrapes `/metrics`.
- Product clients should not infer DPM feature availability from these routes; use
  `/api/v1/integration/capabilities` for capability posture.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_observability_api.py::test_health_endpoints_available tests/unit/dpm/api/test_observability_api.py::test_health_ready_validates_cutover_migrations_in_production tests/unit/dpm/api/test_observability_api.py::test_health_ready_skips_cutover_migrations_outside_production tests/unit/dpm/api/test_observability_api.py::test_health_live_does_not_touch_readiness_dependencies tests/unit/dpm/api/test_observability_api.py::test_action_register_supportability_metric_labels_are_bounded tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_openapi_json_requests_and_responses_have_examples tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_openapi_error_responses_have_json_examples tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_metrics_openapi_documents_prometheus_text_response tests/unit/test_validate_live_api.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

The live validator now also checks the deployed OpenAPI certification contract. A runtime with
passing business probes but stale Swagger examples or a JSON `/metrics` contract is not considered
gold-pass certified.

## Certified endpoint: capabilities discovery

Routes:

- `GET /api/v1/integration/capabilities`

Purpose:

Backend-owned discretionary mandate feature and workflow discovery for Gateway, platform consumers,
and future UI gating. This is a control-plane contract, not a source-data read and not a simulation
state read.

Canonical request shape:

- `consumer_system`
- `tenant_id`

The endpoint intentionally uses canonical source-service snake_case query parameters. Gateway may
continue exposing camelCase on its public BFF contract, but direct source-service calls must use
snake_case.

Functional coverage:

- default consumer and tenant resolution,
- explicit consumer and tenant resolution,
- conservative default input-mode posture,
- environment-controlled stateful `portfolio_id` publication,
- environment-controlled `stateless` publication,
- runtime solver dependency discovery,
- noncanonical camelCase direct-source query parameters fail closed with `422`,
- unknown consumer-system values fail contract validation with `422`.

Default capability posture:

- `stateless` execution is enabled,
- stateful `portfolio_id` execution is disabled until governed `lotus-core` state resolution is
  configured,
- workflow review gates are disabled until explicitly enabled,
- solver-backed target generation is runtime-discovered,
- action-register supportability is always published as a source-backed feature.

Upstream integration posture:

This endpoint has no outbound source-data dependency. It publishes runtime and policy posture from
environment configuration plus local solver dependency discovery. Future stateful `portfolio_id`
execution must integrate through governed `lotus-core` contracts before the feature is enabled by
default.

Downstream consumers:

- `lotus-gateway` platform capabilities aggregation is the strategic downstream consumer.
- `lotus-workbench` consumes the Gateway BFF contract rather than calling `lotus-manage` directly.

Certification finding and tracked downstream remediation:

- `sgajbi/lotus-gateway#178` tracks Gateway cleanup for direct source-service query parameters,
  stale proposal/advisory-era DPM client methods, and normalized capability mapping from strategic
  `lotus-manage` DPM feature/workflow keys. Gateway currently calls the removed
  `/api/v1/platform/capabilities` alias with camelCase query parameters; the certified
  source-service contract is `/api/v1/integration/capabilities` with `consumer_system` and
  `tenant_id`.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_integration_capabilities_api.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint family: mandate digital twin foundation

Routes:

- `GET /api/v1/mandates/by-portfolio/{portfolio_id}`
- `GET /api/v1/mandates/{mandate_id}`
- `GET /api/v1/mandates/{mandate_id}/versions`
- `GET /api/v1/mandates/{mandate_id}/diff`
- `POST /api/v1/mandates/{mandate_id}/refresh-from-core`
- `GET /api/v1/mandates/{mandate_id}/health`
- `POST /api/v1/mandates/{mandate_id}/health/recalculate`
- `POST /api/v1/dpm/monitoring/run-once`
- `GET /api/v1/dpm/monitoring/runs`
- `GET /api/v1/dpm/monitoring/runs/{monitoring_run_id}`
- `GET /api/v1/dpm/command-center`
- `GET /api/v1/dpm/exceptions`
- `POST /api/v1/dpm/exceptions/{exception_id}/resolve`

Purpose:

RFC-0038 mandate digital-twin foundation for discretionary portfolio management. These endpoints
let lotus-manage refresh mandate state from product-specific `lotus-core` source products, persist
the compiled mandate digital twin, read the latest portfolio or mandate view, inspect version
history, explain what changed between versions, recalculate health, run bounded mandate monitoring,
search monitoring runs, summarize a bounded command-center view, search exception queues, and
resolve reviewed exceptions. They are not advisory proposal endpoints and do not claim Gateway or
Workbench product-surface integration.

Functional behavior:

- `refresh-from-core` composes `DiscretionaryMandateBinding:v1`,
  `DpmModelPortfolioTarget:v1`, and optional `MarketDataCoverageWindow:v1`.
- Refresh returns the persisted `DpmMandateDigitalTwin`, a generated mandate-health snapshot,
  derived monitoring exceptions, and explicit field-gap codes for source products not yet
  available in core.
- Read by portfolio and read by mandate return only previously refreshed state and return `404`
  when no mandate snapshot exists.
- Version listing returns persisted mandate twins newest first.
- Diff compares the latest two versions by default, or caller-supplied `from_version` and
  `to_version`, and labels materiality for changed mandate fields.
- Health read returns the latest persisted mandate health snapshot.
- Health recalculate persists a new snapshot and derived exceptions from explicit monitoring input.
- Monitoring run-once evaluates caller-supplied mandate ids that have already been refreshed.
- Monitoring run search and detail return persisted run records.
- Command center aggregates persisted monitoring runs and active exceptions into health
  distribution, attention buckets, recommended actions, and supportability state.
- Exception search supports mandate, portfolio, state, cursor, and limit filters.
- Exception resolve requires an auditable resolution reason and returns the resolved exception.
- Core unavailable maps to `503 DPM_MANDATE_SOURCE_UNAVAILABLE`.
- Core incomplete maps to `424 DPM_MANDATE_SOURCE_INCOMPLETE`.
- Legacy unversioned aliases such as `/mandates/{mandate_id}` remain absent.

```mermaid
flowchart LR
    Caller[Gateway, operator, or validation probe] --> Refresh[POST /api/v1/mandates/{mandate_id}/refresh-from-core]
    Refresh --> Binding[lotus-core mandate binding]
    Refresh --> Targets[lotus-core model targets]
    Refresh --> Coverage[lotus-core market-data coverage]
    Binding --> Twin[DPM mandate digital twin]
    Targets --> Twin
    Coverage --> Health[Mandate health snapshot]
    Twin --> Repo[(Mandate repository)]
    Health --> Repo
    Repo --> Read[Read by portfolio or mandate]
    Repo --> Versions[Version history]
    Versions --> Diff[Version diff]
    Repo --> HealthRead[Health read]
    Health --> Monitoring[Monitoring run-once]
    Monitoring --> CommandCenter[DPM command center]
    Monitoring --> ExceptionQueue[Exception queue and resolution]
```

Non-functional posture:

- The refresh command is a bounded source-product composition. It does not call the retired
  monolithic DPM execution-context route and does not source raw portfolio ledger truth locally.
- The API preserves source-lineage records from core and keeps missing source products explicit
  through `field_gap_codes`.
- Diff output is deterministic and ignores volatile source-lineage ordering.
- The default repository profile is in-memory for local runtime and tests; the Postgres repository
  and migrations exist for production profile wiring.
- Swagger groups the endpoints under `lotus-manage Mandates` with route-local examples and bounded
  failure descriptions.

Upstream integration posture:

`lotus-core` remains authoritative for mandate binding, model targets, market data, portfolio state,
eligibility, tax lots, cash, prices, and FX. RFC-0038 Slice 3 uses only the source products required
to compile the minimum viable mandate twin. Objective profile, client restriction profile,
sustainability preference profile, and portfolio cash-flow forecast remain explicit source-data
gaps until core exposes them as governed data products.

Downstream consumers:

- No production downstream consumer is assumed for the new RFC-0038 target APIs.
- Future `lotus-gateway` and `lotus-workbench` integration should consume these routes through a
  certified Gateway contract rather than reconstructing mandate state client-side.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_mandates_api.py tests/unit/dpm/core/test_mandate_health.py tests/unit/dpm/supportability/test_dpm_mandate_repository.py tests/integration/test_openapi_certification_matrix.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint family: construction alternatives foundation

Routes:

- `POST /api/v1/construction/alternative-sets/generate`
- `GET /api/v1/construction/alternative-sets/{alternative_set_id}`
- `POST /api/v1/construction/alternative-sets/{alternative_set_id}/selections`

Purpose:

RFC-0039 manage-side backend foundation for discretionary portfolio construction alternatives.
These endpoints generate, persist, retrieve, and select a comparable set of construction choices
for one mandate execution context. They support portfolio-manager decisioning before proof packs,
workflow approval, rebalance waves, or downstream product-surface integration. They are not order
execution endpoints and are not advisor-led proposal endpoints.

Functional behavior:

- Generate accepts the same explicit execution envelope posture as rebalance simulation: stateless
  inline snapshots or stateful lotus-core source resolution when the stateful core resolver is
  enabled.
- Generate requires `Idempotency-Key`; a same-key same-request replay returns the original
  alternative set, while same-key different-request usage returns `409`.
- First-wave generation returns do-nothing baseline, explainable heuristic, minimum-turnover, and
  tax-aware posture unless a caller explicitly narrows the method list.
- Authority-backed construction methods return explicit method plans, supportability states, and
  method-specific source-authority context. `SOLVER_CONSTRAINED`, `RISK_AWARE`,
  `LIQUIDITY_AWARE`, `CURRENCY_OVERLAY`, and `REGIME_STRESS_AWARE` must not report `READY` when
  required authority evidence is absent.
- `ESG_AWARE` is explicitly deferred and degrades with
  `ESG_RESTRICTION_AWARE_CONSTRUCTION_DEFERRED` until restriction and sustainability source
  products exist.
- Do-nothing baseline keeps trade count and turnover at zero so "take no action" is visible as a
  governed comparator.
- Minimum-turnover applies a stricter turnover posture and surfaces pending-review behavior when
  turnover budget drops intents.
- Tax-aware posture uses tax-aware engine behavior where tax lots are available and exposes
  degraded supportability reason codes where authoritative transaction cost, risk, or performance
  enrichment is absent.
- Read returns a persisted alternative set by id without recomputation.
- Select records an actor-attributed selection decision with reason code, optional comment, and
  optional correlation id. It does not execute trades.
- Unknown alternative sets and unknown alternative ids return governed `404` errors.

```mermaid
flowchart LR
    Caller[Gateway, operator, or certification probe] --> Generate[POST generate]
    Generate --> Envelope[Stateless bundle or gated stateful core context]
    Envelope --> Methods[First-wave and authority-backed methods]
    Methods --> Baseline[Do-nothing baseline]
    Methods --> Heuristic[Explainable heuristic]
    Methods --> Turnover[Minimum-turnover posture]
    Methods --> Tax[Tax-aware posture]
    Methods --> Risk[Risk-aware via lotus-risk concentration]
    Methods --> Liquidity[Liquidity and settlement aware]
    Methods --> Currency[Currency-overlay policy]
    Methods --> Regime[Regime-stress scenario pack]
    Baseline --> Set[Persisted alternative set]
    Heuristic --> Set
    Turnover --> Set
    Tax --> Set
    Risk --> Set
    Liquidity --> Set
    Currency --> Set
    Regime --> Set
    Set --> Read[GET alternative set]
    Set --> Select[POST selection decision]
```

Non-functional posture:

- The route family is grouped under `lotus-manage Construction Alternatives`.
- OpenAPI includes route-level request/response examples and bounded error descriptions.
- Persistence is behind `ConstructionRepository`, with in-memory local/test support and a Postgres
  repository plus migration for production profile wiring.
- Selection is an audit decision, not an execution command.
- Gateway and Workbench are not yet integrated; paired realization RFCs are written after manage
  proof and hardening when the backend contract and evidence are stable.
- The first-wave and authority-backed generate/read/select contracts are live-proven through the
  repeatable validator against a canonical manage runtime.

Upstream integration posture:

Stateless calls rely on caller-provided source-governed snapshots. Stateful calls use the existing
gated lotus-core source resolver from RFC-0036/RFC-0087 and preserve source supportability state on
the alternative set. `RISK_AWARE` can consume `lotus-risk` concentration authority through the
bounded risk-authority client when configured. `REGIME_STRESS_AWARE` requires source-backed
scenario-pack authority context until a first-class risk/CIO scenario endpoint exists.
`lotus-manage` does not become authority for portfolio ledger state, risk methodology, performance,
tax lots, market data, eligibility, ESG/restriction profiles, or UI composition.

Downstream consumers:

No current production Gateway or Workbench consumer is assumed. Gateway and Workbench must consume
this surface only after paired realization RFCs define the composition contract and user
experience from the implemented manage evidence.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/construction tests/unit/dpm/api/test_construction_api.py -q
python -m pytest tests/unit/dpm/infrastructure/test_risk_authority_client.py -q
python scripts/openapi_quality_gate.py
python -m pytest tests/integration/test_openapi_certification_matrix.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
powershell -ExecutionPolicy Bypass -File scripts/Start-CanonicalManage.ps1 -Port 8020
python scripts/validate_live_api.py --base-url http://127.0.0.1:8020 --skip-demo-pack --json-output output/rfc0039-proof/<timestamp>-authority-backed-canonical/summary.json
```

## Certified endpoint family: policy-pack read supportability

Routes:

- `GET /api/v1/rebalance/policies/effective`
- `GET /api/v1/rebalance/policies/catalog`

Purpose:

Management-side discretionary mandate policy controls for supportability, tenant diagnostics, and
pre-execution integration checks. These endpoints are not advisory proposal APIs; advisor-led
proposal and lifecycle flows belong in `lotus-advise`.

Functional behavior:

- Effective policy resolution uses deterministic precedence: request-scoped `X-Policy-Pack-Id`,
  then tenant default `X-Tenant-Policy-Pack-Id`, then tenant resolver lookup by `X-Tenant-Id`, then
  global default `DPM_DEFAULT_POLICY_PACK_ID`.
- Resolution context is header-only. Unsupported query parameters return `422` instead of being
  ignored or treated as aliases.
- The effective endpoint returns `enabled`, `selected_policy_pack_id`, and `source`.
- The catalog endpoint returns `enabled`, `total`, selected policy-pack id and source,
  `selected_policy_pack_present`, and sorted policy-pack definitions.
- Catalog storage is the governed PostgreSQL policy-pack repository; missing or unavailable storage
  returns `503`.

```mermaid
flowchart LR
    Caller[Gateway, operator, or certification probe] --> Effective[GET /api/v1/rebalance/policies/effective]
    Caller --> Catalog[GET /api/v1/rebalance/policies/catalog]
    Effective --> Precedence{Resolution precedence}
    Precedence --> Request[X-Policy-Pack-Id]
    Precedence --> Tenant[X-Tenant-Policy-Pack-Id or X-Tenant-Id resolver]
    Precedence --> Global[DPM_DEFAULT_POLICY_PACK_ID]
    Catalog --> Repo[(PostgreSQL policy-pack repository)]
    Repo --> Items[Sorted policy-pack definitions]
    Effective --> Selection[Selected policy-pack id and source]
    Catalog --> Selection
```

Non-functional posture:

- `/api/v1/rebalance/policies/effective` performs no repository read and is a low-latency configuration
  resolution endpoint.
- `/api/v1/rebalance/policies/catalog` performs a bounded local repository read, returns a deterministic
  sorted catalog, and performs no upstream calls to `lotus-core`, `lotus-advise`, Gateway, or
  Workbench.
- Header-only resolution avoids query-alias sprawl and keeps the direct source-service contract
  aligned with OpenAPI.
- The policy-pack read surface supports mandate execution governance without reintroducing advisory
  ownership into `lotus-manage`.

Upstream integration posture:

Policy-pack selection may be supplied by Gateway or tenant runtime context through headers.
`lotus-core` remains authoritative for portfolio and mandate source data, but it is not a source for
policy-pack catalog definitions in this endpoint family.

Downstream consumers:

- `lotus-gateway` is the strategic downstream integration boundary before any Workbench product
  surface consumes these controls.
- `lotus-workbench` should consume policy-pack posture through Gateway after integration, not by
  calling `lotus-manage` directly.
- No duplicate strategic source-service route was found in `lotus-manage`.

Client-demo and operations value:

These endpoints let business users and operations explain how a discretionary mandate execution is
governed before the run is submitted: which policy pack will apply, where it came from, and whether
the configured catalog contains the selected pack.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_effective_policy_pack_endpoint_resolution_precedence tests/unit/dpm/api/test_api_rebalance.py::test_policy_pack_supportability_routes_reject_unexpected_query_params tests/unit/dpm/api/test_api_rebalance.py::test_policy_pack_catalog_endpoint_returns_resolution_and_items tests/unit/dpm/api/test_dpm_policy_pack_config.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint family: policy-pack catalog administration

Routes:

- `GET /api/v1/rebalance/policies/catalog/{policy_pack_id}`
- `PUT /api/v1/rebalance/policies/catalog/{policy_pack_id}`
- `DELETE /api/v1/rebalance/policies/catalog/{policy_pack_id}`

Purpose:

Governed operator/admin control-plane access to individual discretionary mandate policy-pack
definitions. The read route supports exact policy inspection by id. Mutation routes are disabled by
default and must be enabled explicitly with `DPM_POLICY_PACK_ADMIN_APIS_ENABLED=true`.

Functional behavior:

- `GET` retrieves one policy-pack definition by id and returns `DPM_POLICY_PACK_NOT_FOUND` for
  missing identifiers.
- `PUT` creates or updates the policy-pack definition under the path identifier; the request body
  contains version and policy controls, not a competing identifier.
- `DELETE` removes one existing policy pack and returns `DPM_POLICY_PACK_NOT_FOUND` for missing
  identifiers.
- `PUT` and `DELETE` return `DPM_POLICY_PACK_ADMIN_APIS_DISABLED` when admin APIs are disabled.
- Query parameters are not accepted on any route in this family; stale aliases such as `dry_run`,
  `force`, or `include_disabled` return `422`.
- Policy payload coverage includes turnover, tax, settlement, constraint, workflow, and idempotency
  controls.

```mermaid
flowchart LR
    Operator[Governed operator or admin automation] --> Read[GET catalog/{policy_pack_id}]
    Operator --> Upsert[PUT catalog/{policy_pack_id}]
    Operator --> Delete[DELETE catalog/{policy_pack_id}]
    Upsert --> Flag{Admin APIs enabled?}
    Delete --> Flag
    Flag -->|false| Disabled[DPM_POLICY_PACK_ADMIN_APIS_DISABLED]
    Flag -->|true| Repo[(PostgreSQL policy-pack repository)]
    Read --> Repo
    Repo --> Definition[Policy-pack definition]
    Repo --> Missing[DPM_POLICY_PACK_NOT_FOUND]
```

Non-functional posture:

- All routes are local repository operations against the governed PostgreSQL policy-pack store and
  perform no upstream calls to `lotus-core`, `lotus-advise`, Gateway, or Workbench.
- The mutation surface is explicitly feature-flagged to keep normal runtime read-only unless
  policy governance operations are required.
- The path-only identity model avoids conflicting identifiers and keeps mutation semantics
  deterministic.
- The endpoints are mandate-governance controls; they are not advisory proposal lifecycle APIs.

Upstream and downstream posture:

- Policy-pack definitions are locally governed management controls. `lotus-core` remains
  authoritative for portfolio and mandate source data, not this policy catalog.
- `lotus-gateway` is the strategic downstream boundary for any future operator surface.
- No duplicate strategic source-service route was found in `lotus-manage`; downstream systems
  should not call these admin routes directly from Workbench.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_dpm_policy_pack_admin_api.py tests/unit/dpm/supportability/test_dpm_policy_pack_postgres_repository.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: run inventory

Route:

- `GET /api/v1/rebalance/runs`

Purpose:

Returns a bounded, filtered page of persisted discretionary mandate rebalance runs for operator,
audit, and supportability investigations. Use this endpoint when the caller needs a run inventory
or the latest runs for a portfolio. Use direct lookup routes when the caller already has a run id,
correlation id, idempotency key, or request hash.

Request surface:

- Filters: `created_from`, `created_to`, `status_filter`, `request_hash`, and `portfolio_id`.
- Pagination: `limit` and `cursor`.
- Ordering: `created_at` descending, then `rebalance_run_id` descending for deterministic ties.
- `next_cursor` is the last returned `rebalance_run_id`.
- Unsupported aliases such as `status`, `from`, or `to` return `422`.

Functional coverage:

- filtering by run status, request hash, portfolio id, and creation window,
- deterministic pagination across same-timestamp rows,
- invalid cursor behavior returns an empty page with no next cursor,
- retention cleanup excludes expired runs before listing,
- unsupported aliases are rejected instead of silently ignored.

Non-functional posture:

- The endpoint is a local supportability read and does not call upstream portfolio, market-data,
  advisory, or gateway services.
- SQLite and Postgres repositories push status predicates and cursor pagination into storage,
  reducing unnecessary in-process filtering and improving latency as run volume grows.
- Page size is bounded by the OpenAPI `limit` contract.

Upstream integration posture:

The endpoint reads persisted `lotus-manage` run records captured from execution requests. Source
portfolio, model, market, and policy authority remains with the original caller and future
`lotus-core` stateful resolution design.

Downstream consumers:

- `lotus-gateway` uses this endpoint with canonical `portfolio_id` and `limit` parameters for
  Workbench and foundation portfolio snapshots.
- No Workbench direct source-service consumer was found; Workbench should continue using Gateway.
- Stale proposal-listing methods still exist in Gateway legacy tests/client surface and are already
  tracked under `sgajbi/lotus-gateway#178`.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_support_runs_list_filters_and_cursor tests/unit/dpm/supportability/test_dpm_run_repository_backends.py::test_repository_list_runs_filter_and_cursor_contract tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py::test_postgres_repository_list_runs_filters_and_cursor tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint family: direct run lookup

Routes:

- `GET /api/v1/rebalance/runs/{rebalance_run_id}`
- `GET /api/v1/rebalance/runs/by-correlation/{correlation_id}`
- `GET /api/v1/rebalance/runs/by-request-hash/{request_hash}`
- `GET /api/v1/rebalance/runs/idempotency/{idempotency_key}`

Purpose:

Returns exact persisted supportability records for discretionary mandate rebalance runs when the
caller already has a specific investigation handle. These routes are intentionally narrow point
lookups. Use `/api/v1/rebalance/runs` for inventory search, `/api/v1/rebalance/runs/{run_id}/artifact` for the
deterministic audit artifact, and support-bundle routes when workflow, lineage, async operation, or
idempotency history context is required.

Functional behavior:

- Run-id, correlation-id, and request-hash routes return the same `DpmRunLookupResponse` shape:
  run id, correlation id, canonical request hash, optional idempotency key, portfolio id, creation
  timestamp, and full persisted rebalance result.
- The idempotency route returns the current key-to-run mapping with idempotency key, request hash,
  run id, and mapping timestamp.
- Missing run, correlation, and request-hash handles return `DPM_RUN_NOT_FOUND`.
- Missing idempotency keys return `DPM_IDEMPOTENCY_KEY_NOT_FOUND`.
- `DPM_SUPPORT_APIS_ENABLED=false` returns `DPM_SUPPORT_APIS_DISABLED` before storage lookup.
- All four routes reject unsupported query parameters with `422`; they do not silently ignore
  filters or include flags.

```mermaid
flowchart LR
    Operator[Operator, Gateway trace, or incident ticket] --> Handle{Available handle}
    Handle -->|run id| ByRun[GET /api/v1/rebalance/runs/{run_id}]
    Handle -->|correlation id| ByCorrelation[GET /api/v1/rebalance/runs/by-correlation/{correlation_id}]
    Handle -->|request hash| ByRequestHash[GET /api/v1/rebalance/runs/by-request-hash/{request_hash}]
    Handle -->|idempotency key| ByIdempotency[GET /api/v1/rebalance/runs/idempotency/{idempotency_key}]
    ByRun --> Store[(Supportability store)]
    ByCorrelation --> Store
    ByRequestHash --> Store
    ByIdempotency --> Store
    Store --> Result[Persisted run or current idempotency mapping]
    Result --> Bundle[Use support-bundle only when broader evidence is needed]
```

Non-functional posture:

- The routes are local supportability reads over the configured repository backend and perform no
  upstream calls to `lotus-core`, `lotus-advise`, market-data services, Gateway, or Workbench.
- Lookup by run id and idempotency key are primary-key style reads in the persistence layer.
- Correlation-id and request-hash lookups resolve the latest mapped run and should remain indexed in
  persistent backends as data volume grows.
- The API surface is low-latency and deterministic; callers should avoid polling these endpoints for
  inventory workflows and use the bounded list endpoint instead.

Upstream integration posture:

These lookup routes expose records captured by `lotus-manage` during execution. The original
portfolio, model, market, and policy inputs remain governed by the request contract and future
`lotus-core` stateful resolution path. The direct lookup family does not create new upstream source
authority.

Downstream consumers:

- `lotus-gateway` can use these routes for source-service supportability and incident resolution
  when it has a run id, correlation id, request hash, or idempotency key.
- Workbench should not call these source-service routes directly; any product surface should remain
  Gateway-mediated.
- No duplicate strategic route was found in `lotus-manage`. Support bundles are complementary, not
  replacements, because they intentionally return a broader investigation payload.

Client-demo and operations value:

- Business and operations users can explain these endpoints as the traceability layer behind a
  discretionary mandate action: every submitted run can be recovered by the operational handle a
  banker, support analyst, or platform trace is likely to have.
- Sales and client-facing demos should position this as auditability and operational resilience,
  not as advisory proposal management. Advisory proposal lifecycle remains owned by `lotus-advise`.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_support_apis_lookup_by_run_correlation_and_idempotency tests/unit/dpm/api/test_api_rebalance.py::test_dpm_support_apis_not_found_and_disabled tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: supportability summary

Route:

- `GET /api/v1/rebalance/supportability/summary`

Purpose:

Returns a store-wide supportability and readiness snapshot for discretionary mandate operations
without requiring direct database access. Use this endpoint for operational health checks, Gateway
portfolio workspace supportability posture, and Workbench readiness surfaces. Use run inventory or
direct lookup endpoints when row-level run details are required.

Request surface:

- No query options.
- Unsupported query parameters return `422`.
- Feature gates: `DPM_SUPPORT_APIS_ENABLED` and `DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED`.

Functional coverage:

- run and async-operation totals,
- run and operation status distributions,
- workflow decision totals plus action and reason-code distributions,
- lineage edge totals,
- oldest and newest run/operation timestamps,
- bounded `supportability` state, reason, freshness bucket, and supporting counts,
- metrics emission through bounded action-register labels,
- disabled feature gates and unsupported query parameters.
- backend initialization failures return `503` with bounded supportability-store error codes.

Non-functional posture:

- The endpoint is a local supportability read and does not call upstream portfolio, market-data,
  advisory, or gateway services.
- SQLite and Postgres repositories aggregate run status counts in storage instead of loading every
  run result payload into application memory.
- The response is bounded by aggregate counts and timestamps rather than row-level payloads.

Upstream integration posture:

The endpoint summarizes persisted `lotus-manage` records captured from execution, async-operation,
workflow, and lineage flows. It does not resolve fresh source state from `lotus-core`; source
authority remains with the original execution request and future stateful source-data design.

Downstream consumers:

- `lotus-gateway` reads this endpoint for portfolio workspace supportability posture.
- `lotus-workbench` receives supportability posture through Gateway portfolio contracts, not direct
  source-service calls.
- No stale downstream source-service consumer was found for this endpoint.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_supportability_summary_endpoint tests/unit/dpm/api/test_api_rebalance.py::test_dpm_supportability_summary_backend_init_error_returns_503 tests/unit/dpm/api/test_api_rebalance.py::test_dpm_supportability_summary_rejects_unexpected_query_params tests/unit/dpm/supportability/test_dpm_run_repository_backends.py::test_repository_supportability_summary_contract tests/unit/dpm/supportability/test_dpm_postgres_repository_scaffold.py::test_postgres_repository_supportability_summary tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: deterministic run artifact

Route:

- `GET /api/v1/rebalance/runs/{rebalance_run_id}/artifact`

Purpose:

Returns only the deterministic artifact for a discretionary mandate rebalance run. Use this endpoint
when an operator, auditor, replay job, or incident-support tool needs the replayable artifact
payload and hash evidence. Use the support-bundle endpoint instead when workflow history, lineage,
async operation, or idempotency context is also required.

Request surface:

- Path parameter: `rebalance_run_id`.
- No query options.
- Unsupported query parameters return `422`.
- Feature gates: `DPM_SUPPORT_APIS_ENABLED` and `DPM_ARTIFACTS_ENABLED`.
- Artifact modes: `DERIVED` and `PERSISTED`.

Functional coverage:

- returned artifact identity, run id, correlation id, idempotency key, portfolio id, status,
  request snapshot, before/after summaries, order intents, rule outcomes, diagnostics, full result,
  and evidence fields are tied to the persisted run,
- `artifact_hash` is recomputed from the canonical response payload with the hash field excluded,
- repeated retrieval returns the same deterministic hash,
- persisted mode stores artifacts and backfills missing persisted artifacts from run data,
- missing run ids and disabled artifact APIs return governed `404` details,
- unsupported query parameters are rejected instead of silently ignored.

Non-functional posture:

- The endpoint performs local deterministic artifact resolution only.
- `DERIVED` mode avoids a separate artifact read and is stateless beyond persisted run data.
- `PERSISTED` mode supports durable storage while retaining deterministic backfill behavior for
  older runs without stored artifacts.
- The route has no outbound source-data calls and no advisory proposal artifact responsibility.

Upstream integration posture:

The artifact is generated from persisted `lotus-manage` run output. The original run payload carries
caller-supplied portfolio, model, market, and policy context; future stateful `portfolio_id` source
resolution remains governed by the `lotus-core` integration design.

Downstream consumers:

- No direct strategic Gateway or Workbench consumer was found for this source-service artifact
  route.
- `lotus-advise` owns advisory proposal artifacts; this endpoint must remain limited to
  discretionary mandate run artifacts.
- Future audit or replay consumers should use this route for artifact-only reads and the
  support-bundle route for broader investigation context.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_support_apis_lookup_by_run_correlation_and_idempotency tests/unit/dpm/api/test_api_rebalance.py::test_dpm_support_apis_not_found_and_disabled tests/unit/dpm/supportability/test_dpm_run_support_service_coverage.py::test_service_persisted_artifact_mode_stores_and_reads_artifact tests/unit/dpm/supportability/test_dpm_run_support_service_coverage.py::test_service_persisted_artifact_mode_backfills_missing_persisted_artifact tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: run supportability bundle

Routes:

- `GET /api/v1/rebalance/runs/{rebalance_run_id}/support-bundle`
- `GET /api/v1/rebalance/runs/by-correlation/{correlation_id}/support-bundle`
- `GET /api/v1/rebalance/runs/idempotency/{idempotency_key}/support-bundle`
- `GET /api/v1/rebalance/runs/by-operation/{operation_id}/support-bundle`

Purpose:

Returns one aggregated supportability bundle for a discretionary mandate rebalance run so operator
or audit investigations can start from a single payload. Use this endpoint when the caller already
has the run id. Use the by-correlation, by-idempotency, or by-operation variants when the caller has
only one of those alternate handles.

Request surface:

- Path parameter: `rebalance_run_id`.
- Optional include flags: `include_artifact`, `include_async_operation`,
  `include_idempotency_history`.
- Always included: `run`, `workflow_history`, and `lineage`.
- Optional: `artifact`, `async_operation`, and `idempotency_history`.
- Unsupported query parameters return `422`.

Functional coverage:

- full bundle includes run payload, deterministic artifact, async operation, workflow history,
  lineage, and idempotency history when each backing record exists,
- compact bundle excludes optional artifact, async operation, and idempotency history while
  retaining core workflow and lineage context,
- by-correlation, by-idempotency, and by-operation variants resolve to the same run bundle,
- missing run, idempotency key, or operation ids return governed `404` details,
- disabled support-bundle feature gate returns governed `404`,
- unsupported query parameters are rejected instead of silently ignored.

Non-functional posture:

- The route performs local supportability aggregation only; it does not call upstream portfolio,
  market-data, advisory, or gateway services.
- Optional include flags let callers reduce payload size and latency when artifact, async detail,
  or idempotency history are not needed.
- `workflow_history` and `lineage` remain always included because they are core audit context for
  run reconstruction.

Upstream integration posture:

The endpoint reports persisted `lotus-manage` supportability records captured during simulation and
async operation handling. Upstream systems remain responsible for source-governed portfolio, model,
market, and policy identifiers in the original run payload.

Downstream consumers:

- Integration and e2e tests use support-bundle variants for supportability proof.
- No direct strategic Gateway or Workbench consumer was found for source-service support-bundle
  routes.
- Future incident tooling should use this endpoint instead of adding duplicate bundle or lineage
  joins downstream.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_run_support_bundle_endpoint tests/unit/dpm/api/test_api_rebalance.py::test_dpm_run_support_bundle_endpoint_by_correlation_and_idempotency tests/unit/dpm/api/test_api_rebalance.py::test_dpm_run_support_bundle_endpoint_by_operation tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: supportability lineage lookup

Route:

- `GET /api/v1/rebalance/lineage/{entity_id}`

Purpose:

Returns persisted supportability lineage edges where `entity_id` is either the source or target of a
relation. Use this endpoint for incident reconstruction, audit evidence, run-to-correlation
traversal, idempotency retry analysis, and async operation traceability.

Request surface:

- Path parameter: `entity_id`.
- Filters: `edge_type`, `created_from`, `created_to`.
- Pagination: `limit` and opaque `cursor`.
- Valid edge types: `CORRELATION_TO_RUN`, `IDEMPOTENCY_TO_RUN`,
  `OPERATION_TO_CORRELATION`.
- Response: `DpmLineageResponse`.
- Unknown entity ids return an empty lineage page rather than `404`.

Functional coverage:

- run-id lookup returns both correlation-to-run and idempotency-to-run edges,
- correlation, idempotency, run, and operation entity ids are supported by the repository lookup,
- edge-type filtering validates against the governed enum,
- created-at windows can produce an empty bounded page,
- cursor pagination is deterministic,
- unsupported query aliases return `422`,
- invalid edge types return `422`,
- metadata preserves request hashes for run and idempotency lineage edges.

Non-functional posture:

- Results are ordered by `created_at`, `source_entity_id`, `edge_type`, and `target_entity_id` for
  deterministic audit review.
- The endpoint is page-bounded with a maximum `limit` of 200.
- Lineage lookup is a local supportability read and never calls upstream portfolio, market-data, or
  advisory systems.

Upstream integration posture:

The endpoint reports lineage captured during `lotus-manage` supportability writes. Upstream systems
remain responsible for source-governed portfolio, model, market, and policy identifiers passed into
the original request.

Downstream consumers:

- Integration tests use lineage lookup for supportability round trips.
- No direct strategic Gateway or Workbench consumer was found for `/api/v1/rebalance/lineage/{entity_id}`.
- Future downstream incident tooling should use this endpoint for DPM supportability graph
  traversal rather than adding duplicate lineage routes.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_dpm_lineage_filters.py tests/unit/dpm/api/test_api_rebalance.py::test_dpm_lineage_api_disabled_and_enabled tests/unit/dpm/api/test_api_rebalance.py::test_lineage_supportability_route_rejects_unexpected_query_params tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: idempotency history lookup

Route:

- `GET /api/v1/rebalance/idempotency/{idempotency_key}/history`

Purpose:

Returns append-only idempotency mapping history for one idempotency key, including run ids,
correlation ids, request hashes, and event timestamps. Use this endpoint for retry-history
investigations, idempotency conflict reconstruction, and audit evidence when replay-disabled runs
share an idempotency key. Use `GET /api/v1/rebalance/runs/idempotency/{idempotency_key}` when only the
latest mapping is needed.

Request surface:

- Path parameter: `idempotency_key`.
- Query parameters: none.
- Response: `DpmRunIdempotencyHistoryResponse`.
- Feature gate: `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`.

Functional coverage:

- disabled history API returns governed `404`,
- enabled history API returns append-only events for repeated idempotency keys,
- event payloads include `rebalance_run_id`, `correlation_id`, `request_hash`, and `created_at`,
- events are ordered by `created_at`, `rebalance_run_id`, `correlation_id`, and `request_hash`,
- missing keys return `404` with `DPM_IDEMPOTENCY_KEY_NOT_FOUND`,
- unsupported query parameters return `422`.

Non-functional posture:

- The endpoint is a bounded supportability read for one idempotency key and does not accept ad hoc
  filters.
- The route reads persisted local supportability state only and does not call upstream services.
- Keeping the history endpoint feature-gated by default avoids exposing retry internals unless an
  operator or certification workflow explicitly enables it.

Upstream integration posture:

The endpoint reports idempotency events captured when `lotus-manage` records simulation runs. It
does not source or mutate upstream portfolio, market, model, or policy data.

Downstream consumers:

- Demo and integration tests use this endpoint for supportability proof when the feature gate is
  enabled.
- No direct strategic Gateway or Workbench consumer was found for the idempotency history route.
- Future incident tooling should use this route rather than scraping run lists for retry history.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_idempotency_history_api_disabled_enabled_and_history_payload tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts tests/unit/test_local_docker_runtime_contract.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint family: workflow review supportability

Routes:

- `GET /api/v1/rebalance/runs/{rebalance_run_id}/workflow`
- `GET /api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow`
- `GET /api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow`
- `POST /api/v1/rebalance/runs/{rebalance_run_id}/workflow/actions`
- `POST /api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow/actions`
- `POST /api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow/actions`
- `GET /api/v1/rebalance/runs/{rebalance_run_id}/workflow/history`
- `GET /api/v1/rebalance/runs/by-correlation/{correlation_id}/workflow/history`
- `GET /api/v1/rebalance/runs/idempotency/{idempotency_key}/workflow/history`
- `GET /api/v1/rebalance/workflow/decisions`
- `GET /api/v1/rebalance/workflow/decisions/by-correlation/{correlation_id}`

Purpose:

Provides the discretionary mandate review-control layer for rebalance runs that require human
review before execution. Workflow supportability is deliberately management-side: it captures
review posture, reviewer actions, reason codes, comments, actors, decision timestamps, and action
correlation ids. It is not an advisory proposal lifecycle and must not be used for advisor-led
client recommendation consent flows; those remain in `lotus-advise`.

Functional behavior:

- Workflow state routes return current run status, workflow status, review-required flag, and latest
  decision when present.
- Workflow action routes accept only `APPROVE`, `REJECT`, or `REQUEST_CHANGES` plus uppercase
  `reason_code`, optional `comment`, required `actor_id`, and optional `X-Correlation-Id`.
- Workflow history routes return append-only decisions in chronological order for the resolved run.
- The global decision list supports bounded search by `rebalance_run_id`, `action`, `actor_id`,
  `reason_code`, `decided_from`, `decided_to`, `limit`, and `cursor`.
- Missing run handles return `DPM_RUN_NOT_FOUND`; missing idempotency handles return
  `DPM_IDEMPOTENCY_KEY_NOT_FOUND`.
- Disabled workflow APIs return `DPM_WORKFLOW_DISABLED`.
- Invalid transitions return `409` with governed workflow transition details.
- Point lookup, history, and action routes reject unsupported query parameters with `422`.

```mermaid
flowchart TD
    Run[Rebalance run] --> Gate{Run status requires review?}
    Gate -->|No| Ready[No workflow action allowed]
    Gate -->|Yes| Pending[PENDING_REVIEW]
    Pending --> RequestChanges[REQUEST_CHANGES]
    RequestChanges --> Pending
    Pending --> Approve[APPROVE]
    Pending --> Reject[REJECT]
    Approve --> Approved[APPROVED]
    Reject --> Rejected[REJECTED]
    Pending --> History[(Append-only workflow decisions)]
    RequestChanges --> History
    Approve --> History
    Reject --> History
    History --> List[GET /api/v1/rebalance/workflow/decisions]
```

Non-functional posture:

- Workflow routes are local supportability reads or writes over the configured repository backend.
- State and history reads do not call upstream `lotus-core`, `lotus-advise`, Gateway, Workbench, or
  market-data services.
- Workflow decision list is page-bounded with a maximum `limit` of 200 and uses explicit canonical
  filters.
- The state/action/history routes are low-latency point operations keyed by run id, correlation id,
  or idempotency key.
- The feature gate keeps review-control internals disabled unless the management workflow is
  intentionally enabled for the runtime.

Upstream integration posture:

Workflow decisions are derived from `lotus-manage` run status and local reviewer actions. They do
not source new portfolio data. The original execution run still carries caller-supplied portfolio,
model, market, and policy context; future stateful source resolution remains governed by the
`lotus-core` integration design.

Downstream consumers:

- `lotus-gateway` is the strategic downstream boundary if workflow posture becomes product-facing.
- Workbench should consume workflow posture through Gateway only, not direct source-service calls.
- No duplicate strategic route was found in `lotus-manage`; workflow history and global decision
  list are complementary because one is run-scoped and the other is filter/search oriented.

Client-demo and operations value:

- Business users can describe this as discretionary mandate control evidence: the platform can show
  which rebalance runs required review, who acted, why, when, and under which trace id.
- Operations can use it to reconstruct review events without database access.
- Sales and client-pitch material should position this as governance and auditability for managed
  portfolio operations, not as an advisory recommendation workflow.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_run_workflow_endpoints_happy_path_and_invalid_transition tests/unit/dpm/api/test_api_rebalance.py::test_dpm_workflow_decision_list_endpoint_filters_and_cursor tests/unit/dpm/api/test_api_rebalance.py::test_dpm_run_workflow_endpoints_disabled_and_not_required_behavior tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: single rebalance simulation

Route:

- `POST /api/v1/rebalance/simulate`

Purpose:

Runs one deterministic discretionary mandate portfolio rebalance from an explicit execution
envelope. `input_mode=stateless` uses a complete inline request bundle. `input_mode=stateful`
is modeled for governed `lotus-core` source-data resolution, but remains feature-gated until live
core-backed proof is complete. This is the core manage-owned execution endpoint for portfolio
management, policy-pack application, run supportability, lineage, idempotency, and workflow-gate
outcome publication. It is not an advisory proposal endpoint and must not be used as a canonical
portfolio read API.

Request surface:

- Body: `input_mode`
- For `input_mode=stateless`: `stateless_input.portfolio_snapshot`,
  `stateless_input.market_data_snapshot`, `stateless_input.model_portfolio`,
  `stateless_input.shelf_entries`, `stateless_input.options`
- For `input_mode=stateful`: `stateful_input.portfolio_id`, `stateful_input.as_of`,
  optional mandate/model/policy/tenant/booking-center selectors, and optional `options_override`
- Required header: `Idempotency-Key`
- Optional headers: `X-Correlation-Id`, `X-Policy-Pack-Id`, `X-Tenant-Policy-Pack-Id`,
  `X-Tenant-Id`

Functional coverage:

- success response with all audit families: before state, universe, target trace, intents,
  after-state, reconciliation, tax impact, rule results, explanation, diagnostics, gate decision,
  and lineage,
- missing idempotency header validation,
- invalid payload validation,
- idempotent replay and hash-conflict behavior,
- optional replay disablement,
- generated correlation id when caller omits `X-Correlation-Id`,
- policy-pack request override,
- explicit tenant policy-pack override,
- tenant resolver fallback,
- blocked and pending-review domain statuses,
- settlement, tax, turnover, group-constraint, and missing-price control branches,
- supportability persistence, artifact, workflow, lineage, idempotency, and summary integration,
- stateful mode feature gate returning `DPM_STATEFUL_INPUT_DISABLED` by default,
- stateful mode returning `DPM_CORE_RESOLVER_UNAVAILABLE` when enabled without core resolver
  configuration,
- mocked stateful simulate proof that resolved core source lineage is emitted on the result,
- core resolver transformation and source-safe resolver failure behavior covered by unit tests.

Non-functional posture:

- Synchronous execution is intended for one bounded simulation request.
- Idempotency protects client retries and prevents same-key/different-request ambiguity.
- The endpoint records supportability state when persistence is enabled; replay-enabled persistence
  failures return service-unavailable responses rather than falsely accepting a run.
- For multi-scenario or deferred execution, use `/api/v1/rebalance/analyze` or `/api/v1/rebalance/analyze/async`.

Upstream integration posture:

The route accepts inline snapshots for stateless mode. For stateful mode, `lotus-manage` now has a
bounded `lotus-core` resolver client and source-context transformation seam over the RFC-087 DPM
source products. The route is disabled by default with `DPM_STATEFUL_CORE_SOURCING_ENABLED=false`.
Upstream portfolio, price, FX, tax-lot, model, mandate, and instrument-source authority remains
outside `lotus-manage`; callers must provide source-governed snapshots in stateless mode, and
stateful mode must use certified `lotus-core` source-data products before being advertised.

Stateful promotion status:

- unblocked at service level by RFC-087 live proof: model targets, mandate binding, eligibility,
  portfolio tax lots, market-data/FX coverage, and source readiness returned READY evidence for
  `PB_SG_GLOBAL_BAL_001`,
- the retired monolithic DPM execution-context route remains absent by design, and
  `lotus-manage` composes product-specific core routes instead,
- integration capabilities do not advertise `stateful` unless the stateful capability flag,
  `DPM_STATEFUL_CORE_SOURCING_ENABLED`, and `DPM_CORE_BASE_URL` are all configured.

Downstream consumers:

- No strategic Gateway or Workbench consumer should call this endpoint as an advisory proposal
  surface.
- Current stale Gateway proposal routing and Workbench proposal documentation are tracked under
  `sgajbi/lotus-gateway#178` and `sgajbi/lotus-workbench#135` for migration away from removed
  manage proposal endpoints and toward strategic advisory or DPM run/operation/workflow contracts
  where needed.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
python -m pytest tests/unit/dpm/api/test_integration_capabilities_api.py tests/unit/dpm/api/test_api_rebalance.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: synchronous what-if analysis

Route:

- `POST /api/v1/rebalance/analyze`

Purpose:

Runs a bounded set of named discretionary mandate what-if scenarios from an explicit execution
envelope and returns the full batch result synchronously. `input_mode=stateless` uses shared inline
snapshots. `input_mode=stateful` is modeled for shared `lotus-core` context plus scenario overrides,
but remains disabled by default until live core-backed proof is complete. Use this endpoint when the
caller needs immediate scenario comparison. Use `/api/v1/rebalance/analyze/async` for polling-based
orchestration or accept-now/execute-later flows.

Request surface:

- Body: `input_mode`
- For `input_mode=stateless`: `stateless_input` with shared `portfolio_snapshot`,
  `market_data_snapshot`, `model_portfolio`, `shelf_entries`, plus a named `scenarios` map.
- For `input_mode=stateful`: `stateful_input` selectors plus a top-level named `scenarios` map.
- Optional headers: `X-Correlation-Id`, `X-Policy-Pack-Id`, `X-Tenant-Policy-Pack-Id`,
  `X-Tenant-Id`.
- Scenario names must match `[a-z0-9_\-]{1,64}`.
- Maximum scenario count is 20.

Functional coverage:

- successful multi-scenario batch with deterministic scenario-key ordering,
- explicit and fallback snapshot identifiers,
- explicit and generated scenario correlation ids,
- request-level and tenant-default policy-pack resolution,
- invalid scenario option isolation,
- runtime failure isolation,
- partial-failure warning publication,
- maximum scenario boundary,
- comparison metrics keyed only to successful scenarios,
- gross turnover metric reconciliation to returned `SECURITY_TRADE` intents,
- mixed `READY`, `PENDING_REVIEW`, and `BLOCKED` scenario outcomes.

Non-functional posture:

- Synchronous analysis is bounded by the 20-scenario request limit.
- Scenarios execute in deterministic sorted-key order for reproducible supportability and tests.
- One scenario failure does not discard successful scenario evidence.
- For latency-sensitive or deferred batches, callers should use `/api/v1/rebalance/analyze/async`.

Upstream integration posture:

The endpoint accepts inline source-governed snapshots in stateless mode. Stateful mode is wired to
the resolver seam but feature-gated until certified `lotus-core` source-data products and live proof
exist. Upstream data authority remains outside `lotus-manage`; lineage and snapshot identifiers must
be preserved by callers or carried from the resolved core context. Policy-pack resolution is local to
`lotus-manage`.

Downstream consumers:

- No direct strategic Gateway or Workbench consumer was found for `/api/v1/rebalance/analyze`.
- Future Gateway/Workbench mandate-analysis integration should capability-gate this endpoint and
  preserve scenario names, correlation ids, and policy-pack context.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: async what-if analysis submission

Route:

- `POST /api/v1/rebalance/analyze/async`

Purpose:

Accepts the same named discretionary mandate scenario batch as synchronous analysis, but returns an
operation handle for polling or accept-now/execute-later orchestration. Use this endpoint when the
caller needs deferred execution, operation-level supportability, or explicit manual execution in
`DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`.

Request surface:

- Body: explicit batch execution envelope. `input_mode=stateless` carries `stateless_input`
  containing the `BatchRebalanceRequest`; `input_mode=stateful` carries `stateful_input` selectors
  plus top-level `scenarios` and remains disabled by default until live core-backed proof exists.
- Optional headers: `X-Correlation-Id`, `X-Policy-Pack-Id`, `X-Tenant-Policy-Pack-Id`,
  `X-Tenant-Id`.
- Response: `DpmAsyncAcceptedResponse` with `operation_id`, initial `status`, `correlation_id`,
  `status_url`, and `execute_url`.
- Retrieval: `GET /api/v1/rebalance/operations/{operation_id}` or
  `GET /api/v1/rebalance/operations/by-correlation/{correlation_id}`.

Functional coverage:

- inline execution accepts and then persists terminal `SUCCEEDED` operation state,
- accept-only mode keeps operation `PENDING` and executable,
- manual execution transitions pending operation to terminal status,
- duplicate correlation ids return `409` with `DPM_ASYNC_OPERATION_CORRELATION_CONFLICT`,
- generated correlation ids are echoed in the response body and `X-Correlation-Id` response header,
- operation failures are captured as `FAILED` status with structured error details,
- async disabled/manual-execution disabled modes return governed `404` responses,
- invalid execution mode falls back to inline execution,
- request and tenant-default policy-pack context is persisted and applied during manual execution,
- accepted Swagger example validates against `DpmAsyncAcceptedResponse`.

Non-functional posture:

- The accepted response is deliberately small and stable for low-latency submission.
- Terminal results are retrieved through operation status endpoints rather than overloading the
  submission response.
- Correlation ids are unique operation handles to prevent ambiguous supportability lookups.
- Accept-only mode enables external orchestration without losing policy context.

Upstream integration posture:

The endpoint persists caller-supplied inline snapshots and policy context for later execution in
stateless mode. Stateful mode stores resolved source-context lineage with the async operation when
enabled, but remains feature-gated until `lotus-core` proof exists. Snapshot authority and lineage
remain with upstream callers and `lotus-core`-governed data products.

Downstream consumers:

- No direct strategic Gateway or Workbench consumer was found for `/api/v1/rebalance/analyze/async`.
- Future downstream integration should treat this endpoint as the strategic deferred DPM analysis
  submission route, not as an advisory proposal lifecycle route.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: async operation manual execution

Route:

- `POST /api/v1/rebalance/operations/{operation_id}/execute`

Purpose:

Executes one pending asynchronous DPM scenario-analysis operation that was accepted through
`POST /api/v1/rebalance/analyze/async` in `DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`. Use this endpoint for
external orchestration flows that intentionally separate operation acceptance from execution.

Request surface:

- Path: `operation_id`.
- Body: none.
- Response: `DpmAsyncOperationStatusResponse`.
- Terminal `SUCCEEDED` responses include the `BatchRebalanceResult` payload in `result`.
- Terminal `FAILED` responses include structured `error` details and leave `result=null`.

Functional coverage:

- pending accept-only operations execute successfully and become non-executable,
- execution failures are captured as terminal `FAILED` operation status,
- failed operations cannot be re-executed and return `409`,
- missing operations return `404`,
- already terminal inline-executed operations return `409`,
- disabled manual execution returns governed `404`,
- request and tenant-default policy-pack context persists from async submission and is applied at
  manual execution time,
- Swagger documents body-less execution, terminal success/failure status behavior, and 404/409
  error surfaces.

Non-functional posture:

- The endpoint is deliberately body-less so execution is bound to the persisted, audited operation
  request and policy context.
- Terminal operation lookup remains stable through `GET /api/v1/rebalance/operations/{operation_id}`;
  repeated execute calls are rejected instead of replaying the calculation.
- Manual execution supports low-latency acceptance while allowing an external orchestrator to start
  compute work under its own scheduling controls.

Upstream integration posture:

Manual execution uses the snapshots and policy context persisted at async submission time. It does
not fetch additional upstream portfolio or market data at execution time, which keeps the operation
auditable and reproducible.

Downstream consumers:

- No direct strategic Gateway or Workbench consumer was found for the manual execute route.
- Future consumers should call this endpoint only for `ACCEPT_ONLY` deferred DPM analysis workflows.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: async operation list

Route:

- `GET /api/v1/rebalance/operations`

Purpose:

Returns a bounded page of asynchronous DPM operation records for supportability, operator triage,
polling dashboards, and recent-operation review after async analysis submission. Use this endpoint
for list/filter views. Use `GET /api/v1/rebalance/operations/{operation_id}` when the caller already has a
single operation handle.

Request surface:

- Query filters: `created_from`, `created_to`, `operation_type`, `status_filter`,
  `correlation_id`.
- Pagination: `limit` and opaque `cursor` from the prior response's `next_cursor`.
- Unsupported aliases such as `status` are rejected.

Functional coverage:

- status filtering with canonical `status_filter`,
- unsupported query-parameter rejection,
- operation type filtering,
- created-at window filtering,
- correlation-id filtering,
- cursor pagination,
- executable flag derivation for pending operations with stored request payloads.

Non-functional posture:

- The endpoint is page-bounded by `limit` with a maximum of 200 rows.
- Results are ordered by newest `created_at`, then operation id descending for deterministic
  supportability review.
- The list item shape excludes raw request payloads and terminal result bodies; callers retrieve
  a specific operation for terminal detail.

Upstream integration posture:

The endpoint reads persisted `lotus-manage` operation state only. It does not call upstream data
providers. Upstream lineage remains available through operation result payloads and supportability
bundle endpoints.

Downstream consumers:

- No direct strategic Gateway or Workbench consumer was found for `/api/v1/rebalance/operations`.
- Future dashboards should use this list route for bounded operation summaries and then call the
  by-id operation endpoint for terminal result/error detail.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_async_operation_list_filters_and_cursor tests/unit/dpm/api/test_api_rebalance.py::test_dpm_async_operation_list_filters_by_created_window_and_operation_type tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: async operation detail by id

Route:

- `GET /api/v1/rebalance/operations/{operation_id}`

Purpose:

Returns one asynchronous operation status record when the caller has the exact operation handle.
Use this endpoint for polling a submitted async analysis operation, inspecting terminal result/error
payloads, or checking manual-execution eligibility. Use
`GET /api/v1/rebalance/operations/by-correlation/{correlation_id}` when only a correlation id is available.

Request surface:

- Path parameter: `operation_id`.
- Response: `DpmAsyncOperationStatusResponse`.
- Terminal success: `result` contains a `BatchRebalanceResult`.
- Terminal failure: `error` contains structured `code` and `message`.
- Missing operation or disabled async operations return `404`.

Functional coverage:

- pending operation lookup by id,
- successful terminal operation lookup with typed `BatchRebalanceResult` payload,
- failed terminal operation lookup with structured error payload,
- missing operation `404`,
- async-disabled `404`,
- by-correlation parity for the same operation record.

Non-functional posture:

- The endpoint returns a single bounded operation record without exposing persisted raw request
  payloads.
- `is_executable` is derived from operation status and stored request availability, avoiding caller
  inference from status alone.
- The route reads local persisted operation state and does not call upstream services.

Upstream integration posture:

The endpoint is a supportability read over `lotus-manage` async operation state. Upstream snapshot
and lineage truth remains in the operation result payload and supportability bundle routes.

Downstream consumers:

- Integration and e2e tests use this endpoint after async submission.
- No direct strategic Gateway or Workbench consumer was found for by-id operation detail.
- Future downstream polling should use this endpoint when it already has `operation_id`.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_async_operation_lookup_by_id_and_correlation tests/unit/dpm/api/test_api_rebalance.py::test_dpm_async_operation_lookup_by_id_returns_typed_terminal_result tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: async operation detail by correlation id

Route:

- `GET /api/v1/rebalance/operations/by-correlation/{correlation_id}`

Purpose:

Returns one asynchronous operation status record when the caller has the submitted correlation id but
not the generated operation id. Use this endpoint for polling after submitting `X-Correlation-Id` to
`POST /api/v1/rebalance/analyze/async`, or for supportability lookup from external logs keyed by
correlation id.

Request surface:

- Path parameter: `correlation_id`.
- Response: `DpmAsyncOperationStatusResponse`.
- Terminal success: `result` contains a `BatchRebalanceResult`.
- Terminal failure: `error` contains structured `code` and `message`.
- Missing correlation id or disabled async operations return `404`.

Functional coverage:

- pending operation lookup by correlation id,
- successful terminal operation lookup with typed `BatchRebalanceResult` payload,
- same operation identity as by-id lookup,
- missing correlation id `404`,
- async-disabled `404`.

Non-functional posture:

- Correlation ids are unique operation handles for async operations.
- The endpoint returns a single bounded operation record without exposing persisted raw request
  payloads.
- The route reads local persisted operation state and does not call upstream services.

Upstream integration posture:

The endpoint is a supportability read over `lotus-manage` async operation state. It depends on the
correlation id captured at submission time and does not query upstream services.

Downstream consumers:

- Integration and e2e tests use this endpoint after async submission.
- No direct strategic Gateway or Workbench consumer was found for by-correlation operation detail.
- Future downstream polling should use this endpoint when the caller owns the correlation id but not
  the operation id.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py::test_dpm_async_operation_lookup_by_id_and_correlation tests/unit/dpm/api/test_api_rebalance.py::test_dpm_async_operation_lookup_by_correlation_returns_typed_terminal_result tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py::test_rebalance_async_and_supportability_endpoints_use_expected_request_response_contracts -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: proof-pack generation

Route:

- `POST /api/v1/rebalance/proof-packs`

Purpose:

Generates and persists an immutable RFC-0040 pre-trade proof pack from either a persisted rebalance
run or a selected RFC-0039 construction alternative. The endpoint is the manage-owned proof-pack
authority and records degraded or blocked section states when required source evidence is not yet
available.

Request surface:

- Header: `Idempotency-Key` is required for replay-safe generation.
- Optional header: `X-Correlation-Id`.
- Body: `DpmProofPackGenerateRequest`.
- Response: `DpmProofPackGenerateResponse`.
- Missing source fields return `422`.
- Missing source records return `404`.
- identity or idempotency conflicts return `409`.

Functional coverage:

- direct rebalance-run proof-pack generation,
- idempotent replay with stable content hash,
- selected-alternative source validation,
- persisted proof-pack lookup after generation,
- optional Markdown/report/AI link generation in the response,
- source-backed mandate-context attachment from the persisted RFC-0038 mandate digital twin and
  latest mandate-health snapshot when available,
- truthful mandate-context degradation when a caller supplies only a mandate id without persisted
  mandate evidence,
- portfolio-mismatched mandate evidence is rejected and exposed as
  `DPM_MANDATE_TWIN_PORTFOLIO_MISMATCH` rather than attached to the proof pack.

Non-functional posture:

- Proof-pack content is hashed and persisted immutably.
- `mandate_context` cannot be promoted to `READY` solely from caller-supplied identity; proof-pack
  source hashes must carry mandate twin and mandate-health evidence for ready mandate-context
  posture.
- The route does not reconstruct source facts from downstream report, AI, Gateway, or Workbench
  layers.
- Report-input and AI-evidence refs are deterministic manage-owned handoff records when requested.
  `lotus-report` materialization and `lotus-ai` PM memo generation remain downstream-owned and are
  not inferred from these refs.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_proof_pack_api.py -q
python -m pytest tests/unit/dpm/proof_packs/test_proof_pack_builder.py::test_mandate_context_degrades_when_only_identifier_is_available -q
python -m pytest tests/unit/test_rfc0040_evidence_script.py tests/unit/dpm/proof_packs/test_proof_pack_service.py -q
python scripts/generate_rfc0040_proof_pack_evidence.py --base-url http://127.0.0.1:8024
python scripts/openapi_quality_gate.py
```

## Certified endpoint family: rebalance wave preview, creation, source-check, simulation, selection, approval, staging, handoff, and supportability

Routes:

- `POST /api/v1/rebalance/waves/preview`
- `POST /api/v1/rebalance/waves`
- `POST /api/v1/rebalance/waves/{wave_id}/source-check`
- `POST /api/v1/rebalance/waves/{wave_id}/simulate`
- `POST /api/v1/rebalance/waves/{wave_id}/items/{wave_item_id}/select`
- `POST /api/v1/rebalance/waves/{wave_id}/approve`
- `POST /api/v1/rebalance/waves/{wave_id}/stage`
- `POST /api/v1/rebalance/waves/{wave_id}/handoff`
- `GET /api/v1/rebalance/waves/{wave_id}/supportability`

Purpose:

RFC-0041 Slice 4 manage-owned wave entrypoint for the first supported trigger:
`EXPLICIT_PORTFOLIO_LIST`. The preview endpoint builds a non-durable affected-portfolio wave so
portfolio managers and downstream orchestration can see the candidate set, source refs, blocked
items, aggregate counts, and event posture before persistence. The create endpoint persists the same
governed wave contract with an idempotency key. Slice 5 adds durable source-check classification
for persisted waves, using manage-owned mandate twins, mandate health snapshots, source-readiness
state, and available upstream `lotus-core` lineage refs. Slice 6 adds ready-item construction
simulation through RFC-0039 and item-level alternative selection with RFC-0040 proof-pack linkage.
Slice 7 adds manage-owned approval, staging, and internal operations handoff evidence without
external execution claims. Slice 8 adds product-safe operator supportability diagnostics and
bounded wave supportability telemetry.

Functional coverage:

- explicit affected-portfolio input only,
- source-backed candidate selection from caller-supplied source refs,
- source-backed candidate enrichment from an existing RFC-0038 mandate digital twin,
- truthful `SOURCE_BLOCKED` item state when affected-portfolio evidence is missing,
- unsupported trigger rejection with `NOT_SUPPORTED_TRIGGER`,
- durable create with idempotent replay,
- durable source-check from `CREATED` to `SOURCE_CHECKED`,
- item classification as `SOURCE_READY`, `SOURCE_DEGRADED`, `REVIEW_REQUIRED`, or
  `SOURCE_BLOCKED`,
- mandate digital-twin, mandate-health, source-readiness, and available `lotus-core` lineage refs
  attached to each item where present,
- source-check idempotent replay for already source-checked waves without duplicate events,
- simulation calls RFC-0039 construction alternatives only for `SOURCE_READY` items,
- ready items without real RFC-0039 construction input become `SIMULATION_BLOCKED`,
- source-blocked, degraded, and review-required item reasons are preserved through simulation,
- item selection delegates to RFC-0039 selection and persists selected alternative ids,
- proof-pack linkage delegates to RFC-0040 and degrades source-honestly when generation is not
  requested or fails,
- approval promotes only selected or proof-pack-ready items and never promotes blocked items,
- mixed approval produces `APPROVED_WITH_EXCEPTIONS`,
- staging promotes only approved items and records no-external-execution posture,
- handoff creates append-only internal operations handoff refs with actor, reason, item ids,
  content hash, and `external_execution_claimed=false`,
- supportability returns wave posture, issue counts, source owners, bounded reason codes,
  remediation routes, and support refs without portfolio ids, client ids, raw payloads, secrets, or
  trace details,
- no PM-book discovery, CIO model-change cohort discovery, Gateway composition, or Workbench
  product claim in these slices.

Non-functional posture:

- Preview is side-effect free and does not persist wave state.
- Create requires `Idempotency-Key` and stores a durable wave using optimistic-concurrency-ready
  repository contracts introduced in Slice 3.
- Aggregate metrics are reconciled from item state, not caller-provided totals.
- Missing source authority is exposed as blocked evidence instead of defaulting to readiness.
- Source-check does not promote any item to ready from a caller-supplied portfolio id or caller
  source ref alone; ready requires authoritative mandate twin and ready health/source-readiness
  evidence.
- Simulation does not synthesize holdings, market data, model targets, or shelf entries from
  mandate identifiers. It requires caller-supplied RFC-0039 construction input for each ready item.
- Selection appends a durable item-selection event without advancing approval or handoff state.
- Approval, staging, and handoff commands are idempotent after their terminal command states and do
  not append duplicate events or duplicate handoff refs.
- Handoff evidence is an internal operations readiness package only; it is not an OMS handoff,
  order execution instruction, or client communication.
- Supportability emits bounded structured logs and `lotus_manage_wave_supportability_total` with
  allowlisted `surface`, `supportability_state`, and `reason` labels.
- The endpoints do not call `lotus-core`, `lotus-risk`, `lotus-performance`, `lotus-report`,
  `lotus-ai`, Gateway, or Workbench directly in Slices 4 through 8.

Upstream integration posture:

The supported Slice 4-8 source inputs are existing manage-owned mandate digital twins, mandate
health snapshots, their source-readiness state, their persisted source lineage, explicit
caller-supplied affected-portfolio source refs, caller-supplied RFC-0039 construction inputs for
ready items, RFC-0040 proof-pack outputs generated from selected alternatives, and manage-owned
workflow decisions captured through actor-attributed approval/staging/handoff commands.
Supportability diagnostics are derived from persisted wave state and bounded item diagnostics.
Automatic PM-book or CIO model-change cohort discovery remains deferred until the owning app exposes
a certified source product.

Downstream consumers:

- `lotus-gateway` and `lotus-workbench` must wait for the later RFC-0041 realization RFC slice
  before advertising this as a full front-office product flow.
- Operators and API consumers may use these endpoints as manage backend preview/create contracts.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_waves_api.py tests/unit/dpm/api/test_observability_api.py tests/unit/test_observability_contracts.py tests/unit/dpm/waves/test_wave_domain.py -q
python -m ruff check src/api/services/wave_service.py src/api/routers/waves.py src/api/observability.py tests/unit/dpm/api/test_waves_api.py tests/unit/dpm/api/test_observability_api.py
python -m mypy --config-file mypy.ini src/api/services/wave_service.py src/api/routers/waves.py src/api/observability.py tests/unit/dpm/api/test_waves_api.py
python scripts/openapi_quality_gate.py
python scripts/api_vocabulary_inventory.py --validate-only
```

## Certified endpoint: proof-pack detail

Route:

- `GET /api/v1/rebalance/proof-packs/{proof_pack_id}`

Purpose:

Returns the persisted proof-pack JSON contract, including section states, source refs, evidence
refs, decision timeline, lineage, supportability counts, source hashes, and content hash.

Request surface:

- Path parameter: `proof_pack_id`.
- Response: `DpmProofPackLookupResponse`.
- Missing proof pack returns `404`.

Functional coverage:

- persisted proof-pack retrieval,
- hash and lineage round-trip,
- section-state visibility for ready, degraded, blocked, and pending-review posture.

Non-functional posture:

- The endpoint reads the stored proof-pack artifact and does not regenerate calculations.
- The response is bounded to the proof-pack contract and avoids raw upstream payload exposure.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_proof_pack_api.py::test_generate_get_and_render_direct_run_proof_pack -q
python scripts/openapi_quality_gate.py
```

## Certified endpoint: proof-pack Markdown summary

Route:

- `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/summary.md`

Purpose:

Returns deterministic human-readable Markdown rendered from the persisted proof pack for PM,
compliance, operations, audit, sales/pre-sales, and client-demo review material.

Request surface:

- Path parameter: `proof_pack_id`.
- Response: `text/plain` Markdown.
- Missing proof pack returns `404`.

Functional coverage:

- deterministic Markdown rendering,
- supportability matrix and evidence-gap visibility,
- timeline and integrity hash presentation.

Non-functional posture:

- Markdown is derived from persisted proof-pack truth and does not become a separate evidence
  authority.
- Degraded source evidence remains visible in the rendered summary.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_proof_pack_api.py::test_generate_get_and_render_direct_run_proof_pack tests/unit/dpm/proof_packs/test_proof_pack_markdown.py -q
python scripts/openapi_quality_gate.py
```

## Certified endpoint: proof-pack report input

Route:

- `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/report-input`

Purpose:

Returns deterministic `DpmProofPackReportInput` for a persisted proof pack. `lotus-report` can use
this payload for report materialization without reconstructing proof-pack sections, source hashes,
or supportability posture.

Request surface:

- Path parameter: `proof_pack_id`.
- Success response: `DpmProofPackReportInput`.
- Missing proof pack returns `404`.

Functional coverage:

- deterministic report-input generation,
- OpenAPI success contract for report payloads,
- append-only evidence ref generation when requested by the proof-pack generation call,
- report-input boundary kept separate from report materialization.

Non-functional posture:

- `lotus-manage` exposes report input only; `lotus-report` owns report materialization.
- The payload includes Markdown and section evidence derived from immutable proof-pack truth.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_proof_pack_api.py::test_generate_get_and_render_direct_run_proof_pack -q
python scripts/openapi_quality_gate.py
```

## Certified endpoint: proof-pack AI-evidence input

Route:

- `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/ai-evidence-input`

Purpose:

Returns deterministic `DpmProofPackAiEvidenceInput` for a persisted proof pack. The payload is
bounded for downstream AI workflows and carries forbidden-action guardrails.

Request surface:

- Path parameter: `proof_pack_id`.
- Success response: `DpmProofPackAiEvidenceInput`.
- Missing proof pack returns `404`.

Functional coverage:

- deterministic AI-evidence input generation,
- OpenAPI success contract for bounded AI-evidence payloads,
- forbidden-field removal,
- forbidden-action guardrails,
- append-only evidence ref generation when requested by the proof-pack generation call,
- AI-evidence boundary kept separate from AI PM memo generation.

Non-functional posture:

- `lotus-manage` exposes bounded evidence only; RFC-0043 and `lotus-ai` own memo generation.
- The payload must not be treated as approval, execution instruction, or client communication.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_proof_pack_api.py::test_generate_get_and_render_direct_run_proof_pack -q
python scripts/openapi_quality_gate.py
```
