# RFC-0040 Source Map And Gap Analysis

This document is the Slice 0 evidence map for RFC-0040. It records how the first
`DpmPreTradeProofPack` implementation should use existing `lotus-manage` foundations, which
source-owning apps must remain authoritative, which sections can be generated in the first manage
implementation wave, and which gaps must stay visible instead of being hidden behind placeholders.

The rule for RFC-0040 is strict: no proof-pack section may claim `READY` unless the fact, metric,
source ref, hash, or supportability state is backed by the owning app or by deterministic
`lotus-manage` evidence. Missing source truth must produce `DEGRADED`, `BLOCKED`,
`PENDING_REVIEW`, or `NOT_APPLICABLE` with reason codes.

## Slice 0 Result

| Slice 0 requirement | Result |
| --- | --- |
| Existing run artifacts, supportability, lineage, workflow, mandate health, monitoring, and construction alternatives reviewed | Current evidence is mapped below from RFC-0017, RFC-0019, RFC-0020, RFC-0023, RFC-0036, RFC-0038, and RFC-0039 implementation artifacts. |
| Section-to-source map complete | The first-wave section map covers every RFC-0040 proof-pack section and records owner, evidence, first implementation posture, and missing-source behavior. |
| Minimum viable first implementation confirmed | The first implementation must generate all required sections, but sections without source-backed values remain explicit degraded or not-applicable sections rather than omitted fields. |
| Cross-app gaps identified | Required and deferred cross-app gaps are listed by owning repository with expected contract, tests, and proof. |
| Existing RFC ownership checked | RFC-0037 defines the strategic DPM operating system and mentions proof packs, but RFC-0040 is the first owning execution RFC for the `DpmPreTradeProofPack` artifact. RFC-0041 through RFC-0043 depend on it. |
| Downstream conflicts identified | Existing Gateway and Workbench command-center RFCs mention proof-pack posture, and Gateway RFC-0098 currently misattributes proof-pack ownership to `lotus-report`; that must be corrected in the downstream realization slice after manage contracts stabilize. |

## Current Manage Foundations

| Foundation | Current implementation evidence | RFC-0040 reuse posture |
| --- | --- | --- |
| Deterministic run artifact | `src/core/rebalance_runs/artifact.py`, `GET /api/v1/rebalance/runs/{rebalance_run_id}/artifact`, ADR-0005 | Reuse as direct-run source evidence and one source hash input; do not treat the derived artifact as the proof pack itself. |
| Run supportability and lookup | `src/core/rebalance_runs/service.py`, `src/api/routers/rebalance_runs.py`, support bundle routes | Reuse persisted run result, correlation id, idempotency key, operation refs, and supportability state. |
| Workflow gates and reviewer decisions | `src/core/common/workflow_gates.py`, `src/core/rebalance_runs/workflow.py`, workflow API routes | Reuse for approval requirements, decision timeline, and operations handoff. |
| Lineage lookup | `src/core/rebalance_runs/repository.py`, lineage routes, RFC-0023 | Reuse run, correlation, idempotency, and operation lineage; proof-pack-specific lineage refs still need Slice 5 persistence. |
| Stateful core sourcing | `src/infrastructure/core_sourcing/client.py`, `src/core/dpm_source_context.py` | Reuse source product refs for mandate, target, eligibility, tax lots, market-data coverage, and readiness. |
| Mandate digital twin and health | `src/core/mandates.py`, `src/core/mandate_repository.py`, `src/api/services/mandate_service.py` | Reuse mandate context, health dimensions, monitoring exceptions, command-center state, and source gaps. |
| Construction alternatives and selection | `src/core/construction/`, `src/api/services/construction_service.py`, `src/infrastructure/construction/` | Reuse selected alternative, method status, objective and constraint traces, comparison metrics, and actor-attributed selection. |
| Hash helper | `src/core/common/canonical.py` | Reuse canonical JSON and SHA-256 helpers; extend to proof-pack body, section, source, report-input, and AI-evidence hashes. |
| OpenAPI governance | `scripts/openapi_quality_gate.py`, `scripts/api_vocabulary_inventory.py`, OpenAPI certification tests | Reuse for proof-pack endpoint certification; add proof-pack endpoints to certification matrix only when Slice 6 implements APIs. |

## First-Wave Proof-Pack Section Map

| Section | Source authority | Available implementation evidence | First implementation posture | Missing-source behavior |
| --- | --- | --- | --- | --- |
| `decision_summary` | `lotus-manage` | Rebalance run status/result, selected alternative, actor reason | Generate in manage from source run or selection. | `DEGRADED` when actor reason is absent; `BLOCKED` when no source run or selected source exists. |
| `mandate_context` | `lotus-manage` + `lotus-core` | Mandate twin, mandate binding, model target lineage | Use refreshed mandate twin when available; include field gap codes. | `BLOCKED` when mandate identity is missing; `DEGRADED` for fallback policy fields. |
| `source_readiness` | `lotus-core` source products, manage integration | `DpmSourceReadiness:v1`, market-data coverage, source supportability | Preserve source readiness state and product lineage. | Critical missing holdings/model/price/FX becomes `BLOCKED`; optional stale or partial families become `DEGRADED`. |
| `before_state` | `lotus-core` or caller request | Run artifact before summary, portfolio snapshot, request hash | Capture summarized holdings/allocation metadata and snapshot refs, not unsafe raw payloads. | `BLOCKED` when no portfolio state exists. |
| `target_state` | `lotus-core` model target or caller request | Model portfolio target, generated target weights, request hash | Capture model id/version, target summary, and source posture. | `DEGRADED` for caller-supplied-only target; `BLOCKED` if required target is absent. |
| `selected_alternative` | `lotus-manage` RFC-0039 | Alternative set, selected alternative, method status, objective and constraint traces | `READY` when selected alternative and set are persisted and selection belongs to set. | `DEGRADED` for direct-run proof packs with no alternative; `BLOCKED` for invalid selected alternative linkage. |
| `trade_intents` | `lotus-manage` | Run result intents and alternative `intent_ids` | Capture intended trades and FX/funding intents only as pre-trade intent evidence. | `BLOCKED` when intents cannot reconcile to after-state in trade-generating paths. |
| `after_state` | `lotus-manage` simulation | Run artifact after summary and result status | Capture simulated after-state allocation/cash summary. | `BLOCKED` when simulation failed or after-state is absent. |
| `drift_impact` | `lotus-manage` | Construction comparison metrics and run diagnostics | Use alternative metrics where present; derive only from existing run result/diagnostics otherwise. | `DEGRADED` when model/benchmark evidence is incomplete. |
| `risk_impact` | `lotus-risk` | Current manage risk-authority concentration seam for RFC-0039 | Consume risk context or mark unavailable; no local risk methodology. | `DEGRADED` until broader risk enrichment is implemented; `BLOCKED` only if policy requires risk approval and authority is missing. |
| `performance_context` | `lotus-performance` | No RFC-0040-specific manage integration yet | First wave may include explicit unavailable/degraded section. | `DEGRADED` until performance benchmark context is consumed from performance authority. |
| `tax_impact` | `lotus-core` tax lots + manage tax-aware allocation | Tax lots from core, tax-aware sell allocation diagnostics | Capture lot supportability and realized gain/loss diagnostics when source-backed. | `DEGRADED` when lots or tax budget are absent; do not infer jurisdiction rules. |
| `turnover_and_cost` | `lotus-manage` + `lotus-core` `TransactionCostCurve:v1` | Turnover controls, comparison metrics, and observed booked-fee transaction-cost evidence when stateful core sourcing returns it | Capture turnover, trade count, labelled estimated cost if present, and source-owned observed cost supportability, evidence window, missing securities, source hash, and bounded curve points. | `DEGRADED` when authoritative transaction-cost curve is absent; do not treat observed cost evidence as a predictive quote or optimization model. |
| `liquidity_and_cash` | `lotus-manage` settlement engine + core cash/eligibility | Settlement awareness, cash summary, liquidity context | Capture funding, cash buffer, settlement, and liquidity reason codes. | `BLOCKED` for funding deficits; `PENDING_REVIEW` for policy breach; `DEGRADED` for incomplete cashflow forecast. |
| `fx_funding_plan` | `lotus-core` market-data coverage + manage FX diagnostics | FX coverage, FX intent diagnostics | Capture required pairs, base currency, and funding posture. | `BLOCKED` for missing required FX pair; `DEGRADED` for stale optional coverage. |
| `currency_overlay_evidence` | Manage policy context + FX source | Currency-overlay authority context in RFC-0039 | Capture policy id, eligible currencies, hedge bands, and supportability where provided. | `DEGRADED` until treasury hedge products/forward curves exist. |
| `scenario_and_regime_evidence` | `lotus-risk` / CIO authority | Regime stress authority context accepted by manage; `RegimeScenarioPackEvaluation:v1` now supplies first-wave scenario-pack evaluation for RFC-0039 construction | Preserve selected-alternative source-backed scenario pack metadata, supportability state, reason codes, source refs, and canonical `regime_stress_context` hash; also preserve generation-time direct source-owned `regime_stress_context` when selected-alternative evidence is absent. | `DEGRADED` when no selected-alternative or direct source-owned scenario context is present; optional per-security contribution rows and v3 scenario/contribution methodology are source-owned in `lotus-risk`; approval evidence remains future source depth. |
| `eligibility_and_restrictions` | `lotus-core` eligibility/restriction authority | Instrument eligibility product, restriction codes | Capture buy/sell eligibility, shelf status, restriction reason codes. | `DEGRADED` for missing client restriction profile; no ESG/restriction-ready claim. |
| `sustainability_controls` | Future sustainability authority | No source-backed sustainability profile currently | Include `NOT_APPLICABLE` or `DEGRADED` with explicit deferral reason. | `DEGRADED` until sustainability preference/profile source exists. |
| `rule_results` | `lotus-manage` policy/rule engine | Run artifact rule outcomes and compliance diagnostics | Capture pass/warn/block outcomes and reason codes. | `BLOCKED` when mandatory rules cannot be evaluated. |
| `approval_requirements` | `lotus-manage` workflow gates | Workflow status, gate decision, reviewer decisions | Capture required approvals, latest decision, and pending review posture. | `PENDING_REVIEW` when approval is required and incomplete. |
| `operations_handoff` | `lotus-manage` | Run status, operation refs, supportability, workflow state | Capture execution-not-order state, blocked actions, operator refs. | `DEGRADED` when operation refs are incomplete. |
| `decision_timeline` | Manage workflow/run/selection/monitoring events | Run created, selection event, workflow decisions, monitoring exceptions | Build ordered proof-pack-local timeline from existing event sources. | `BLOCKED` if selected source event is missing; optional events are `DEGRADED`. |
| `lineage` | All source systems; manage aggregation | Source product lineage, run lineage, alternative ids, correlation ids | Capture source refs and hashes without raw payloads. | `BLOCKED` when source run identity is missing. |
| `supportability` | `lotus-manage` | Section states, run supportability, source supportability | Always generated and never omitted. | Overall state follows worst material section state. |
| `reporting_refs` | Manage report-input adapter; `lotus-report` consumer later | Slice 7 now provides typed proof-pack report input. | Generate typed manage-owned report input and append evidence refs when requested. | `READY` for manage adapter; no report-service materialization claim until report app supports it. |
| `ai_refs` | Manage AI-evidence adapter; `lotus-ai` consumer later | Slice 7 now provides bounded AI evidence input. | Generate bounded evidence input with forbidden-field and forbidden-action guardrails. | `READY` for manage adapter; no AI memo claim until RFC-0043. |

## Minimum Viable First Implementation

The first manage implementation must generate a complete section set for both source types:

1. selected RFC-0039 alternative,
2. direct rebalance run.

Required first-wave behavior:

1. include every RFC-0040 section in the proof pack,
2. carry source refs, owner, supportability, reason codes, redaction policy, and generated timestamp
   for every section,
3. mark unavailable risk, performance, report, AI, sustainability, and unsupported source-product
   sections truthfully instead of omitting them,
4. persist the proof pack immutably before exposing report or AI handoff refs,
5. produce deterministic hashes from canonical JSON and exclude only the hash fields being
   calculated,
6. treat selected alternative proof packs as stronger than direct-run proof packs because they carry
   method status, objective trace, constraint trace, comparison metrics, and actor selection reason,
7. keep Gateway and Workbench support claims out of `lotus-manage` supported-feature material until
   downstream RFCs are implemented and live-proven.

## Cross-App Dependency Matrix

| Capability or gap | Owning repo | Required for RFC-0040 completion? | Expected contract/change | Required tests and proof | Slice 0 decision |
| --- | --- | --- | --- | --- | --- |
| Portfolio, mandate, target, eligibility, tax lots, market-data coverage, source readiness | `lotus-core` | Yes for source-backed canonical proof | Existing RFC-087 source products and readiness APIs | Use existing core/manage live proof; add core changes only if proof-pack generation exposes missing mandatory field. | Already sufficient for first-wave proof; verify in Slice 9 live evidence. |
| Mandate twin, health, monitoring exceptions, command center | `lotus-manage` | Yes | Existing RFC-0038 APIs and repositories | Reuse with proof-pack builder tests and later API proof. | Implemented foundation; integrate in Slice 3. |
| Construction alternatives, selection, method traces | `lotus-manage` | Yes for selected-alternative proof packs | Existing RFC-0039 APIs and repositories | Builder tests must prove selected alternative belongs to the set and traces are preserved. | Implemented foundation; integrate in Slice 3. |
| Broader risk enrichment beyond concentration | `lotus-risk` | Not first-wave blocker, but needed for richer gold outcome claims | Risk-owned proof-pack enrichment or existing risk analytics contract consumed by manage/gateway | Risk repo tests and manage degraded-state tests if not implemented. | Defer broader risk enrichment unless Slice 3/9 evidence shows risk section is mandatory for the supported claim. |
| Performance benchmark context | `lotus-performance` | Not first-wave blocker, but needed before performance-aware proof-pack support claim | Performance-owned benchmark/return/attention context for DPM proof packs | Performance contract tests and manage adapter tests when added. | Explicitly deferred for first manage implementation; section remains degraded. |
| Authoritative transaction-cost curve | `lotus-core` source authority consumed by `lotus-manage` | Yes for RFC-0040 proof-pack evidence and RFC-0039 `COST_AWARE` comparison; no for predictive execution quotes, market-impact modelling, venue routing, or true min-cost execution optimization | `TransactionCostCurve:v1` through `/integration/portfolios/{portfolio_id}/transaction-cost-curve` | Core source-owner tests plus manage core-sourcing, construction, and proof-pack tests. | Implemented for proof-pack evidence preservation and source-observed cost-aware construction comparison. Predictive execution methodology remains future source-owner work. |
| Sustainability preference and client restriction profile | `lotus-core` or dedicated client governance source | No for first wave; yes before ESG/restriction-ready support | `ClientRestrictionProfile:v1`, `SustainabilityPreferenceProfile:v1` | Core/source tests, manage supportability tests, live proof. | Deferred; no sustainability support claim. |
| Scenario pack authority | `lotus-risk` / CIO authority | Not required for original RFC-0040 closure; first-wave source now exists for selected RFC-0039 alternatives and direct proof-pack enrichment payloads | `RegimeScenarioPackEvaluation:v1` through `POST /analytics/risk/regime-scenario-pack/evaluate` or caller-supplied source-owned `regime_stress_context` at proof-pack generation time | Risk tests, manage adapter tests, and manage proof-pack preservation tests. | Proof packs preserve the selected alternative's source-backed scenario context and can preserve a direct source-owned scenario context when the selected alternative lacks it. `lotus-risk` PR #116 adds optional reconciled per-security contribution rows to the source product; CIO approval/applicability evidence remains future depth. |
| Typed report input consumer | `lotus-report` | Manage must produce input; report consumption may be separate unless required by Slice 7 | Report-side consumer contract for `DpmProofPackReportInput` if report generation is claimed | Report contract/API tests plus manage adapter tests. | Manage adapter required; report app changes only if report consumption is promoted. |
| Typed AI evidence consumer | `lotus-ai` | Manage must produce guarded evidence; AI memo belongs to RFC-0043 | AI workflow-pack or evidence ingestion contract for proof-pack memo | AI guardrail/eval tests plus manage forbidden-field tests. | Manage adapter required; AI generation deferred to RFC-0043. |
| Gateway proof-pack composition | `lotus-gateway` | Required before front-office product outcome | Gateway RFC must consume manage proof-pack APIs and preserve section states, hashes, refs, report/AI refs | Gateway contract/OpenAPI/live proof | Create or tighten downstream RFC in Slice 8. Existing Gateway RFC-0098 has ownership conflict to fix. |
| Workbench proof-pack review UX | `lotus-workbench` | Required before front-office product outcome | Workbench RFC must consume Gateway only and render section matrix/evidence drawer/actions | Workbench unit, browser, accessibility, canonical live screenshots | Create or tighten downstream RFC in Slice 8. Existing Workbench RFC-0098 should be adjusted after Gateway truth is stable. |
| Platform comparable evidence conventions | `lotus-platform` | Yes for repeatable cross-repo proof if current automation is insufficient | Evidence manifest/scaffold/check improvements if needed | Platform unit/contract tests | Decide in Slice 1 after comparing current platform automation to RFC-0040 evidence needs. |

## Downstream RFC Conflict To Resolve Later

Current `lotus-gateway/docs/rfcs/RFC-0098-dpm-command-center-composition-contract.md` says
`lotus-report` owns proof-pack generation and proof-pack lifecycle in multiple places. RFC-0040
now makes `lotus-manage` the authority for `DpmPreTradeProofPack`, while `lotus-report` owns report
materialization from typed proof-pack report input.

Required later action:

1. Slice 8 must create or tighten the Gateway proof-pack realization RFC so Gateway consumes
   `lotus-manage` proof-pack APIs and does not reconstruct sections.
2. The Gateway RFC must replace old `lotus-report` proof-pack ownership language with
   `lotus-manage` proof-pack authority and `lotus-report` report materialization ownership.
3. Workbench RFC updates must follow the stabilized Gateway contract and preserve Gateway-only
   consumption.

This is not patched in Slice 0 because the manage API contracts, examples, hashes, and live proof
do not exist yet. Changing downstream implementation RFCs before manage contract proof would be
speculative.

## Implementation Order Confirmation

RFC-0040 should proceed in the RFC-defined order:

1. Slice 1: classify platform/scaffold gaps before creating manage-local evidence conventions.
2. Slice 2: clean proof-pack-adjacent structure only where it reduces duplication or stale
   terminology.
3. Slice 3: implement domain models and pure proof builder from direct runs and selected
   alternatives.
4. Slice 4: add deterministic Markdown after section shape is stable.
5. Slice 5: add immutable persistence, refs, events, retention, and repository parity.
6. Slice 6: expose certified APIs after domain, rendering, and persistence contracts are stable.
7. Slice 7: add report and AI handoff adapters.
8. Slice 8: create/tighten Gateway and Workbench realization RFCs from implemented manage proof.
9. Slice 9 through Slice 11: live proof, hardening, documentation, PR, wiki, and branch hygiene.

Do not start Slice 3 implementation before Slice 1 and Slice 2 are completed because platform
evidence conventions and local structure affect the proof-pack module boundaries.
