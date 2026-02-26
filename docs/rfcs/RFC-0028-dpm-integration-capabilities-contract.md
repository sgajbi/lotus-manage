# RFC-0028 lotus-manage Integration Capabilities Contract

- Status: Accepted
- Date: 2026-02-23

## Summary

Add `GET /integration/capabilities` to expose backend-governed lotus-manage feature and workflow capability flags for lotus-gateway, lotus-core, and UI integration.

## Contract

Inputs:
- `consumerSystem`
- `tenantId`

Outputs:
- `contractVersion`
- `sourceService`
- `consumerSystem`
- `tenantId`
- `policyVersion`
- `supportedInputModes`
- `features[]`
- `workflows[]`

## Rationale

1. Keeps workflow/feature control in backend.
2. Enables lotus-gateway/UI to drive behavior from capability contracts.
3. Aligns lotus-manage with lotus-core and lotus-performance integration-governance direction.
