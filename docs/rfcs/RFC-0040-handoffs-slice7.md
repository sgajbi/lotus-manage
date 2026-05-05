# RFC-0040 Slice 7 Report and AI Handoff Evidence

This slice adds the manage-owned handoff contracts for downstream report materialization and
governed AI evidence consumption. It does not implement `lotus-report` report rendering, `lotus-ai`
memo generation, Gateway composition, or Workbench product realization.

## Implementation

Slice 7 added:

1. `DpmProofPackReportInput` and `DpmProofPackReportSection`,
2. `DpmProofPackAiEvidenceInput` and `DpmProofPackAiEvidenceSection`,
3. deterministic builders in `src/core/proof_packs/handoffs.py`,
4. AI forbidden-action and forbidden-field guardrails,
5. report and AI endpoint response contracts that now return typed payloads,
6. append-only evidence refs for generated report/AI inputs,
7. API hydration of append-only refs without mutating the immutable proof-pack body.

## Contract Boundaries

`lotus-manage` owns:

1. proof-pack truth,
2. report-input shaping,
3. AI-evidence shaping,
4. source hashes and section hashes,
5. forbidden-field removal for AI evidence,
6. generated handoff evidence refs.

`lotus-report` still owns report materialization from `DpmProofPackReportInput`.

`lotus-ai` still owns any PM memo, operations summary, copilot answer, or model execution. RFC-0043
will govern those user-facing AI outputs.

Gateway and Workbench remain downstream realization work. They must consume manage/Gateway
contracts and must not reconstruct proof-pack evidence in presentation code.

## Guardrails

The AI evidence adapter removes forbidden field names including:

1. `client_name`,
2. `client_id`,
3. `account_number`,
4. `email`,
5. `phone`,
6. `raw_payload`,
7. `raw_request`,
8. `raw_response`,
9. `secret`,
10. `token`.

The AI evidence adapter also carries forbidden actions:

1. `place_orders`,
2. `approve_rebalance`,
3. `override_controls`,
4. `invent_missing_evidence`,
5. `contact_client`.

## Evidence Commands

```bash
python -m pytest tests/unit/dpm/api/test_proof_pack_api.py tests/unit/dpm/proof_packs -q
python -m mypy src/api/routers/proof_packs.py src/api/services/proof_pack_service.py src/core/proof_packs src/infrastructure/proof_packs --config-file mypy.ini
python scripts/openapi_quality_gate.py
```

## No Supported-Feature Promotion

RFC-0040 remains in progress. Slice 7 completes manage-owned report and AI evidence handoff
contracts, but report rendering, AI memo generation, Gateway composition, Workbench UX, live
canonical proof, and final RFC gold-pass assessment remain later slices.
