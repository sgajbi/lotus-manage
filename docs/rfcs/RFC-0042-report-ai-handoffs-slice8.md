# RFC-0042 Slice 8 - Report Input and AI Evidence Input Handoffs

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0042 Post-Trade Outcome Feedback Loop |
| **Slice** | 8 - Report Input and AI Evidence Input Handoffs |
| **Status** | DONE for manage handoff contracts |
| **Branch** | `feat/rfc0042-implementation` |

---

## Scope Completed

Slice 8 adds deterministic outcome-review handoff contracts:

1. `DpmOutcomeReportInput`
2. `DpmOutcomeAiEvidenceInput`
3. `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/report-input`
4. `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/ai-evidence-input`

These contracts are derived from the persisted immutable `DpmPostTradeOutcomeReview`. They do not
generate rendered reports, archive records, prompts, PM memos, recommendations, approvals, client
communications, or execution instructions inside `lotus-manage`.

---

## Design Decisions

1. Report input carries review id, review hash, portfolio/mandate/run/proof/wave references,
   review window, state, overall outcome, variance summary, dimension facts, supportability,
   source lineage, source hashes, section hashes, structured
   `DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY` evidence, redaction policy, evidence ref, and
   canonical content hash.
2. AI evidence input carries permitted use, forbidden actions, forbidden-field posture, bounded
   dimension facts, source refs, structured `DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY` evidence,
   evidence ref, and canonical content hash.
3. AI guardrails explicitly forbid order placement, rebalance approval, control overrides,
   invented missing evidence, `score_portfolio_manager`, and client contact.
4. Handoff hashes are deterministic and linked back to the source outcome-review content hash.
5. Missing reviews return `404 OUTCOME_REVIEW_NOT_FOUND`.

---

## Tests and Validation

Focused Slice 8 validation:

```powershell
python -m pytest tests\unit\core\test_outcome_handoffs.py tests\unit\api\test_outcome_reviews_api.py -q
python -m ruff check src\core\outcomes\handoffs.py src\core\outcomes\__init__.py src\api\services\outcome_review_service.py src\api\routers\outcome_reviews.py tests\unit\core\test_outcome_handoffs.py tests\unit\api\test_outcome_reviews_api.py
python scripts\openapi_quality_gate.py
python scripts\api_vocabulary_inventory.py --validate-only
python scripts\no_alias_contract_guard.py
python -m pytest tests\integration\test_openapi_certification_matrix.py -q
```

Result:

1. Focused handoff/API tests passed with `6 passed`.
2. Ruff passed.
3. OpenAPI quality gate passed.
4. API vocabulary inventory was regenerated and then passed validate-only with no drift.
5. No-alias contract guard passed.
6. OpenAPI certification matrix passed with `80 passed`.

Broader RFC-0042 targeted validation is run before committing the slice and recorded in the commit
evidence.

Broader targeted validation before closure:

```powershell
python -m pytest tests\unit\core\test_outcome_handoffs.py tests\unit\api\test_outcome_reviews_api.py tests\unit\core\test_outcome_comparison.py tests\unit\core\test_realized_outcome_sources.py tests\integration\dpm\test_outcome_expected_snapshot_assembly.py tests\unit\infrastructure\test_outcome_review_repository.py tests\unit\test_documentation_current_state.py -q
```

Result: `45 passed`.

---

## Support Claim

Slice 8 promotes only the manage-owned handoff contract implementation inside this implementation
branch. No full outcome-review product support is claimed. Report rendering, report archive
lifecycle, AI workflow packs, prompts, generated narrative, Gateway composition, Workbench UX,
supportability/observability hardening, live canonical proof, final PR/CI, merge, and wiki
publication remain pending.
