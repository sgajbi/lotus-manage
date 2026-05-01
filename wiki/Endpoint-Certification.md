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
