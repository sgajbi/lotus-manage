# RFC-0040 Slice 12 Mandate-Context Source Hardening

This post-gold audit slice tightens the RFC-0040 mandate-context section so it meets the source
authority standard in the RFC instead of treating a supplied mandate id as enough evidence.

## Finding

The Slice 11 gold-pass audit correctly bounded front-office product claims, but a second review
found one manage-owned evidence gap:

1. `mandate_context` was marked `READY` when a caller supplied `mandate_id`,
2. the proof pack did not require persisted RFC-0038 mandate digital-twin evidence,
3. the proof pack did not attach latest mandate-health evidence or hashes,
4. the summary text still implied deeper mandate evidence belonged to later slices.

That behavior was source-honest for identity presence, but not gold-standard for a proof-pack
section whose RFC source map says it should use RFC-0038 mandate twin and core source refs.

## Implementation

Slice 12 changes proof-pack generation to resolve persisted mandate evidence from the existing
RFC-0038 mandate repository:

1. if no `mandate_id` is supplied, `mandate_context` remains `BLOCKED`,
2. if a `mandate_id` is supplied but no persisted mandate twin is available, `mandate_context` is
   `DEGRADED` with `DPM_MANDATE_TWIN_EVIDENCE_MISSING`,
3. if a mandate twin exists but latest health evidence is absent, `mandate_context` is `DEGRADED`
   with `DPM_MANDATE_HEALTH_EVIDENCE_MISSING`,
4. if persisted mandate evidence belongs to a different portfolio, `mandate_context` is `DEGRADED`
   with `DPM_MANDATE_TWIN_PORTFOLIO_MISMATCH` and the unsafe evidence is not attached,
5. if mandate twin and health evidence exist, section state is derived from mandate-health state:
   `READY`, `PENDING_REVIEW`, `BLOCKED`, or `DEGRADED` for non-ready source readiness,
6. mandate twin and health hashes are added to `source_hashes`,
7. mandate twin and health refs are added as source refs,
8. proof-pack APIs inject the governed mandate repository rather than fabricating mandate facts.

The service also refuses to attach mandate evidence when the persisted mandate portfolio does not
match the proof-pack source portfolio.

## Code Evidence

| Area | Evidence |
| --- | --- |
| Builder | `src/core/proof_packs/builder.py` |
| API service | `src/api/services/proof_pack_service.py` |
| API dependency injection | `src/api/routers/proof_packs.py` |
| Builder tests | `tests/unit/dpm/proof_packs/test_proof_pack_builder.py` |
| API tests | `tests/unit/dpm/api/test_proof_pack_api.py` |

## Validation

Focused validation:

```bash
python -m pytest tests\unit\dpm\proof_packs\test_proof_pack_builder.py tests\unit\dpm\api\test_proof_pack_api.py -q
python -m pytest tests\unit\dpm\proof_packs\test_proof_pack_service.py tests\unit\test_rfc0040_evidence_script.py tests\unit\test_documentation_current_state.py -q
python -m ruff check src\core\proof_packs\builder.py src\api\services\proof_pack_service.py src\api\routers\proof_packs.py tests\unit\dpm\proof_packs\test_proof_pack_builder.py tests\unit\dpm\api\test_proof_pack_api.py
python -m ruff format --check src\core\proof_packs\builder.py src\api\services\proof_pack_service.py src\api\routers\proof_packs.py tests\unit\dpm\proof_packs\test_proof_pack_builder.py tests\unit\dpm\api\test_proof_pack_api.py
make check
python scripts\generate_rfc0040_proof_pack_evidence.py --base-url http://127.0.0.1:8025
```

Expected proof:

1. proof packs with only a mandate id degrade instead of claiming `READY`,
2. proof packs with portfolio-mismatched mandate evidence degrade without attaching unsafe hashes,
3. proof packs with persisted mandate twin and health evidence carry mandate source hashes,
4. Markdown exposes the true mandate-context state,
5. direct-run and selected-alternative generation still work through the existing API contract,
6. live canonical evidence is captured in `output/rfc0040-proof/20260503-145818` with
   `mandate_context_source_honest: true` in `critical-review.json`.

## Product Boundary

This slice does not implement Gateway composition, Workbench proof-pack review UX, report
materialization, or AI PM memo generation. It tightens the manage-owned backend evidence fabric so
future downstream product slices consume stronger mandate context truth.
