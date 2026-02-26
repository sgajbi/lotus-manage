# RFC-0028 DPM Integration Capabilities Contract

- Status: Accepted
- Date: 2026-02-23

## Summary

Add `GET /integration/capabilities` to expose backend-governed DPM feature and workflow capability flags for BFF, PAS, and UI integration.

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
2. Enables BFF/UI to drive behavior from capability contracts.
3. Aligns DPM with PAS and PA integration-governance direction.
