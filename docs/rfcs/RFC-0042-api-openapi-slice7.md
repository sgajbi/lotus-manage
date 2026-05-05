# RFC-0042 Slice 7 - Certified Manage APIs and OpenAPI Quality

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0042 Post-Trade Outcome Feedback Loop |
| **Slice** | 7 - Certified Manage APIs and OpenAPI Quality |
| **Status** | DONE for manage API foundation |
| **Branch** | `feat/rfc0042-implementation` |

---

## Scope Completed

Slice 7 adds the first RFC-0042 manage API foundation for post-trade outcome reviews:

1. `POST /api/v1/rebalance/outcome-reviews/preview`
2. `POST /api/v1/rebalance/outcome-reviews`
3. `GET /api/v1/rebalance/outcome-reviews`
4. `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}`
5. `POST /api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources`
6. `GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability`
7. `GET /api/v1/rebalance/runs/{rebalance_run_id}/outcome-review`
8. `GET /api/v1/rebalance/waves/{wave_id}/outcome-reviews`

The endpoints are grouped under `lotus-manage Outcome Reviews` and expose the RFC-0042 backend
truth surface without claiming Gateway, Workbench, report, archive, or AI product realization.

---

## Design Decisions

1. Preview is side-effect free and uses explicit expected and realized snapshots.
2. Create requires `Idempotency-Key` and persists an immutable review with content hash, source
   lineage, retention metadata, and append-only creation event.
3. Search is bounded and repository-backed by portfolio, mandate, wave, run, and state.
4. Supportability returns operator-safe state and reason codes without raw source payloads.
5. Source refresh reuses the immutable expected snapshot, accepts a new source-owner realized
   snapshot, recomputes comparison output, and appends an `OUTCOME_REVIEW_SOURCE_REFRESHED` event.
   It does not mutate the immutable review body.
6. Run and wave lookup endpoints are read-side conveniences over the same outcome-review authority;
   they do not reconstruct state or compose source-owner values locally.

---

## OpenAPI Quality

The API test suite now asserts that RFC-0042 paths are present in OpenAPI, grouped under
`lotus-manage Outcome Reviews`, and that the preview and refresh descriptions include explicit
What/When/How guidance. Pydantic field descriptions and examples are carried from the domain models
and request/response models.

Remaining OpenAPI depth for later hardening:

1. add route-local degraded, blocked, unsupported, conflict, and not-found examples for every
   endpoint,
2. add report-input and AI-evidence endpoint schemas during Slice 8,
3. include API vocabulary/no-alias evidence in the implementation-proof bundle.

---

## Tests and Validation

Focused Slice 7 validation:

```powershell
python -m pytest tests\unit\api\test_outcome_reviews_api.py -q
python -m ruff check src\api\routers\outcome_reviews.py src\api\services\outcome_review_service.py tests\unit\api\test_outcome_reviews_api.py
python scripts\openapi_quality_gate.py
python scripts\api_vocabulary_inventory.py --validate-only
python scripts\no_alias_contract_guard.py
python -m pytest tests\integration\test_openapi_certification_matrix.py -q
```

Result:

1. API behavior tests passed.
2. OpenAPI grouping and What/When/How guardrail test passed.
3. Ruff passed for the new API/service/test files.
4. OpenAPI quality gate passed.
5. API vocabulary inventory was regenerated and then passed validate-only with no drift.
6. No-alias contract guard passed.
7. OpenAPI certification matrix passed with `80 passed`.

Broader RFC-0042 targeted validation is run before committing the slice and recorded in the commit
evidence.

Broader targeted validation before closure:

```powershell
python -m pytest tests\unit\api\test_outcome_reviews_api.py tests\unit\core\test_outcome_comparison.py tests\unit\core\test_realized_outcome_sources.py tests\integration\dpm\test_outcome_expected_snapshot_assembly.py tests\unit\infrastructure\test_outcome_review_repository.py tests\unit\test_documentation_current_state.py -q
```

Result: `42 passed`.

---

## Support Claim

No full RFC-0042 supported feature is promoted by Slice 7. It completes the manage API foundation
needed for later report/AI handoffs, supportability/observability, live evidence,
Gateway/Workbench RFC realization, hardening, final documentation, PR review, CI, merge, and wiki
publication.
