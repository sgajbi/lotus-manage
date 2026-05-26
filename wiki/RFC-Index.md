# RFC Index

## Platform RFCs that matter most here

- RFC-0066
- RFC-0067
- RFC-0071
- RFC-0072
- RFC-0073
- RFC-0082

## High-value local RFCs

- RFC-0001 to RFC-0013
  core rebalance simulation, controls, optimization, and what-if analysis foundation
- RFC-0001
  implemented deterministic DPM simulation foundation; later RFCs own current persistence,
  idempotency, supportability, and stateful sourcing layers
- RFC-0002
  implemented enterprise hardening baseline; durable idempotency and persistence are now delivered
  by later supportability RFCs rather than deferred work
- RFC-0003 to RFC-0006B
  implemented audit bundle, holdings-aware after-state, reconciliation, safety, configurable rules,
  FX dependencies, and institutional scenario matrix foundations
- RFC-0007A
  implemented contract-tightening baseline for the canonical rebalance execution surface
- RFC-0016
  idempotency replay contract
- RFC-0017
  run supportability APIs
- RFC-0018
  async operations resource
- RFC-0019
  deterministic run artifact contract
- RFC-0020
  workflow gate API and persistence
- RFC-0021
  OpenAPI hardening, request/response model separation, and current certification evidence
- RFC-0022
  policy-pack configuration model
- RFC-0023
  persistent supportability store and lineage APIs
- RFC-0028
  implemented `GET /api/v1/integration/capabilities` backend-governed capabilities contract

## Active And Recently Completed RFCs

- RFC-0036
  implemented target-state stateful `lotus-core` sourcing and duplicate endpoint consolidation

## Strategic DPM RFCs With Implemented Boundaries

These RFCs started as proposed roadmap and execution-guide material. Their supported claims now
follow the implementation-backed posture recorded in each RFC, the WTBD reintegration ledger,
certified API docs, wiki source, and canonical Workbench proof. Future scope and external-owner
dependencies remain explicit non-claims until implementation, certification, live evidence, wiki
updates, and supported-feature promotion are complete.

- RFC-0037
  strategic DPM operating-system and mandate-intelligence parent roadmap. Bounded Lotus-owned child
  realization is complete for command center, construction, proof-pack, wave, outcome,
  portfolio-memory, campaign, PM-quality, and PM copilot workspace surfaces. Broader strategic
  source-product depth remains open under RFC37-WTBD-004, even though the bounded Manage consumer
  path for lotus-core `DpmPortfolioUniverseCandidate:v1` now advances bulk-review campaign
  candidate discovery with fail-closed page completeness, source-lineage controls, and
  front-office-validated source-owned selection-basis evidence.
- RFC-0038
  implemented first DPM operating-system foundation: source-mapped mandate digital twin,
  deterministic health engine, monitoring exception taxonomy, persistence, certified mandate and
  monitoring APIs, bounded command-center summary, local manage proof, local canonical manage plus
  live core proof, wiki publication, and downstream Gateway/Workbench/platform handoff issues.
- RFC-0039
  implementation-backed manage and first-wave product foundation: advanced portfolio construction and rebalance
  alternatives now have a governed source-data and method map, manage-local construction API
  governance, a dedicated `src/core/construction/` package, pure alternative models, do-nothing
  baseline, heuristic wrapping, normalized drift/turnover metrics, conservative alternative-set
  status roll-up, a bounded method registry with explicit solver/fallback posture, pure
  tax/turnover/liquidity/cost/FX enrichment posture, `lotus-risk` concentration authority
  integration for risk-aware construction, regime-stress authority context, certified manage backend
  APIs for generating, retrieving, and selecting persisted construction alternative sets,
  Postgres-backed canonical manage proof, source-backed ESG/restriction profile consumption, and
  construction-specific Gateway/Workbench realization proof. Broader unsupported source-product
  methodology, OMS execution, order routing, and settlement remain non-claims.
- RFC-0040
  implemented pre-trade proof-pack and DPM evidence-fabric authority with durable
  JSON, Markdown summary, report-input, AI-evidence input, lineage, retention posture,
  Gateway/Workbench realization, portfolio-memory lineage, PM-quality source-event family posture,
  and canonical Postgres-backed live proof under `output/rfc0040-proof`
- RFC-0041
  rebalance-wave orchestration and CIO model-change impact is `DONE` for the manage-owned explicit
  portfolio-list wave backend authority, bounded campaign control surfaces, downstream realization,
  and no-OMS boundary posture. Source-map, platform-scaffold evidence improvement, cleanup review, wave
  domain contracts, persistence foundation, explicit affected-portfolio preview, idempotent
  durable create, durable source-check classification, ready-item simulation, item-level
  alternative selection, proof-pack linkage, approval, staging, internal operations handoff
  evidence, pre-execution cancellation, product-safe supportability diagnostics, bounded wave
  supportability telemetry,
  repository-backed search/detail/item/proof-pack/supportability read models, OpenAPI
  certification, aggregate reconciliation, hardening review, downstream Gateway/Workbench
  RFC-0098 wave realization addenda, source-owned `PM_BOOK_REVIEW` wave discovery through
  lotus-core `PortfolioManagerBookMembership:v1`, campaign-definition BFF composition, and
  Workbench launch/history rendering are complete. Global portfolio-universe campaign discovery and
  external workflow orchestration remain source-owner/external-owner promotion dependencies.
- RFC-0042
  post-trade outcome feedback loop; `DONE` for the manage backend authority after gold-standard
  tightening on 2026-05-05, with Slice 0 source-map guardrails, Slice 1 platform scaffold evidence, Slice 2 cleanup/structure
  evidence, Slice 3 pure domain comparison evidence, Slice 4 expected snapshot assembly evidence,
  Slice 5 realized source-degraded evidence, Slice 6 persistence/events evidence, Slice 7 certified
  manage API/OpenAPI evidence, Slice 8 report-input/AI-evidence handoff contracts, Slice 9
  supportability/observability diagnostics, Slice 10 Gateway/Workbench realization RFC alignment,
  Slice 11 live manage implementation proof at
  `output/rfc0042-outcome-proof/20260505-024352/`, and Slice 12 hardening proof at
  `output/rfc0042-outcome-proof/20260505-025613/`. Post-merge audit proof at
  `output/rfc0042-outcome-proof/20260505-040212/` restored the cross-RFC work-to-be-done ledger.
  WTBD audit proof at `output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/` and canonical
  Workbench evidence at `lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/`
  prove the first-wave Gateway/Workbench outcome-review product path after owning-app
  implementation. PM operating quality backend support, Gateway BFF composition, Workbench
  policy/score/fairness/review-action/summary-invocation UI, portfolio-memory lineage, and
  `lotus-ai` `pm_quality_summary.pack@v1` support-only score-run summaries are implemented.
  Unsupported execution/OMS ownership, client contact, PM ranking, HR/conduct decisions, and raw
  prompt/generated-summary retention remain explicit non-claims.
- RFC-0043
  implemented governed AI PM copilot support using `lotus-ai` without transferring domain decision
  ownership to AI. Owner-side DPM packs exist for proof-pack PM memo, wave PM memo, outcome-review
  narrative, operations handoff summary, exception summary, and PM quality summary.
  Gateway/Workbench operations-handoff, exception-summary, PM-quality summary-invocation, and
  Gateway-only `mode=copilot` workspace realization are now implemented through governed Gateway
  routes and Workbench actions. Additional future copilot product surfaces remain owner-specific
  scope and cannot claim autonomous advice, PM ranking, client contact, orders, OMS execution, raw
  prompt retention, or generated model-output retention without new owner proof.

## Removed local RFC sprawl

- RFC-0030 through RFC-0035 were deleted from the active repository documentation set. They were
  incremental test-pyramid expansion waves whose implemented test coverage is now represented by
  the current test suite and RFC-0036 evidence rather than six separate active RFC records.

## Superseded advisory scope

- Advisor-led proposal simulation, artifacts, consent, and lifecycle RFCs are no longer active
  `lotus-manage` scope. They belong in `lotus-advise`.

## Rebaselined foundation RFCs

- RFC-0001 through RFC-0007A, RFC-0021, RFC-0024, RFC-0025, and RFC-0028 were reviewed against
  current implementation evidence on 2026-05-03.
- Early MVP and pre-persistence RFCs are preserved as historical foundation layers. They should not
  be read as the current product ceiling for enterprise lotus-manage.
- RFC-0024 and RFC-0025 are complete for current lotus-manage DPM supportability and production
  cutover scope. Historical advisory migration notes remain in the RFC files for audit traceability
  only.

## Full local RFC inventory

- [docs/rfcs/README.md](../docs/rfcs/README.md)
