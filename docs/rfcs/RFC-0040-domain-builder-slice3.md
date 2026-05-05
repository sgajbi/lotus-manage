# RFC-0040 Slice 3 Domain Models and Pure Builder Evidence

Date: 2026-05-03

Branch: `feat/rfc0040-gold-standard-tightening`

## Result

Slice 3 is complete.

This slice adds the manage-owned pure domain layer for RFC-0040 proof packs. It deliberately does
not add Markdown, persistence, or APIs; those remain later RFC-0040 slices. The implementation can now
assemble a deterministic `DpmPreTradeProofPack` from current manage truth without claiming
downstream report, AI, Gateway, or Workbench support.

## Implemented Domain Boundary

New package:

1. `src/core/proof_packs/models.py`
2. `src/core/proof_packs/builder.py`
3. `src/core/proof_packs/__init__.py`

Implemented models:

1. `DpmPreTradeProofPack`
2. `DpmProofPackSection`
3. `DpmProofPackDecisionSummary`
4. `DpmProofPackDecisionTimeline`
5. `DpmProofPackSupportability`
6. source and evidence reference models

Implemented pure builders:

1. `build_proof_pack_from_run`
2. `build_proof_pack_from_selected_alternative`

## Evidence Behavior

The builder now:

1. generates every RFC-0040 section,
2. assigns each section a truthful `READY`, `PENDING_REVIEW`, `DEGRADED`, or `BLOCKED` state,
3. computes deterministic section hashes and proof-pack content hash,
4. captures direct-run evidence without inventing selected-alternative context,
5. captures selected-alternative method, method status, objective trace, constraint trace, and
   comparison metrics,
6. captures optional workflow decisions in approval evidence and the decision timeline,
7. blocks proof-pack promotion when mandatory mandate identity is missing,
8. leaves report input and AI evidence refs degraded until their owning slices implement the typed
   handoff contracts,
9. leaves risk, performance, sustainability, currency-overlay, and scenario authority sections
   degraded unless source-backed authority context is present in later slices.

## Validation

Targeted behavior and cleanup validation:

1. `python -m pytest tests\unit\dpm\proof_packs\test_proof_pack_builder.py -q`
2. `python -m pytest tests\unit\dpm\proof_packs\test_proof_pack_builder.py tests\unit\dpm\construction\test_alternative_engine.py tests\unit\dpm\supportability\test_dpm_run_support_service_coverage.py -q`
3. `python -m ruff check src\core\proof_packs tests\unit\dpm\proof_packs`
4. `python -m ruff format --check src\core\proof_packs tests\unit\dpm\proof_packs`
5. `git diff --check`

Repository governance validation to run before committing this slice:

1. `python -m pytest tests\unit\test_documentation_current_state.py -q`
2. `python scripts/api_vocabulary_inventory.py --validate-only`
3. `python scripts/no_alias_contract_guard.py`
4. `python scripts/openapi_quality_gate.py`

## Deferred To Later Slices

1. immutable persistence and repository adapters,
2. generated Markdown summary persistence,
3. typed report input adapter,
4. typed AI evidence adapter,
5. proof-pack APIs and OpenAPI certification,
6. Gateway and Workbench realization RFC updates.
