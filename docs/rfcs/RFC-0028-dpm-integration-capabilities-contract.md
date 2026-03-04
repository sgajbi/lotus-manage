# RFC-0028 lotus-manage Integration Capabilities Contract

- Status: Implemented
- Created: 2026-02-23
- Last Reviewed: 2026-03-05
- Depends On: RFC-0021, RFC-0022, RFC-0027

## Executive Summary

This RFC defines the backend-governed capabilities contract consumed by lotus-gateway and other clients. The implemented design exposes both:
1. `GET /integration/capabilities`
2. `GET /platform/capabilities`

and is mounted under both root and `/api/v1` prefixes.

## Original Proposal

The original proposal introduced `GET /integration/capabilities` with:
1. Inputs: `consumer_system`, `tenant_id`
2. Outputs: contract metadata, supported input modes, feature list, and workflow list
3. Goal: move feature/workflow toggles to backend contract governance.

## Implemented Contract (Current Reality)

Implementation location:
1. `src/api/routers/integration_capabilities.py`
2. Router included in `src/api/main.py` (root + `/api/v1`)

### Request Parameters

1. `consumer_system` (`lotus-gateway|lotus-performance|lotus-manage|UI|UNKNOWN`, default `lotus-gateway`)
2. `tenant_id` (`string`, default `default`)

### Response Schema

1. `contract_version`: version string (`v1`)
2. `source_service`: service identity (default `lotus-manage`, env-overridable)
3. `consumer_system`: echoed request consumer identity
4. `tenant_id`: echoed tenant scope
5. `generated_at`: UTC timestamp
6. `as_of_date`: service local date stamp
7. `policy_version`: policy bundle/version identifier
8. `supported_input_modes[]`: currently `pas_ref` plus optional `inline_bundle`
9. `features[]`:
   1. `key`
   2. `enabled`
   3. `owner_service`
   4. `description`
10. `workflows[]`:
    1. `workflow_key`
    2. `enabled`
    3. `required_features[]`

### Capability Evaluation Logic

Deterministic construction logic:
1. `lifecycle_enabled = bool(DPM_CAP_PROPOSAL_LIFECYCLE_ENABLED, default=true)`
2. `inline_bundle_enabled = bool(DPM_CAP_INPUT_MODE_INLINE_BUNDLE_ENABLED, default=true)`
3. `supported_input_modes = {"pas_ref"} U ({"inline_bundle"} if inline_bundle_enabled else {})`
4. `policy_version = env(DPM_POLICY_VERSION, "dpm.policy.v1")`
5. `source_service = env(DPM_CAP_SOURCE_SERVICE, "lotus-manage")`

This keeps clients backend-agnostic: clients consume capabilities, not internal implementation assumptions.

## What Changed vs Original and Why It Is Better

1. Originally proposed one route; implemented two route aliases (`/integration/capabilities`, `/platform/capabilities`) and versioned mounting for compatibility across caller types.
2. Original output list was high-level; implemented schema adds `generated_at` and `as_of_date` for observability and cache coherency.
3. Original contract did not define dynamic governance source; implemented contract uses environment-controlled flags and policy versioning for controlled rollout.

These changes improve compatibility, operational control, and auditability without breaking the original contract intent.

## Validation Evidence

1. Unit contract checks: `tests/unit/dpm/api/test_integration_capabilities_api.py`
2. Integration contract checks: `tests/integration/dpm/api/test_dpm_api_workflow_integration.py` (`test_integration_capabilities_contract_default_consumer`)
3. Health/capability coverage: `tests/integration/test_health.py`

## Remaining Delta

No functional delta remains for RFC-0028 scope.
