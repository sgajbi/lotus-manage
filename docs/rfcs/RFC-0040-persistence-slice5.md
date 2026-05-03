# RFC-0040 Slice 5 Persistence Evidence

Date: 2026-05-03

Branch: `feat/rfc0040-gold-standard-tightening`

## Result

Slice 5 is complete.

This slice adds the proof-pack persistence contract, in-memory implementation, PostgreSQL adapter,
and DPM PostgreSQL migration. It does not expose proof-pack APIs; API certification remains Slice 6.

## Implemented

New persistence contract:

1. `src/core/proof_packs/repository.py`
2. `DpmProofPackRepository`
3. immutable save semantics
4. idempotency lookup
5. retention metadata lookup
6. append-only post-creation refs

New infrastructure:

1. `src/infrastructure/proof_packs/in_memory.py`
2. `src/infrastructure/proof_packs/postgres.py`
3. `src/infrastructure/postgres_migrations/dpm/0006_pre_trade_proof_packs.sql`

Persistence covers:

1. proof-pack body,
2. proof-pack sections,
3. content hashes,
4. source and section round-trip through payload JSON,
5. retention policy and expiry,
6. append-only refs.

## Validation

Targeted validation:

1. `python -m pytest tests\unit\dpm\proof_packs\test_proof_pack_repository.py tests\unit\shared\dependencies\test_postgres_migrations.py -q`
2. `python -m pytest tests\unit\dpm\proof_packs tests\unit\shared\dependencies\test_postgres_migrations.py -q`
3. `python -m ruff check src\core\proof_packs src\infrastructure\proof_packs tests\unit\dpm\proof_packs`
4. `python -m mypy src\core\proof_packs src\infrastructure\proof_packs --config-file mypy.ini`

Repository governance validation to run before committing this slice:

1. `git diff --check`
2. `python -m pytest tests\unit\test_documentation_current_state.py -q`
3. `python scripts/api_vocabulary_inventory.py --validate-only`
4. `python scripts/no_alias_contract_guard.py`
5. `python scripts/openapi_quality_gate.py`

## Wiki Decision

No wiki source change is made in Slice 5. Persistence is not directly user-facing until Slice 6
adds certified APIs and supported-feature truth can be promoted accurately.
