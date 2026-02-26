# RFC-0021: lotus-manage OpenAPI Contract Hardening and Separation of Request/Response Models

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0007A, RFC-0016, RFC-0017 |
| **Doc Location** | `docs/rfcs/RFC-0021-dpm-openapi-contract-hardening.md` |

## 1. Executive Summary

Harden lotus-manage OpenAPI contracts so request and response objects are explicitly separated, with complete field-level descriptions/examples and contract tests to prevent accidental schema drift.

## 2. Problem Statement

Schema ambiguity and mixed request/response models reduce integrator confidence and make production support harder. Advisory APIs already use stricter schema discipline.

## 3. Goals and Non-Goals

### 3.1 Goals

- Separate request and response models for public endpoints.
- Require field descriptions and examples for Swagger quality.
- Add contract tests that assert schema shape and metadata.

### 3.2 Non-Goals

- Re-architect core engine logic.
- Introduce breaking route changes.

## 4. Proposed Design

### 4.1 OpenAPI Improvements

- Dedicated DTOs for request vs response per endpoint.
- `Field(..., description=..., examples=[...])` coverage for each public attribute.
- Consistent error envelope docs.

### 4.2 Contract Testing

- Snapshot/semantic tests over `/openapi.json`.
- Assertions for required fields, enums, and examples on targeted models.

Phase-1 implemented:
- Added lotus-manage OpenAPI contract tests for async/supportability/artifact schemas and endpoint contracts:
  - `tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py`
- Validates:
  - field-level descriptions/examples for key lotus-manage response DTOs
  - field-level descriptions/examples for lotus-manage policy-pack resolution/catalog and nested policy DTOs
  - request/response schema separation and response header docs on async analyze
  - request/response schema separation on:
    - `POST /rebalance/simulate`
    - `POST /rebalance/analyze`
    - `POST /rebalance/analyze/async`
    - `GET /rebalance/policies/effective`
    - `GET /rebalance/policies/catalog`
  - execute endpoint contract shape (`POST /rebalance/operations/{operation_id}/execute`)
  - artifact endpoint contract shape (`GET /rebalance/runs/{rebalance_run_id}/artifact`)
Phase-2 implemented:
- Extended lotus-manage OpenAPI contract assertions for policy-pack management APIs:
  - `GET /rebalance/policies/catalog/{policy_pack_id}`
  - `PUT /rebalance/policies/catalog/{policy_pack_id}`
  - `DELETE /rebalance/policies/catalog/{policy_pack_id}`
- Added schema metadata assertions for:
  - `DpmPolicyPackUpsertRequest`
  - `DpmPolicyPackMutationResponse`
- Updated schema assertions to support request/response split model naming patterns
  (`-Input` / `-Output`) while preserving strict docs coverage checks.

### 4.3 Configurability

- `DPM_STRICT_OPENAPI_VALIDATION` (default `true` in CI, configurable locally)

Phase-1 implemented:
- lotus-manage contract test suite reads `DPM_STRICT_OPENAPI_VALIDATION`.
- When set to `false`, strict lotus-manage OpenAPI contract tests are skipped for local iteration.

## 5. Test Plan

- OpenAPI generation test for each lotus-manage route family.
- Schema tests for required example/description coverage.
- Regression tests for idempotency and supportability models.

## 6. Rollout/Compatibility

No runtime behavior change intended. External clients benefit from clearer contracts and stronger backward compatibility guardrails.

## 7. Status and Reason Code Conventions

No status vocabulary changes introduced by this RFC.
