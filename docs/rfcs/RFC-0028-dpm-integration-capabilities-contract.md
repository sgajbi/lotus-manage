# RFC-0028: lotus-manage Integration Capabilities Contract

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-23 |
| **Depends On** | RFC-0021, RFC-0022 |
| **Doc Location** | `docs/rfcs/RFC-0028-dpm-integration-capabilities-contract.md` |

## 1. Executive Summary

Expose a backend-governed capabilities contract so upstream, gateway, UI, and operations tooling can
discover which lotus-manage DPM features and workflows are enabled without hard-coding runtime
assumptions.

The implemented endpoint is:

`GET /api/v1/integration/capabilities`

## 2. Current Status Review (2026-05-03)

RFC-0028 is **implemented and aligned** with the current manage-only architecture. The original
draft named an unversioned capabilities route; the certified public route now uses the standard
versioned API prefix.

| Requirement | Current implementation evidence | Current status |
| --- | --- | --- |
| Backend-governed capability flags | `src/api/routers/integration_capabilities.py` | Implemented |
| Consumer and tenant-aware contract shape | `src/api/routers/integration_capabilities.py`, API tests | Implemented |
| Workflow capability publication | `src/core/capabilities.py`, integration capability tests | Implemented |
| Stateful portfolio-id mode advertised only when core sourcing is truly enabled | `src/api/routers/integration_capabilities.py`, `tests/unit/api/test_integration_capabilities_api.py` | Implemented |
| OpenAPI certified and documented | `tests/integration/test_openapi_certification_matrix.py`, `wiki/Endpoint-Certification.md` | Implemented |

## 3. Problem Statement

Downstream consumers should not infer lotus-manage behavior from environment variables, stale docs,
or UI assumptions. Enterprise DPM integration needs a machine-readable control point that states:

1. which input modes are currently available,
2. which DPM features are enabled,
3. which workflow surfaces are available, and
4. whether stateful execution can safely source required data from lotus-core.

## 4. Goals and Non-Goals

### 4.1 Goals

1. Publish the current lotus-manage DPM feature surface through one certified integration endpoint.
2. Keep feature gating in the backend, where it can use runtime configuration and dependency state.
3. Make stateful mode truthful: advertise it only when portfolio-id input, core sourcing, and core
   base URL configuration are all enabled.
4. Give lotus-gateway, lotus-workbench, operations tooling, and future consumers a stable discovery
   contract.

### 4.2 Non-Goals

1. Replace endpoint-level OpenAPI documentation.
2. Introduce advisory proposal capabilities into lotus-manage.
3. Provide portfolio-specific eligibility decisions; those belong to execution/readiness endpoints.

## 5. Contract

### 5.1 Request

Query parameters:

| Parameter | Required | Description | Example |
| --- | --- | --- | --- |
| `consumer_system` | No | Calling system requesting capability truth. | `lotus-workbench` |
| `tenant_id` | No | Tenant context used for policy-aware capability presentation. | `private-bank-sg` |

### 5.2 Response

Top-level fields:

| Field | Description |
| --- | --- |
| `contract_version` | Version of the capabilities response contract. |
| `source_service` | Always `lotus-manage`. |
| `consumer_system` | Echoed consumer identifier or default value. |
| `tenant_id` | Echoed tenant identifier when supplied. |
| `generated_at` | Server timestamp for the generated contract. |
| `as_of_date` | Business date used for policy presentation when available. |
| `policy_version` | Effective policy version advertised to consumers. |
| `supported_input_modes` | Available request modes, including stateless payload and portfolio-id mode when enabled. |
| `features` | Feature flags and explanatory metadata. |
| `workflows` | Workflow capabilities exposed by the service. |

## 6. Design Reasoning

This endpoint is intentionally descriptive rather than operational. It lets consumers render or route
correctly before invoking execution APIs, while execution APIs remain the source of truth for actual
portfolio-specific outcomes.

The stateful capability is deliberately conservative. It is enabled only when:

1. `DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED=true`,
2. `DPM_STATEFUL_CORE_SOURCING_ENABLED=true`,
3. `DPM_CORE_BASE_URL` is configured, and
4. no retired monolithic execution-context route is configured.

That prevents downstream systems from presenting a stateful workflow when lotus-manage cannot source
the required DPM data products from lotus-core.

## 7. Acceptance Criteria

1. `GET /api/v1/integration/capabilities` returns a versioned contract.
2. The contract includes input modes, features, and workflows with clear enabled/disabled semantics.
3. Stateful portfolio-id mode is advertised only when all required core-sourcing controls are enabled.
4. The route is included in OpenAPI and endpoint certification evidence.
5. Tests cover default, tenant/consumer, disabled, and stateful-enabled capability presentations.

## 8. Current Gap Assessment

No active implementation gaps remain in RFC-0028. Future changes should update this RFC only when
the capabilities contract itself changes; endpoint-specific behavior belongs in the owning endpoint
RFC and OpenAPI certification evidence.
