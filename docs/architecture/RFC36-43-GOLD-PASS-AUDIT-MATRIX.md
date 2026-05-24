# RFC36-43 Gold-Pass Audit Matrix

Date: 2026-05-24

Scope: current `lotus-manage` mainline after merge
`74bb4abc1cbfc90bee6fa1941a6b2ae511d4e858`, with Main Releasability Gate
`26358177212` green.

This is the decision register for the RFC36-43 gold-pass completion program. It does not replace
the detailed WTBD ledger in `docs/rfcs/RFC-worktobedone.md`; it summarizes the current audit
classification, required proof posture, and next implementation slices.

## Current WTBD Recount

| Control | Count | Audit conclusion |
| --- | ---: | --- |
| Total WTBD items | 59 | RFC36 through RFC42 follow-up items currently tracked in `docs/rfcs/RFC-worktobedone.md`. RFC43 is integrated through RFC37-WTBD-002 and has no standalone WTBD row in the ledger. |
| Done on merged/published Lotus-owned truth | 58 | Completed items have implementation-backed owner evidence, repo-native tests, CI proof, and wiki publication where support truth changed. |
| Partial / in progress | 0 | No WTBD row is classified as partial after the bounded RFC37-WTBD-003 front-office realization closure. |
| Remaining / open | 1 | RFC37-WTBD-004 remains open for broader strategic source-product depth and must not be closed by consumer-only work. |

## Classification Rules

| Classification | Meaning |
| --- | --- |
| `fix-now` | A bounded implementation, test, documentation, or live-proof gap exists in the current owned surface and can be addressed without changing source ownership. |
| `source-owner` | The next real improvement belongs in `lotus-core`, `lotus-risk`, `lotus-performance`, or another source owner before Manage/Gateway/Workbench can claim support. |
| `front-office-realization` | Source-owner or Manage truth exists, but Gateway/Workbench/live canonical product proof still needs to expose it. |
| `documentation-truth` | The implementation is already bounded, but README/wiki/RFC/demo material needs sharper implementation-backed language. |
| `unsupported-nonclaim` | The item is intentionally outside current Lotus support and must remain a non-claim until a source owner, external owner, or product owner implements and proves it. |

## RFC-Level Audit Matrix

| RFC | Current completeness | Correctness and tests | Live proof and docs | Gold-pass decision | Follow-up classification |
| --- | --- | --- | --- | --- | --- |
| RFC-0036 | Implemented: canonical `/api/v1` Manage execution and supportability posture, stateful sourcing envelope, mesh/source-readiness promotion, and retired alias cleanup are integrated. | Documentation tests and API/vocabulary gates protect removal of stale advisory/proposal and unversioned product surfaces. | Supported-feature, endpoint-certification, and RFC truth are current; downstream Gateway/Workbench support is merged. | Meets current first-wave standard for Lotus-owned Manage execution supportability. | `documentation-truth` only if future API mirrors drift; broader source depth remains RFC37-WTBD-004. |
| RFC-0037 | Strategic parent roadmap remains partially implemented by design. Completed child realizations cover outcome, copilot, front-office DPM realization, reporting/evidence, canonical demo story, and portfolio memory. | Current docs correctly retain RFC37-WTBD-004 as open and treat the roadmap as a boundary ledger, not a blanket support claim. | Latest bounded source-consumer improvement consumes `DpmPortfolioUniverseCandidate:v1` without closing source-product depth. | Not globally complete; completed child surfaces are bounded and implementation-backed. | `source-owner`, `front-office-realization`, and `unsupported-nonclaim` for RFC37-WTBD-004. |
| RFC-0038 | Implemented for Manage mandate digital twin, health, command-center foundation, source-context preservation, and downstream command-center realization. | Current tests protect source refs, supportability states, PM-book discovery, and documentation truth. | Canonical seed proof covers populated ready, selector-driven partial, and empty command-center posture. | Meets current first-wave standard for the implemented command-center scope. | `source-owner` for degraded/blocked fixtures and richer profile-detail source products. |
| RFC-0039 | Implemented for construction alternatives, source-authority posture, restriction/sustainability, transaction-cost, liquidity, regime-stress, lifecycle into proof/wave/report/AI, and Workbench realization. | Unit/API/source-client tests cover deterministic alternatives, method posture, source supportability, and failure handling. | Workbench construction validation and docs prove Gateway-only product support. | Meets current first-wave standard for bounded construction alternatives. | `source-owner` for future predictive execution/FX/treasury depth; `unsupported-nonclaim` for OMS and autonomous PM choice. |
| RFC-0040 | Implemented for proof packs, report input, AI evidence, source analytics, transaction-cost/scenario enrichment, decision timeline, and portfolio memory linkage. | Tests cover section states, content hashes, source refs, replay safety, boundary evidence, and malformed source contexts. | Canonical front-office proof classifies `dpm.proof_pack` as ready; report/render/archive/AI downstream support is merged. | Meets current first-wave proof-pack and evidence-fabric standard. | `source-owner` for future source-event families; `unsupported-nonclaim` for client communication execution and OMS. |
| RFC-0041 | Implemented for explicit portfolio-list waves, PM-book/CIO/risk/tactical/campaign cohorts, campaign-definition controls, maker-checker evidence, launch history, report/AI handoffs, and no-OMS boundary evidence. | Tests cover wave lifecycle, campaign definitions, assignment/action/control ledgers, fail-closed readiness, and no execution claims. | Workbench wave command center and campaign-definition surfaces are Gateway-only and validated for bounded support. | Meets current first-wave wave-orchestration standard. | `source-owner` and `front-office-realization` for richer campaign source discovery; `unsupported-nonclaim` for external workflow/OMS. |
| RFC-0042 | Implemented for outcome review, reports/archive, AI narrative, source-methodology preservation, external execution boundary, PM operating quality, and downstream realization. | Tests cover outcome evidence, source-methodology preservation, PM-quality controls, fairness/support posture, and non-use boundaries. | Gateway/Workbench product proof exists for outcome, portfolio-memory filters/facets, and PM-quality surfaces. | Meets current first-wave outcome and PM operating quality standard. | `source-owner` for future execution/OMS ingestion and additional realized methodology products; `unsupported-nonclaim` for HR/conduct/PM ranking. |
| RFC-0043 | Implemented for governed DPM workflow packs and Workbench copilot workspace through RFC37-WTBD-002. | Owner-side AI packs, Gateway invocation routes, and Workbench copilot rendering preserve review-gated support-only boundaries. | Docs explicitly prohibit raw prompt/model-output retention, autonomous decisions, PM ranking, client contact, and OMS claims. | Meets current first-wave governed copilot standard. | `front-office-realization` only for future owner-specific packs after source truth exists. |

## WTBD Slice Audit Register

| WTBD slice | Gold-pass status | Audit classification | Next action |
| --- | --- | --- | --- |
| RFC36-WTBD-001 | Done: Gateway canonical `/api/v1` Manage integration is merged. | `documentation-truth` | Keep API vocabulary mirrors current. |
| RFC36-WTBD-002 | Done: Workbench surfaces Manage action-register supportability through Gateway. | `documentation-truth` | Revalidate in canonical stack during Slice 2. |
| RFC36-WTBD-003 | Done: portfolio-level DPM operation dashboards are merged and live-proven. | `documentation-truth` | Preserve Gateway-only consumption. |
| RFC36-WTBD-004 | Done: `DpmSourceReadiness:v1` mesh promotion is complete. | `source-owner` | Future source-depth belongs to RFC37-WTBD-004. |
| RFC36-WTBD-005 | Done: current source-depth wave added bounded benchmark assignment lineage. | `source-owner` | Do not broaden into benchmark analytics without source-owner proof. |
| RFC36-WTBD-006 | Done: no compatibility alias required after downstream audit. | `unsupported-nonclaim` | Keep retired aliases absent. |
| RFC37-WTBD-001 | Done: first-wave outcome-review product path is complete. | `documentation-truth` | Revalidate cross-screen consistency in canonical evidence slice. |
| RFC37-WTBD-002 | Done: governed AI PM copilot support is complete for current packs. | `front-office-realization` | Add future packs only after owner-side evidence exists. |
| RFC37-WTBD-003 | Done: bounded front-office DPM realization is complete. | `documentation-truth` | Do not reopen unless a real source-owner or realization regression appears. |
| RFC37-WTBD-004 | Open: broader strategic source-product depth remains unclosed. | `source-owner` | Continue with bounded source-owner slices; current Core `DpmPortfolioUniverseCandidate:v1` Manage consumer slice advances but does not close it and must not be promoted as global universe ownership. |
| RFC37-WTBD-005 | Done: report/archive/evidence materialization is complete for supported proof-pack, wave, and outcome families. | `unsupported-nonclaim` | Client communication execution remains unsupported until a source owner implements it. |
| RFC37-WTBD-006 | Done: canonical DPM demo story is implementation-backed. | `documentation-truth` | Refresh evidence only after live validation passes. |
| RFC37-WTBD-007 | Done: portfolio-memory supportability is complete for Lotus-owned source events. | `source-owner` | Broader cross-app source-event search and OMS/client events need source-owner products. |
| RFC38-WTBD-001 | Done: Gateway DPM command-center composition is merged. | `documentation-truth` | Preserve Manage authority in BFF rendering. |
| RFC38-WTBD-002 | Done: Workbench command-center panels render Gateway truth. | `documentation-truth` | Revalidate UI behavior in Slice 2. |
| RFC38-WTBD-003 | Done: platform canonical seed automation covers ready, partial, and empty posture. | `source-owner` | Add degraded/blocked fixtures only when source-owner scenarios exist. |
| RFC38-WTBD-004 | Done: PM-book monitoring cohort discovery consumes Core membership. | `source-owner` | Future PM-book depth belongs in Core. |
| RFC38-WTBD-005 | Done: mandate objective, benchmark identity, review cadence, and model-change source posture are preserved. | `source-owner` | Benchmark analytics remain risk/performance/source-owner depth. |
| RFC38-WTBD-006 | Done: restriction, sustainability, cashflow, income-needs, reserve, and withdrawal evidence are preserved. | `source-owner` | Profile-detail UI and richer classifications need source-owner/product-depth work. |
| RFC38-WTBD-007 | Done: risk/performance health contexts are preserved without local methodology. | `source-owner` | New analytics methodology must land in Risk/Performance first. |
| RFC38-WTBD-008 | Done: front-office command-center product support is merged and live-proven. | `front-office-realization` | Revalidate in current canonical stack. |
| RFC39-WTBD-001 | Done: Gateway construction composition is merged. | `documentation-truth` | Keep Gateway from selecting alternatives. |
| RFC39-WTBD-002 | Done: Workbench construction lab is live-proven. | `front-office-realization` | Revalidate current UI density and source-readiness rendering. |
| RFC39-WTBD-003 | Done: first-wave construction product realization is complete. | `front-office-realization` | Revalidate construction-to-proof/wave continuity. |
| RFC39-WTBD-004 | Done: ESG/restriction-aware construction consumes Core source profiles. | `source-owner` | Do not claim automatic ESG approval or suitability. |
| RFC39-WTBD-005 | Done: risk/performance alternative enrichment preserves source-owned analytics. | `source-owner` | Richer analytics require source-owner methodology. |
| RFC39-WTBD-006 | Done: transaction-cost evidence supports observed-cost comparison. | `source-owner` | Predictive execution and market-impact modelling remain unsupported. |
| RFC39-WTBD-007 | Done: liquidity-aware construction preserves cashflow/income/reserve evidence. | `source-owner` | Financial-planning advice and funding recommendations remain unsupported. |
| RFC39-WTBD-008 | Done: external treasury/currency-overlay boundary is fail-closed. | `unsupported-nonclaim` | Runtime treasury ingestion is external-owner scope. |
| RFC39-WTBD-009 | Done: regime scenario-pack source support is first-wave implemented. | `source-owner` | CIO approval/applicability UX remains future source/product depth. |
| RFC39-WTBD-010 | Done: selected alternatives flow through proof packs, waves, reports, AI, and outcomes. | `front-office-realization` | Revalidate continuity in current canonical stack. |
| RFC40-WTBD-001 | Done: Gateway proof-pack composition is merged. | `documentation-truth` | Preserve no browser reconstruction of proof-pack sections. |
| RFC40-WTBD-002 | Done: Workbench proof-pack review UX is merged. | `front-office-realization` | Revalidate source hashes and action eligibility in Slice 2. |
| RFC40-WTBD-003 | Done: first-wave proof-pack product realization is live-proven. | `front-office-realization` | Revalidate current canonical proof-pack state. |
| RFC40-WTBD-004 | Done: proof-pack report materialization is implemented in report/render/archive. | `documentation-truth` | Keep Manage as report-input authority only. |
| RFC40-WTBD-005 | Done: AI PM memo generation over proof-pack evidence is implemented. | `unsupported-nonclaim` | Preserve no prompt construction or autonomous decision claim. |
| RFC40-WTBD-006 | Done: proof packs preserve source-owned risk/performance context. | `source-owner` | No local risk/performance methodology. |
| RFC40-WTBD-007 | Done: transaction-cost curve evidence is preserved in proof packs. | `source-owner` | No predictive execution quote or min-cost optimization claim. |
| RFC40-WTBD-008 | Done: restriction and sustainability evidence is preserved in proof packs. | `source-owner` | Security-level sustainability gaps remain pending review unless sourced. |
| RFC40-WTBD-009 | Done: scenario-pack governance/evaluation evidence is preserved. | `source-owner` | No local scenario methodology or CIO approval calculation. |
| RFC40-WTBD-010 | Done: portfolio memory links mandate, construction, proof, wave, outcome, report, AI, and archive events in bounded form. | `source-owner` | Broader source-event discovery and OMS/client events remain future source-owner scope. |
| RFC41-WTBD-001 | Done: PM-book cohort discovery consumes Core membership. | `source-owner` | Future cohort depth belongs in Core. |
| RFC41-WTBD-002 | Done: CIO model-change affected cohorts consume Core source truth. | `source-owner` | Model-change methodology remains source-owned. |
| RFC41-WTBD-003 | Done: risk-event, tactical house-view, and bounded campaign cohorts are supported. | `source-owner` | Global universe discovery and external workflow orchestration remain source/external-owner scope. |
| RFC41-WTBD-004 | Done: wave aggregate analytics preserve Risk/Performance source values. | `source-owner` | No Manage-local risk/performance calculation. |
| RFC41-WTBD-005 | Done: Gateway wave composition is merged. | `documentation-truth` | Preserve Manage wave authority. |
| RFC41-WTBD-006 | Done: Workbench wave command center is merged and live-proven. | `front-office-realization` | Revalidate current campaign/wave UI behavior. |
| RFC41-WTBD-007 | Done: first-wave wave command-center product support is complete. | `front-office-realization` | Revalidate active campaign definition and launch-history boundaries. |
| RFC41-WTBD-008 | Done: wave report materialization is implemented. | `documentation-truth` | Keep report/render/archive ownership explicit. |
| RFC41-WTBD-009 | Done: wave PM memo generation is implemented through AI/Gateway/Workbench. | `unsupported-nonclaim` | Preserve no browser prompt, no autonomous decision, and no execution claim. |
| RFC41-WTBD-010 | Done: external execution integration is bounded as fail-closed supportability. | `unsupported-nonclaim` | OMS acknowledgement, fills, settlement, and reconciliation remain unsupported. |
| RFC42-WTBD-001 | Done: Gateway outcome-review BFF is merged. | `documentation-truth` | Preserve Manage outcome authority. |
| RFC42-WTBD-002 | Done: Workbench outcome-review UX is merged and live-proven. | `front-office-realization` | Revalidate UI/API consistency. |
| RFC42-WTBD-003 | Done: first-wave outcome feedback product support is canonically proven. | `front-office-realization` | Revalidate against current stack. |
| RFC42-WTBD-004 | Done: outcome report/archive lifecycle is implemented. | `documentation-truth` | Keep Manage as bounded report-input authority. |
| RFC42-WTBD-005 | Done: outcome AI narrative/copilot flow is governed and merged. | `unsupported-nonclaim` | Preserve no prompt construction or autonomous decision claim. |
| RFC42-WTBD-006 | Done: Lotus-owned source-methodology supportability is complete for current realized families. | `source-owner` | New methodologies must land in source owners first. |
| RFC42-WTBD-007 | Done: external execution/OMS boundary is fail-closed. | `unsupported-nonclaim` | Bank-owned OMS ingestion and reconciliation remain external-owner scope. |
| RFC42-WTBD-008 | Done: PM operating quality is implemented as bounded support-only policy/score/review evidence. | `unsupported-nonclaim` | Do not claim PM ranking, protected-class inference, HR, compensation, conduct, client contact, trade approval, order routing, OMS, or execution. |

## Fix-Forward Backlog

| Priority | Backlog item | Classification | Owner | Required evidence before support claim |
| --- | --- | --- | --- | --- |
| 1 | Current canonical front-office evidence refresh across command center, construction, proof-pack, wave, campaign, portfolio memory, outcome, PM quality, and copilot panels. | `fix-now` | `lotus-workbench` plus platform QA wrapper | `npm run live:stack:up`, `npm run live:validate`, platform `Invoke-Canonical-FrontOffice-QA.ps1`, API/panel evidence, logs, metrics/traces where available, screenshots captured only after validation passes. |
| 2 | Gateway/Workbench realization of the new Core `DpmPortfolioUniverseCandidate:v1` candidate-source mode. | `front-office-realization` | `lotus-gateway`, `lotus-workbench` | BFF request preservation, source-readiness rendering, incomplete/truncated-page warnings, no caller-supplied portfolios in Core-discovery mode, focused UI tests, and live proof. |
| 3 | Broader RFC37-WTBD-004 source-product depth beyond bounded campaign candidates. | `source-owner` | `lotus-core`, `lotus-risk`, `lotus-performance`, future source owners | Source-owner contracts, producer declarations, platform catalog mirror, consumer declarations, fail-closed degraded/missing/stale behavior, contract tests, and live source proof. |
| 4 | Documentation/demo enrichment after new live evidence. | `documentation-truth` | Owning repo for changed truth | RFC Gold-Pass Assessment updates, wiki supported-feature updates, demo material tied to current evidence, wiki publication, and drift zero. |
| 5 | External workflow, client communication, OMS, fills, settlement, reconciliation, PM ranking, HR/conduct, generated-summary retention, and raw prompt storage. | `unsupported-nonclaim` | Future/external owners only | Must remain non-claims until explicit source/external-owner implementation, governance, tests, docs, and live proof exist. |

## Gold-Pass Assessment

| Assessment area | Result |
| --- | --- |
| What was truly completed | RFC36, RFC38, RFC39, RFC40, RFC41, RFC42, and RFC43 have bounded first-wave implementation-backed support claims. RFC37 is a strategic parent roadmap with all current child support claims complete except RFC37-WTBD-004 broader source-product depth. |
| Quality improvements confirmed | The current mainline preserves source ownership, Gateway-only Workbench consumption, fail-closed degraded states, lineage/source refs, deterministic evidence hashes, no-OMS/no-client-contact boundaries, and documentation tests that keep stale closure language out. |
| Debt removed | Historical advisory/proposal remnants, stale route aliases, stale vocabulary mirrors, and pre-merge closure wording are already guarded by current-state documentation tests. |
| Testing and evidence basis | Recount is protected by `test_wtbd_control_snapshot_counts_match_detailed_ledger`; RFC-specific documentation tests protect integrated Gold-Pass sections; current mainline is backed by Main Releasability Gate `26358177212`. |
| Remaining risk | The full current-stack evidence refresh requested by the user has not yet been rerun in this slice. That is the next implementation slice and must happen before new demo-ready screenshots or new front-office support claims are made. |
| Expected-standard decision | The audit ledger is production-useful as a decision register, but it does not claim the whole RFC36-43 ecosystem is beyond improvement. Remaining improvements are explicitly classified and scheduled for source-owner, front-office-realization, documentation, or unsupported-nonclaim handling. |

Wiki decision for this slice: no wiki source change is required because this file is an internal
engineering control ledger. Wiki/demo truth should change only after the canonical evidence and
product-quality slices produce new implementation-backed results.
