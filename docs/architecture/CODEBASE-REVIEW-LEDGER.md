# Codebase Review Ledger

This ledger records cleanup and structural review evidence for RFC-0036.

## RFC36-S2-001: Review control docs were missing

- Date: 2026-05-01
- Scope: `docs/architecture`, RFC-0036 cleanup slice
- Finding: the repository had RFC execution text and current-state docs, but no durable local ledger
  for pattern-based cleanup findings.
- Action: added `docs/architecture/README.md`,
  `docs/architecture/CODEBASE-REVIEW-PLAYBOOK.md`, and this ledger.
- Status: fixed
- Wiki decision: no wiki source change required; these are engineering control documents, not
  product/operator truth.

## RFC36-S2-002: Retired advisory/proposal package directories existed as generated remnants

- Date: 2026-05-01
- Scope: retired advisory and proposal package namespaces
- Finding: active Python modules had already been removed, but ignored `__pycache__` directories kept
  retired package namespaces present on disk.
- Action: removed the generated directories and tightened the current-state documentation test to
  guard both retired package namespaces.
- Status: fixed
- Wiki decision: no wiki source change required; the existing wiki already states that advisory
  proposal workflows belong to `lotus-advise`.

## RFC36-S2-003: Duplicate unversioned domain API mounts remain

- Date: 2026-05-01
- Scope: `src/api/main.py`
- Finding: unversioned product routers are still mounted alongside `/api/v1` routers.
- Action: deferred to RFC-0036 Slice 3 because it changes runtime endpoint behavior and must be
  implemented with route inventory, OpenAPI, vocabulary, docs, tests, and live evidence together.
- Status: deferred to Slice 3
- Wiki decision: no wiki source change in Slice 2.

## RFC36-S3-001: Duplicate product endpoint surface removed

- Date: 2026-05-01
- Scope: `src/api/main.py`, `src/api/routers/integration_capabilities.py`, OpenAPI inventory
- Finding: product routers were mounted both unversioned and under `/api/v1`, and capability
  discovery was exposed under both integration and platform namespaces.
- Action: removed unversioned product router mounts, removed the platform capability alias, kept
  health and metrics as unversioned infrastructure probes, and regenerated the API vocabulary
  inventory.
- Status: fixed
- Wiki decision: wiki source updated because endpoint and demo-facing product truth changed.

## RFC36-S2-004: Advisory vocabulary remains in historical rationale and boundary docs

- Date: 2026-05-01
- Scope: `docs/rfcs`, `docs/adr`, `docs/documentation`, `wiki`
- Finding: advisory/proposal terms appear in historical RFCs and explicit ownership-boundary docs.
  Current-state tests already block removed proposal route names, proposal persistence, and proposal
  repository language in active docs.
- Action: retained historical rationale and boundary statements; deferred active vocabulary cleanup
  to RFC-0036 Slice 4.
- Status: deliberately retained until Slice 4 review
- Wiki decision: no wiki source change in Slice 2.
