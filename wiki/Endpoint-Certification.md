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
   response attribute with examples,
6. live API evidence has been captured against a running `lotus-manage` instance.

## Certified endpoint: capabilities discovery

Routes:

- `GET /integration/capabilities`
- `GET /platform/capabilities`

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
- `/platform/capabilities` alias parity with `/integration/capabilities`,
- conservative default input-mode posture,
- environment-controlled stateful `portfolio_id` publication,
- environment-controlled `inline_bundle` publication,
- runtime solver dependency discovery,
- noncanonical camelCase direct-source query parameters do not override defaults.

Default capability posture:

- `inline_bundle` execution is enabled,
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

Tracked downstream remediation:

- `sgajbi/lotus-gateway#178` tracks Gateway cleanup for direct source-service query parameters,
  stale proposal/advisory-era DPM client methods, and normalized capability mapping from strategic
  `lotus-manage` DPM feature/workflow keys.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_integration_capabilities_api.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: single rebalance simulation

Route:

- `POST /rebalance/simulate`

Purpose:

Runs one deterministic discretionary mandate portfolio rebalance from a complete inline request
bundle. This is the core manage-owned execution endpoint for portfolio management, policy-pack
application, run supportability, lineage, idempotency, and workflow-gate outcome publication. It is
not an advisory proposal endpoint and must not be used as a canonical portfolio read API.

Request surface:

- Body: `portfolio_snapshot`, `market_data_snapshot`, `model_portfolio`, `shelf_entries`, `options`
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
- supportability persistence, artifact, workflow, lineage, idempotency, and summary integration.

Non-functional posture:

- Synchronous execution is intended for one bounded simulation request.
- Idempotency protects client retries and prevents same-key/different-request ambiguity.
- The endpoint records supportability state when persistence is enabled; replay-enabled persistence
  failures return service-unavailable responses rather than falsely accepting a run.
- For multi-scenario or deferred execution, use `/rebalance/analyze` or `/rebalance/analyze/async`.

Upstream integration posture:

The current route accepts inline snapshots and does not make outbound source-data reads. Upstream
portfolio, price, FX, and instrument-source authority remains outside `lotus-manage`; callers must
provide source-governed snapshots and preserve lineage identifiers. Stateful `portfolio_id`
execution remains disabled in capabilities until governed `lotus-core` resolution is implemented.

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
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: synchronous what-if analysis

Route:

- `POST /rebalance/analyze`

Purpose:

Runs a bounded set of named discretionary mandate what-if scenarios against shared inline snapshots
and returns the full batch result synchronously. Use this endpoint when the caller needs immediate
scenario comparison. Use `/rebalance/analyze/async` for polling-based orchestration or
accept-now/execute-later flows.

Request surface:

- Body: shared `portfolio_snapshot`, `market_data_snapshot`, `model_portfolio`, `shelf_entries`,
  plus a named `scenarios` map.
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
- For latency-sensitive or deferred batches, callers should use `/rebalance/analyze/async`.

Upstream integration posture:

The endpoint accepts inline source-governed snapshots and does not perform outbound source-data reads.
Upstream data authority remains outside `lotus-manage`; lineage and snapshot identifiers must be
preserved by callers. Policy-pack resolution is local to `lotus-manage`.

Downstream consumers:

- No direct strategic Gateway or Workbench consumer was found for `/rebalance/analyze`.
- Future Gateway/Workbench mandate-analysis integration should capability-gate this endpoint and
  preserve scenario names, correlation ids, and policy-pack context.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```

## Certified endpoint: async what-if analysis submission

Route:

- `POST /rebalance/analyze/async`

Purpose:

Accepts the same named discretionary mandate scenario batch as synchronous analysis, but returns an
operation handle for polling or accept-now/execute-later orchestration. Use this endpoint when the
caller needs deferred execution, operation-level supportability, or explicit manual execution in
`DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`.

Request surface:

- Body: `BatchRebalanceRequest`.
- Optional headers: `X-Correlation-Id`, `X-Policy-Pack-Id`, `X-Tenant-Policy-Pack-Id`,
  `X-Tenant-Id`.
- Response: `DpmAsyncAcceptedResponse` with `operation_id`, initial `status`, `correlation_id`,
  `status_url`, and `execute_url`.
- Retrieval: `GET /rebalance/operations/{operation_id}` or
  `GET /rebalance/operations/by-correlation/{correlation_id}`.

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

The endpoint persists caller-supplied inline snapshots and policy context for later execution. It
does not perform outbound source-data reads; snapshot authority and lineage remain with upstream
callers and `lotus-core`-governed data products.

Downstream consumers:

- No direct strategic Gateway or Workbench consumer was found for `/rebalance/analyze/async`.
- Future downstream integration should treat this endpoint as the strategic deferred DPM analysis
  submission route, not as an advisory proposal lifecycle route.

Evidence commands:

```bash
python -m pytest tests/unit/dpm/api/test_api_rebalance.py tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
LOTUS_MANAGE_BASE_URL=http://127.0.0.1:8001 make live-api-validate
```
