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

## Strategic Target-State RFCs

These RFCs are proposed roadmap and execution-guide material. They permit clean strategic API
redesign and endpoint retirement because no production downstream dependency is assumed for the
revamp surface. They become supported product claims only after implementation, certification, live
evidence, and supported-feature promotion.

- RFC-0037
  proposed DPM operating-system and mandate-intelligence roadmap intended to make
  `lotus-manage` the management-side crown jewel of the Lotus ecosystem, with the 15 target
  capability themes explicitly accounted for as implementation slices or dependent RFCs
- RFC-0038
  implemented first DPM operating-system foundation: source-mapped mandate digital twin,
  deterministic health engine, monitoring exception taxonomy, persistence, certified mandate and
  monitoring APIs, bounded command-center summary, local manage proof, local canonical manage plus
  live core proof, wiki publication, and downstream Gateway/Workbench/platform handoff issues.
- RFC-0039
  implementation-backed manage foundation: advanced portfolio construction and rebalance
  alternatives now have a governed source-data and method map, manage-local construction API
  governance, a dedicated `src/core/construction/` package, pure alternative models, do-nothing
  baseline, heuristic wrapping, normalized drift/turnover metrics, conservative alternative-set
  status roll-up, a bounded method registry with explicit solver/fallback posture, pure
  tax/turnover/liquidity/cost/FX enrichment posture, `lotus-risk` concentration authority
  integration for risk-aware construction, regime-stress authority context, certified manage backend
  APIs for generating, retrieving, and selecting persisted construction alternative sets,
  Postgres-backed canonical manage proof, explicit ESG/restriction deferral, and
  construction-specific Gateway/Workbench realization requirements. Full product-surface support is
  not claimed until Gateway and Workbench implement and live-prove the downstream journey.
- RFC-0040
  implemented manage-backend pre-trade proof-pack and DPM evidence-fabric authority with durable
  JSON, Markdown summary, report-input, AI-evidence input, lineage, retention posture,
  Gateway/Workbench realization RFC alignment, canonical Postgres-backed live proof under
  `output/rfc0040-proof`, and no full product-surface claim until downstream implementation is
  complete
- RFC-0041
  rebalance-wave orchestration and CIO model-change impact is `DONE` for the manage-owned explicit
  portfolio-list wave backend authority. Source-map, platform-scaffold evidence improvement, cleanup review, wave
  domain contracts, persistence foundation, explicit affected-portfolio preview, idempotent
  durable create, durable source-check classification, ready-item simulation, item-level
  alternative selection, proof-pack linkage, approval, staging, internal operations handoff
  evidence, pre-execution cancellation, product-safe supportability diagnostics, bounded wave
  supportability telemetry,
  repository-backed search/detail/item/proof-pack/supportability read models, OpenAPI
  certification, aggregate reconciliation, hardening review, and downstream Gateway/Workbench
  RFC-0098 wave realization addenda are complete for explicit portfolio-list waves. PM-book/CIO automatic cohort
  discovery is deferred until source-owning products are proven. Full Gateway/Workbench product
  support remains proposed until downstream implementation and canonical front-office proof are
  complete.
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
  `output/rfc0042-outcome-proof/20260505-040212/` restored the cross-RFC work-to-be-done ledger,
  added RFC-0042 remaining-work ownership, reran live manage proof, and passed canonical
  front-office validation for `PB_SG_GLOBAL_BAL_001` without promoting downstream
  Gateway/Workbench outcome-review UX. Full Gateway/Workbench product support remains downstream
  until implemented and canonically proven in the owning apps
- RFC-0043
  proposed governed AI PM copilot roadmap using `lotus-ai` without transferring domain decision
  ownership to AI

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
