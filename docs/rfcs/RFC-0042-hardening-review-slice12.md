# RFC-0042 Slice 12 - Second-Last Hardening and Review

| Field | Value |
| --- | --- |
| RFC | RFC-0042 Post-Trade Outcome Feedback Loop |
| Slice | 12 - Second-Last Hardening and Review |
| Status | COMPLETE |
| Branch | `feat/rfc0042-implementation` |
| Hardening proof | `output/rfc0042-outcome-proof/20260505-025613/` |
| Critical review | `output/rfc0042-outcome-proof/20260505-025613/critical-review.json` |

## Review Scope

Slice 12 reviewed the RFC-0042 manage backend implementation after Slice 11 live proof. The review
covered domain comparison behavior, idempotency, API request validation, OpenAPI guidance,
report/AI handoff contracts, supportability telemetry, source-boundary posture, persistence
immutability, and proof repeatability.

## Findings and Fixes

| Finding | Risk | Fix |
| --- | --- | --- |
| Same `Idempotency-Key` with changed source evidence replayed the original review. | Caller error could look like a successful changed-evidence create. | `create_outcome_review` now recomputes the deterministic review content hash before replay and raises `DPM_OUTCOME_REVIEW_IDEMPOTENCY_CONFLICT` when same-key evidence changes. |
| Outcome-review search accepted `state` as an arbitrary string. | Invalid state filters could silently look like no results. | `state` is now typed as `OutcomeReviewState`, producing a 422 validation error for invalid filters. |
| Report/AI handoff evidence ref helper was named `_placeholder_ref`. | Misleading naming suggested placeholder behavior in a no-placeholder evidence contract. | Renamed to `_handoff_ref`; behavior remains deterministic and source-ref-backed. |
| Live proof did not explicitly prove idempotency conflict behavior. | Hardening fix would rely only on unit tests. | `scripts/generate_rfc0042_outcome_evidence.py` now captures same-key replay and same-key changed-evidence conflict responses. |

## Live Proof Result

The hardening proof passed at `output/rfc0042-outcome-proof/20260505-025613/`.

Critical-review checks include:

1. `review_created_ready`,
2. `idempotency_replay_preserved_review`,
3. `idempotency_conflict_rejected`,
4. `source_lineage_preserved`,
5. `supportability_operator_fields_present`,
6. `report_input_is_handoff_only`,
7. `ai_evidence_guardrails_present`,
8. `degraded_source_example_visible`,
9. `refresh_appended_event`,
10. `openapi_certification_passed`,
11. `variance_worked_example_passed`.

Additional hardening evidence files:

1. `04a-idempotency-replay-response.json`,
2. `04b-idempotency-conflict-response.json`.

## Validation Commands

Slice 12 validation included:

```powershell
python -m pytest tests\unit\api\test_outcome_reviews_api.py tests\unit\core\test_outcome_handoffs.py -q
python -m ruff check src\api\routers\outcome_reviews.py src\api\services\outcome_review_service.py src\core\outcomes\handoffs.py tests\unit\api\test_outcome_reviews_api.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Start-CanonicalManage.ps1 -Port 8001
python scripts\generate_rfc0042_outcome_evidence.py --base-url http://127.0.0.1:8001
```

The full RFC-0042 gate must still be run during Slice 13 closure before PR finalization.

## Supported-Feature Decision

No full RFC-0042 product support is promoted by Slice 12. The manage backend is stronger and
live-proven with hardening evidence, but final closure, PR/CI, merge, wiki publication, and
downstream product realization where surfaced remain required.
