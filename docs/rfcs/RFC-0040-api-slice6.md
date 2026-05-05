# RFC-0040 Slice 6 API Evidence

This slice adds the certified manage-owned API surface for pre-trade proof-pack generation,
retrieval, Markdown rendering, and guarded downstream evidence-reference retrieval. It does not
implement report-input or AI-evidence adapters; those remain Slice 7 and are exposed as truthful
`424` failed-dependency states until generated refs exist.

## Implementation

Slice 6 added:

1. `src/api/routers/proof_packs.py` for `/api/v1/rebalance/proof-packs` endpoints,
2. `src/api/services/proof_pack_service.py` for source lookup, proof-pack building, persistence,
   idempotency, retention, and API error mapping,
3. `get_proof_pack_repository` dependency with a bounded in-memory default for local/test runtime,
4. run-support service read methods for source-backed proof-pack assembly,
5. unit API coverage for generation, idempotent replay, lookup, Markdown, guarded report/AI refs,
   source validation, and OpenAPI path documentation.

## Certified Routes

| Route | Purpose | Current support posture |
| --- | --- | --- |
| `POST /api/v1/rebalance/proof-packs` | Generate and persist a proof pack from a rebalance run or selected alternative. | Supported manage backend API. |
| `GET /api/v1/rebalance/proof-packs/{proof_pack_id}` | Retrieve persisted proof-pack JSON with hashes, lineage, sections, and supportability. | Supported manage backend API. |
| `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/summary.md` | Render deterministic Markdown from the persisted proof pack. | Supported manage backend API. |
| `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/report-input` | Retrieve generated report-input evidence ref. | Route certified; returns `424` until Slice 7 adapter generates refs. |
| `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/ai-evidence-input` | Retrieve generated AI-evidence input ref. | Route certified; returns `424` until Slice 7 adapter generates refs. |

## Boundary Decisions

1. `lotus-manage` remains the proof-pack artifact authority.
2. Gateway and Workbench do not gain product-realization support in this slice.
3. Report materialization and AI PM memo generation are not claimed.
4. Report and AI endpoints expose success response contracts for generated refs, but unavailable
   refs are governed failed dependencies until Slice 7.
5. Missing source evidence remains visible through degraded or blocked section states.

## Evidence Commands

```bash
python -m pytest tests/unit/dpm/api/test_proof_pack_api.py -q
python -m pytest tests/unit/dpm/api/test_proof_pack_api.py tests/unit/dpm/proof_packs tests/unit/shared/dependencies/test_postgres_migrations.py tests/unit/test_documentation_current_state.py -q
python -m ruff check src/api/dependencies.py src/api/main.py src/api/routers/proof_packs.py src/api/services/proof_pack_service.py src/core/rebalance_runs/service.py tests/unit/dpm/api/test_proof_pack_api.py
python scripts/openapi_quality_gate.py
```

## No Supported-Feature Promotion

RFC-0040 remains in progress. The Slice 6 API is implementation-backed and endpoint-certified, but
the full proof-pack business outcome still requires report and AI adapters, Gateway composition,
Workbench product realization, live canonical evidence, PR merge evidence, and final RFC gold-pass
assessment.
