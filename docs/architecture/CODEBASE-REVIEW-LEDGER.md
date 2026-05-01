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

## RFC36-S4-001: Advisory-era client-consent workflow vocabulary removed

- Date: 2026-05-01
- Scope: DPM engine options, workflow gates, policy-pack contracts, tests, OpenAPI vocabulary, docs
- Finding: discretionary mandate workflow gates still exposed advisory-style client-consent fields
  and gate states. That wording is not domain-correct for DPM execution control.
- Action: replaced client-consent API vocabulary with mandate-approval vocabulary:
  `workflow_requires_mandate_approval`, `mandate_approval_already_obtained`,
  `MANDATE_APPROVAL_REQUIRED`, and `REQUEST_MANDATE_APPROVAL`.
- Status: fixed
- Wiki decision: wiki supported-features source updated to keep advisory client-consent ownership
  with `lotus-advise`.

## RFC36-S4-002: Retired proposal infrastructure remnants removed

- Date: 2026-05-01
- Scope: retired proposal infrastructure package and migration namespaces
- Finding: tracked proposal infrastructure code was already gone, but ignored generated remnants kept
  retired proposal directories present on disk.
- Action: removed generated remnants and expanded current-state tests so retired proposal
  infrastructure and migration namespaces stay absent.
- Status: fixed
- Wiki decision: no wiki source change required for generated local remnants.

## RFC36-S5-001: Stateless request envelope made explicit

- Date: 2026-05-01
- Scope: simulate, sync analyze, async analyze request contracts, demo payloads, OpenAPI inventory
- Finding: product endpoints still accepted direct inline bundles, which made it harder to add
  stateful `portfolio_id` mode without ambiguous request shapes.
- Action: added `StatelessRebalanceRequestEnvelope` and
  `StatelessBatchRebalanceRequestEnvelope`, moved demo/API request payloads under
  `stateless_input`, and added a regression test proving direct stateless bodies are rejected.
- Status: fixed
- Wiki decision: wiki endpoint certification and supported-features source updated because request
  contract truth changed.

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
