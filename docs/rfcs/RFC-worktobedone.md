# RFC Work To Be Done Ledger

This ledger records implementation-backed remaining work after an RFC is closed or partially
delivered. It is not an aspirational backlog and it must not be used to claim support for unfinished
features.

Purpose:

1. preserve what remains after an RFC without weakening the RFC closure result,
2. explain why each remaining item was not implemented in the completed wave,
3. assign the owning application or source authority,
4. define the conditions that must be true before implementation starts,
5. define proof and documentation requirements for promoting a feature to supported status.

Governance rules:

1. no item in this ledger is a supported-feature claim,
2. each item must identify the owning repository or explicitly state that ownership is not yet
   established,
3. source-data gaps must be fixed in the source-owning application, not locally cloned in
   `lotus-manage`,
4. Gateway and Workbench items must consume domain-authoritative services through the governed
   product path,
5. promotion requires implementation, tests, OpenAPI/API certification where applicable, live or
   canonical evidence, README/wiki/supported-features updates, PR merge, wiki publication, and branch
   cleanup.

Wiki decision for this ledger update:

The WTBD ledger is now used as a product-readiness control surface, not only an engineering
planning artifact. `wiki/Supported-Features.md` is updated in this slice with an
implementation-backed DPM product-readiness view, integration diagram, and next-priority WTBD
sequence suitable for developers, operations, business stakeholders, sales/pre-sales, and client
demo preparation. The wiki remains careful not to promote unfinished WTBDs as supported features.

## Completed WTBD RFC Reintegration Index

Completed and audited WTBD truth belongs in the original RFC that introduced the business change.
This ledger remains the control register for residual, partial, deferred, or source-owner work; it
must not become a second durable narrative for completed scope. The following completed WTBD groups
have been moved back into their owning RFCs as post-closure integration audits, with the WTBD ledger
retained only as evidence index and sequencing control.

| Owning RFC | Completed WTBD truth now integrated into the RFC | Ledger boundary that remains here |
| --- | --- | --- |
| RFC-0036 | RFC36-WTBD-001 through RFC36-WTBD-003 and RFC36-WTBD-006 are incorporated into `docs/rfcs/RFC-0036-dpm-stateful-core-sourcing-and-endpoint-consolidation.md`. | RFC36-WTBD-004 and RFC36-WTBD-005 remain source-product and upstream-depth controls. |
| RFC-0037 | RFC37-WTBD-005, RFC37-WTBD-006, and the bounded RFC37-WTBD-001 first-wave outcome-review realization are incorporated into `docs/rfcs/RFC-0037-dpm-operating-system-and-mandate-intelligence.md`. | RFC-0037 remains a strategic parent roadmap; broader outcome-learning loops, full portfolio memory, source-owner depth, execution, PM scoring, and client-communication ownership stay outside the completed parent-roadmap claims. |
| RFC-0038 | RFC38-WTBD-001 through RFC38-WTBD-006 and RFC38-WTBD-008 are incorporated into `docs/rfcs/RFC-0038-mandate-digital-twin-health-and-command-center.md`. | RFC38-WTBD-007 remains the broader risk/performance health-enrichment control. |
| RFC-0039 | RFC39-WTBD-001 through RFC39-WTBD-004, RFC39-WTBD-006, RFC39-WTBD-010, and the bounded first-wave RFC39-WTBD-007 and RFC39-WTBD-009 results are incorporated into `docs/rfcs/RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md`. | RFC39-WTBD-005 remains a broader risk/performance control. RFC39-WTBD-008 is partial for external treasury source-product contract boundaries, active fail-closed hedge-readiness, currency-exposure, hedge-policy, eligible-hedge-instrument, and FX forward-curve posture merged in `lotus-core`, platform mirror truth, and Manage consumption of the unavailable postures; runtime external treasury ingestion remains pending. |
| RFC-0040 | RFC40-WTBD-001 through RFC40-WTBD-010 are incorporated into `docs/rfcs/RFC-0040-pre-trade-proof-pack-and-evidence-fabric.md`, including the portfolio-memory source-event family posture that lists supported manage/report/AI/archive families, explicitly defers OMS execution, supports bounded PM quality score-run and review-action lineage for persisted score runs whose source-owned Core PM-book membership evidence includes the requested portfolio, and supports generation-time direct proof-pack enrichment from source-owned `RegimeScenarioPackEvaluation:v1` context when the selected alternative does not already carry regime-stress authority. | Source-owned scenario governance posture is now bounded and implementation-backed through `lotus-risk` and preserved by `lotus-manage`; future OMS execution products, broader external CIO workflow UX, and richer score-run analytics remain separate product depth rather than hidden manage proof-pack or portfolio-memory gaps. |
| RFC-0041 | RFC41-WTBD-001, RFC41-WTBD-002, RFC41-WTBD-004 through RFC41-WTBD-009, the bounded risk-event source-owner plus manage-consumer result for RFC41-WTBD-003, the bounded tactical house-view source-owner plus manage-consumer result, the bounded manage-owned `BulkReviewCampaignMembership:v1` result, persisted Manage-owned `BulkReviewCampaignDiscovery:v1` over campaign definitions, Manage-owned campaign-definition retirement/supersession/lifecycle-event projection, preview-readiness checks, launch packages, durable campaign-definition launch with append-only launch history, first-class launch-history audit pages, append-only campaign approval-decision evidence, append-only campaign assignment/escalation actions, controlled campaign assignment-task lifecycle evidence, append-only maker-checker control evidence, bounded campaign operating queue, bounded campaign approval-attention inbox, bounded campaign workflow board, bounded campaign assignment plan, bounded campaign workflow-automation readiness, Gateway campaign-definition BFF composition, and Workbench active campaign-definition list plus launch/history rendering are incorporated into `docs/rfcs/RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md`. | RFC41-WTBD-003 remains partial only for global portfolio-universe campaign discovery and external workflow orchestration beyond Manage-side task readiness. Tactical house-view source ownership is implemented in `lotus-advise`: it owns `TacticalHouseViewAffectedCohort:v1` for governed bank-authored house-view instructions and caller-supplied source-backed candidates. `lotus-manage` consumes that product for bounded `TACTICAL_HOUSE_VIEW` wave preview/create without recomputing advisory, house-view, holdings, exposure, alignment, or mandate facts. `lotus-manage` also owns and implements the first `BulkReviewCampaignMembership:v1` DPM operating campaign envelope with optional approval, expiry, access-purpose, source-ref, actor-entitlement governance evidence, persisted `BulkReviewCampaignDefinition:v1` definitions over source-backed candidate sets, `GET /api/v1/rebalance/waves/campaign-discovery` for bounded persisted campaign discovery, `GET /api/v1/rebalance/waves/campaign-operating-queue` for launch-ready/attention-required/closed queue posture, `GET /api/v1/rebalance/waves/campaign-approval-inbox` for read-only approval-complete/approval-required/approval-incomplete/expiry-attention/entitlement-attention/closed posture, `GET /api/v1/rebalance/waves/campaign-workflow-board` for read-only actor-aware next-action posture, `GET /api/v1/rebalance/waves/campaign-assignment-plan` for read-only actor routing/escalation/SLA posture, `GET /api/v1/rebalance/waves/campaign-workflow-automation` for read-only Manage-side task automation readiness, `POST`/`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions` for append-only assignment, reassignment, escalation, de-escalation, and resolution posture evidence, `POST`/`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks` for controlled assignment task state, `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions` for append-only task transition evidence, `POST`/`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls` for append-only actor-separation control evidence, `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/retire` to keep retired definitions auditable while blocking new preview/create use, `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede` to keep replaced definitions auditable while pointing to an active replacement version/hash, `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/lifecycle-events` for bounded lifecycle audit projection, `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness` for fail-closed supportability, `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package` for bounded preview/create request drafts and idempotency guidance, `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch` for deterministic durable wave launch only when readiness is `READY`, `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-history` for paged append-only launch audit evidence, and `POST`/`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions` for append-only approval posture evidence. Source apps still own the underlying facts and calculated reasons. `lotus-gateway` PR #231 (`ea6c036`, Main Releasability Gate `25989936539`) preserves bounded campaign-definition lifecycle-events, launch-history, launch-package, durable launch, and campaign-discovery BFF payloads without local cohort, readiness, idempotency, order, or OMS calculation. `lotus-workbench` PR #244 (`31ea877`, Main Releasability Gate `25989936388`) renders the Gateway-only READY-gated launch and paged launch-history/empty-state/no-order/no-OMS boundaries without computing cohort membership or readiness locally. RFC41-WTBD-010 remains deferred execution scope with no supported claim. |
| RFC-0042 | RFC42-WTBD-001 through RFC42-WTBD-005 and the bounded RFC42-WTBD-008 PM operating quality policy administration, preview, persisted score-run lifecycle, governance controls, optional source-owned PM-book materialization, bounded source-segment fairness-analysis preview/create/read/list lifecycle, bounded immutable review-action preview/create/read/list ledger, bounded portfolio-memory score-run and review-action lineage projection, Gateway policy/score-run/fairness-analysis/support-summary BFF composition, AI-owned support-only PM quality summary pack, and Gateway/Workbench PM-quality policy/score-run/fairness-analysis/support-summary product realization are incorporated into `docs/rfcs/RFC-0042-post-trade-outcome-feedback-loop.md`. | RFC42-WTBD-006 remains partial source-family work; RFC42-WTBD-007 is now partial for Lotus-side fail-closed execution/OMS boundary truth while bank-owned OMS ingestion remains unsupported. PM quality does not claim PM ranking, protected-class inference, HR, compensation, conduct enforcement, client contact, trade approval, order routing, OMS, execution, persisted summary history, review-action BFF/UI realization, approval workflow beyond immutable review actions, or autonomous decisions. |
| RFC-0043 | The bounded DPM workflow-pack result from RFC37-WTBD-002 is incorporated into `docs/rfcs/RFC-0043-governed-ai-pm-copilot-for-dpm.md`, now including the merged owner-side operations handoff summary, exception summary, and PM quality summary packs plus first-wave Gateway/Workbench invocation surfaces where implemented. | RFC-0043 remains partial until the full copilot workspace and any additional product-surface requirements are implemented by their owners. |

## Mainline WTBD Control Snapshot

Snapshot basis: the 2026-05-20 clean mainline after `lotus-manage` PR #329
(`e03be66c58e881024938eb5a63f4fb373e914c00`) incorporated bounded
`PM_QUALITY_REVIEW_ACTION` portfolio-memory projection. The latest verified Main Releasability
Gate is GitHub Actions run `26161414570`. Earlier classification updates
reclassified RFC39-WTBD-008 as partial because external treasury contracts, active fail-closed
source postures, and Manage consumption are merged while runtime external treasury ingestion
remains pending. The classification also normalizes RFC37-WTBD-002, RFC37-WTBD-003, and
RFC37-WTBD-007 as partial, matching the detail rows: bounded first-wave product paths, cross-app
product surfaces, and portfolio-memory lineage exist, while the full copilot workspace, broader
front-office realization, full portfolio memory, OMS execution/fill/settlement projection,
PM scoring, and remaining source-owner depth remain future scope. The current classification is
59 total WTBD items: 45 done on merged/published truth, 8 partial or in progress, and
6 remaining/open. The post-PR #329 recount keeps the same classification: the Manage backend
review-action ledger and portfolio-memory projection are supported, while Gateway/Workbench
review-action realization remains downstream work and is not counted as hidden completed scope.
`lotus-performance` PR #168 (`781415f`, wiki `6fb7209`) advances the existing
RFC42-WTBD-006 partial row with source-owned stateless MWR source-preconverted FX evidence, but it
does not move the count because stateful per-input FX evidence, broader FX methodology, predictive
execution, and OMS remain unfinished.
Earlier source slices include the RFC40-WTBD-009
selected-alternative regime-scenario proof-pack preservation slice, the RFC-0043 owner-side AI
workflow-pack truth reintegration slice, the RFC41-WTBD-003 manage risk-event consumer slice, the
RFC38-WTBD-006 source-backed mandate-health consumption slice, the RFC38-WTBD-008 command-center
product closure, the RFC38-WTBD-005 mandate objective/benchmark/review source-consumption slice,
and the RFC39-WTBD-010 construction lifecycle audit. RFC37-WTBD-005 now has the supported
proof-pack, rebalance-wave, and outcome-review report, render, archive, Gateway/Workbench posture,
and AI-evidence handoff truth moved into RFC-0037 as a completed parent-roadmap closure result.
RFC36-WTBD-006 is now closed as a no-migration-required conditional item after the cross-repo audit
found no active consumer dependency that justifies restoring retired manage proposal routes; the
only stale durable truth found was the platform API vocabulary mirror, which `lotus-platform`
PR #316 refreshed and validated. RFC41-WTBD-003 now has
`lotus-risk:RiskEventAffectedCohort:v1` source ownership, the platform mesh mirror, and the
`lotus-manage` `RISK_EVENT` wave preview/create consumer implemented, validated, merged to
`main`, and wiki-published. RFC38-WTBD-006 now has `lotus-manage` first-wave mandate-health
consumption of `ClientRestrictionProfile:v1`, `SustainabilityPreferenceProfile:v1`, and
`PortfolioCashflowProjection:v1` merged, CI-green, and wiki-published. RFC39-WTBD-010 now has
bounded selected-alternative lifecycle support across manage proof packs, wave selection and
proof-pack linkage, report inputs, AI evidence inputs, and outcome expected-snapshot assembly.
The canonical DPM command-center seed still proves populated source-ready `ready`,
selector-driven `partial`, and empty-date `empty` postures while `lotus-manage` exposes bounded
ready/degraded/blocked source-readiness states for downstream consumers. RFC40-WTBD-007 adds
source-owned observed transaction-cost evidence through `TransactionCostCurve:v1`; RFC39-WTBD-006
adds a bounded `COST_AWARE` construction method that applies observed cost bps to candidate trade
notionals for comparison evidence; and RFC39-WTBD-004/RFC40-WTBD-008 add source-backed
restriction/sustainability profile consumption. Manage can block candidate trades that violate hard
client restrictions and preserve sustainability preference evidence in construction alternatives
and proof packs, while sustainability classification evidence gaps remain pending review.
Mandate twins now source objective, review cadence, review dates, and benchmark id from core where
available and keep explicit gap codes only when source fields are absent. Manage does not promote
predictive execution-cost quotes, market impact modelling, venue routing, broader execution
methodology, performance benchmark analytics, or unsupported ESG approval.

| Control | Count | Meaning |
| --- | ---: | --- |
| Total WTBD items | 59 | RFC-0036 through RFC-0042 follow-up items tracked in this ledger. |
| Done on merged/published truth | 45 | Implementation-backed items merged to owning `main` branches, validated, and published where wiki truth changed. |
| Partial / in progress | 8 | Items with meaningful implementation-backed progress but known source-owner or downstream gaps. |
| Remaining / open | 6 | Items still deferred, proposed, conditional, unsupported, or awaiting ownership. |

Recently closed in this snapshot:

RFC42-WTBD-008 is complete for the bounded PM operating quality support claim. `lotus-manage`
owns policy administration, score-run preview/create/read/list, source-backed PM-book scope
materialization, peer-group/lookback-window scope evidence, immutable fairness-analysis
preview/create/read/list, immutable review-action preview/create/read/list, portfolio-memory
score-run lineage, and fail-closed governance controls.
`lotus-gateway` PR #213 exposes the bounded PM operating quality BFF and review-gated
`pm_quality_summary.pack@v1` handoff, and `lotus-workbench` PR #245 (`2af063b`, wiki `2ba368d`,
Main Releasability Gate `25991445845`) completes the Gateway-only Workbench policy, score-run,
fairness-analysis preview/create/list/detail, and support-summary invocation surface. The closure
does not claim PM ranking, protected-class inference, HR, compensation, conduct, client contact,
trade approval, order routing, OMS, execution, persisted summary history, approval workflow beyond
immutable review actions, or autonomous decisions.

RFC40-WTBD-010 is complete for the current source-backed portfolio-memory support claim. Manage report-input APIs now attach bounded portfolio-memory context for proof-pack, rebalance-wave, and
outcome-review reports without folding that context into recursive report-input hashes. `lotus-ai`
PR #62 adds bounded portfolio-memory consumers for DPM PM memo and outcome-review narrative packs,
and `lotus-ai` PR #64 adds the AI-owned workflow-pack source-event family. The manage API now
publishes source-event family posture so future OMS execution and PM scoring remain explicit
deferred source-owner products rather than hidden portfolio-memory functionality.

RFC40-WTBD-009 is complete for the bounded scenario-pack authority support claim. `lotus-risk` PR
#141 (`978f441ef2023d178e6c3ba4f0f361c84b856427`, wiki `c2c6560`, Main Releasability Gate
`26098602664`) adds source-owned `governance_evidence` to `RegimeScenarioPackEvaluation:v1` for
CIO approval status/reference, approval body/time, effective-period posture, portfolio
applicability posture/scope/ref, methodology reference, and fail-closed reason-code/supportability
states for effective-period exceptions, missing portfolio applicability, and non-applicable
portfolios. `lotus-manage` now consumes the nested source-owned governance evidence through the
risk-authority client and preserves it in selected-alternative and direct proof-pack
`scenario_and_regime_evidence` facts without calculating scenario methodology, CIO approval,
effective-period posture, portfolio applicability, or contribution rows locally. Broader external
CIO workflow UX/integration remains future product depth rather than a WTBD blocker for this
bounded support claim.

Partial / in-progress items:

| ID | Current partial scope | Remaining gap |
| --- | --- | --- |
| RFC37-WTBD-001 | `lotus-manage` RFC-0042 backend authority and first-wave outcome product path are implemented. | Complete richer downstream/source-owner realization across all outcome learning loops. |
| RFC41-WTBD-003 | `lotus-risk` owns `RiskEventAffectedCohort:v1` at `POST /analytics/risk/risk-event-cohorts/evaluate`, merged in `lotus-risk` PR #115 (`bd69d1576d8c01bdcfd2309202ef37f780cc2d06`) and published to `lotus-risk.wiki` commit `91f933a`; `lotus-platform` PR #313 (`4218d4319d5dac82e87106429fadb14247c36515`) mirrors the product declaration for mesh governance. `lotus-manage` consumes that product for bounded `RISK_EVENT` wave preview/create from caller-supplied candidate portfolios with source-supplied exposure weights, fail-closed dependency handling, source-ref preservation, OpenAPI/API-vocabulary updates, and repo-native consumer declaration coverage. `lotus-advise` owns `TacticalHouseViewAffectedCohort:v1`; `lotus-manage` consumes it for bounded `TACTICAL_HOUSE_VIEW` wave preview/create over managed/discretionary source-backed candidates, preserving Advise cohort refs and candidate source refs without recomputing house-view or portfolio facts. `lotus-manage` now also owns `BulkReviewCampaignMembership:v1` for bounded `BULK_REVIEW_CAMPAIGN` wave preview/create over source-backed candidate portfolios with source-owned portfolio types, DPM portfolio-type filtering, deterministic membership refs and hash, optional approval/expiry/actor-entitlement governance evidence, persisted `BulkReviewCampaignDefinition:v1` definitions, persisted `BulkReviewCampaignDiscovery:v1` summaries at `GET /api/v1/rebalance/waves/campaign-discovery`, bounded campaign operating queue at `GET /api/v1/rebalance/waves/campaign-operating-queue`, bounded read-only campaign approval-attention inbox at `GET /api/v1/rebalance/waves/campaign-approval-inbox`, bounded read-only workflow board at `GET /api/v1/rebalance/waves/campaign-workflow-board`, bounded read-only assignment plan at `GET /api/v1/rebalance/waves/campaign-assignment-plan`, bounded read-only workflow automation readiness at `GET /api/v1/rebalance/waves/campaign-workflow-automation`, append-only assignment-action evidence, controlled assignment-task lifecycle evidence, append-only maker-checker control evidence with actor separation for completed reviews, campaign-definition retirement at `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/retire`, campaign-definition supersession at `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede`, lifecycle-event projection at `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/lifecycle-events`, workflow overview at `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview`, preview-readiness at `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness`, launch packages at `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package`, durable launch at `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch`, launch-history audit pages at `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-history`, assignment tasks at `POST`/`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`, task transitions at `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions`, and fail-closed validation. `lotus-gateway` PR #212 (`891d00dea0328525ada14fabad278af1d1b9386b`) exposes campaign-definition list/get/upsert BFF routes and published Gateway wiki commit `f49e84f`; PR #231 (`ea6c036`, Main Releasability Gate `25989936539`) extends the bounded BFF surface for lifecycle-events, launch-history, launch-package, durable launch, and campaign discovery while preserving Manage payloads without recomputing cohorts, membership, readiness, idempotency, order, or OMS facts. `lotus-workbench` PR #184 (`502aa2113a6e3954d53a35f9f956d258c84d5be0`) renders the active campaign-definition list and published Workbench wiki commit `694d9cd`; PR #244 (`31ea877`, Main Releasability Gate `25989936388`) validates Gateway-only READY-gated launch and paged launch-history/empty-state/no-order/no-OMS boundary rendering. | Global portfolio-universe campaign discovery and external workflow orchestration beyond Manage-side task readiness remain future depth. |
| RFC42-WTBD-006 | Selected risk, performance, core tax/cash/FX/cashflow/source-readiness/liquidity source-family adapters and methodology products are implemented. `lotus-risk` now has implementation-backed volatility, drawdown, Sharpe, Sortino, VaR, beta, tracking-error, and information-ratio methodology truth for `RiskMetricsReport:v1` plus rolling volatility, rolling Sharpe, rolling beta, rolling maximum drawdown, rolling tracking-error, and rolling information-ratio methodology truth for `RollingRiskMetricsReport:v1`, plus maximum-drawdown, average-drawdown, ulcer-index, and time-under-water methodology truth for `DrawdownAnalyticsReport:v1`, plus position-HHI, top-position weight, top-N cumulative weight, issuer-HHI, and top-issuer weight methodology truth for `ConcentrationRiskReport:v1`, including percentage-point to decimal conversion, `ddof=1` sample standard deviation/covariance/variance behavior, annualized percentage-point non-rolling volatility output, signed percentage-point non-rolling drawdown output, dimensionless annualized non-rolling Sharpe output, dimensionless annualized non-rolling Sortino output, signed percentage-point non-rolling VaR output, dimensionless non-rolling beta slope output, annualized percentage-point non-rolling tracking-error output, dimensionless annualized non-rolling information-ratio output, annualized decimal rolling volatility output, annualized decimal tracking-error output, dimensionless rolling Sharpe, beta, and information-ratio output, decimal rolling drawdown-ratio output, decimal drawdown analytics maximum-drawdown and average-drawdown output, non-negative decimal drawdown analytics ulcer-index output, observation-count drawdown analytics time-under-water output, conventional `0..10000` concentration position-HHI and issuer-HHI output, decimal `0..1` concentration top-position, top-N cumulative weight, and top-issuer weight output, strictly-underwater average-drawdown inclusion, strictly-underwater observation counting for time under water, full-path squared drawdown inclusion for ulcer index, concentration positive-value extraction, concentration current/proposed state fallback, concentration deterministic top-position driver selection, concentration top-N cumulative summation, concentration covered-subset issuer aggregation, concentration legal versus ultimate-parent issuer grouping, concentration issuer-enrichment precedence, concentration issuer coverage/supportability posture, concentration deterministic top-issuer driver selection, concentration top-issuer proposed-state fallback, concentration input-universe option boundaries, drawdown episode peak/trough/recovery semantics, warm-up/null behavior, source-owned risk-free/benchmark alignment posture, no-aligned dependency posture, zero-volatility Sharpe failure behavior, no-downside-observation Sortino failure behavior, signed non-rolling drawdown peak-to-trough posture, signed VaR loss-threshold posture, square-root VaR horizon scaling, zero-benchmark-variance beta failure behavior, constant-active-return zero tracking-error behavior, zero-tracking-error non-rolling information-ratio fail-closed behavior, zero-excess-volatility rolling-Sharpe flagging, zero-benchmark-variance rolling-beta flagging, and zero-tracking-error information-ratio flagging. `lotus-core` now has implementation-backed `HoldingsAsOf:v1` methodology truth for booked holdings, explicit as-of holdings, projected-inclusive holdings, cash-balance reads, reporting-currency cash balances, snapshot-versus-history fallback, position weights, supportability states, and explicit non-claims for income-needs planning, performance returns, risk exposure methodology, tax advice, execution quality, and OMS acknowledgement. `lotus-core` now has implementation-backed `MarketDataCoverageWindow:v1` methodology truth for latest price and FX observation selection, missing/stale coverage classification, configurable max-staleness policy, populated DPM source-readiness support, and explicit non-claims for valuation, FX attribution, market impact, execution quality, best execution, venue routing, and OMS acknowledgement. `lotus-core` now has implementation-backed `DpmSourceReadiness:v1` methodology truth for mandate binding, model target, eligibility, tax-lot, and market-data coverage composition, deterministic instrument-universe assembly, fail-closed family precedence, supportability/data-quality mapping, and explicit non-claims for mandate approval, client suitability, tax advice, valuation, FX attribution, execution quality, best execution, venue routing, and OMS acknowledgement. `lotus-core` now has implementation-backed `PortfolioCashflowProjection:v1` methodology truth for booked-only versus projected modes, latest-cashflow-row selection, settlement-dated external `DEPOSIT`/`WITHDRAWAL` inclusion, same-day booked/projected additivity with separate booked and projected component fields, portfolio-base-currency output, and explicit non-claims for tax, performance, market impact, and OMS execution. `lotus-core` now also has implementation-backed `PortfolioLiquidityLadder:v1` methodology truth for opening cash balance, fixed horizon buckets, booked/projected/net cashflow, cumulative cash balance, shortfall, asset-liquidity-tier exposure, supportability, OpenAPI route documentation, route-family governance, source-product catalog/security profiles, and explicit non-claims for advice, funding recommendations, income-needs planning, tax methodology, FX attribution, market impact, best execution, venue routing, and OMS acknowledgement. `lotus-core` now also has implementation-backed `PortfolioTaxLotWindow:v1` methodology truth for effective-date lot selection, optional security filtering, open/closed lot posture, deterministic paging, open-quantity status derivation, cost-basis preservation, empty-source supportability, and explicit non-claims for jurisdiction-specific tax advice, realized-tax optimization, wash-sale handling, client-tax approval, tax-reporting certification, and execution methodology. `lotus-core` now has implementation-backed `ClientTaxProfile:v1` and `ClientTaxRuleSet:v1` source products for profile/rule ingestion, discretionary-mandate portfolio binding, supportability, lineage, route-family governance, source-product catalog/security profiles, and explicit non-claims for tax advice, after-tax optimization, tax-loss harvesting suitability, jurisdiction-specific recommendation, and OMS acknowledgement. `lotus-core` PR #362 (`c1fb350c`) now has implementation-backed `ClientIncomeNeedsSchedule:v1`, `LiquidityReserveRequirement:v1`, and optional `PlannedWithdrawalSchedule:v1` source products for bounded client-liquidity reference evidence, supportability, lineage, route-family governance, source-product catalog/security profiles, wiki publication (`40a1228`), and explicit non-claims for financial-planning advice, funding recommendations, treasury instructions, cashflow forecasting, suitability approval, and OMS acknowledgement. `lotus-core` now has implementation-backed `PortfolioRealizedTaxSummary:v1` methodology truth for portfolio-level explicit realized tax evidence, withholding-tax and other-interest-deduction aggregation by ledger currency, optional reporting-currency restatement from Core FX rates, lineage/supportability posture, route-family governance, source-product catalog/security profiles, and explicit non-claims for tax advice, after-tax optimization, tax-loss harvesting suitability, jurisdiction-specific recommendation, client-tax approval, and tax-reporting certification. `lotus-core` also has implementation-backed `TransactionLedgerWindow:v1` methodology truth for booked and projected-inclusive ledger modes, effective as-of resolution, row filtering by portfolio/instrument/security/transaction type/FX event/date/as-of window, joined transaction-cost and linked-cashflow row preservation, field-aware reporting-currency restatement from latest FX rates using book currency for book fields and trade currency for trade/local fields, explicit row-level realized FX P&L local evidence, canonical USD/SGD and EUR/SGD seed coverage for front-office proof, empty/complete/paged data-quality posture, and explicit non-claims for tax advice, FX attribution, cash movement aggregation, transaction-cost curve methodology, execution quality, and OMS acknowledgement. `lotus-core` also has implementation-backed `TransactionCostCurve:v1` methodology truth for observed booked-fee grouping, trade-fee precedence, zero-fee/zero-notional exclusion, notional-weighted average bps, min/max bps, deterministic paging, and explicit non-claims for predictive execution quotes, market impact, venue routing, best execution, and OMS acknowledgement. `lotus-performance` has tightened source-owner MWR and contribution methodology/wiki truth for stateful lotus-core source resolution and portfolio/position timeseries normalization. The attribution methodology truth covers stateful lotus-core portfolio/position, benchmark, and source-currency normalization for allocation, selection, interaction, active-return, currency-attribution outputs, and source-owned portfolio-level `currency_attribution_totals` through `lotus-performance` PR #164 (`cbda83f`, wiki `f76a954`). | Aggregated risk/performance outside implemented source products, broader FX methodology beyond performance-owned Karnosky-Singer attribution totals, financial-planning advice, funding recommendations, predictive execution, and OMS execution methodologies remain source-owner work. No tax-advice, after-tax optimization, tax-loss harvesting suitability, jurisdiction-specific recommendation, client-tax approval, or tax-reporting certification claim is made. |
| RFC42-WTBD-007 | Lotus-side fail-closed source contract and Manage consumer are implemented for external execution/OMS acknowledgements. | Production OMS integration still needs a bank-owned execution/OMS owner, ingestion controls, acknowledgements, fills, settlement, and reconciliation contract before support can be promoted. |

Next bank-buyable product-readiness priorities:

2026-05-16 source-owner FX attribution update: `lotus-performance` PR #167 (`16261c9`, wiki
`41bdaa3`) tightens the existing source-owned portfolio-level `currency_attribution_totals` path.
Grouped requests that include `currency` plus another dimension now recompute a date/currency panel
from summed weights and weight-averaged local/FX returns before applying Karnosky-Singer formulas.
This advances RFC42-WTBD-006 source-owner FX methodology depth without adding any Manage-local FX
attribution calculation, tax, execution, OMS, or Workbench product claim.

2026-05-16 source-owner historical-attribution supportability update: `lotus-risk` PR #139
(`40ac7a5`, wiki `421ae79`) tightens `HistoricalRiskAttributionReport:v1` so any source-owned
attribution-set quality flag degrades response-level `metadata.calculation_supportability`.
Manage consumes this as source-owner supportability truth only: missing grouping data, empty
active-risk alignment, and unsupported attribution combinations remain degraded risk evidence, not
ready values for local promotion or recalculation.

| Priority | WTBD | Why this is next | Promotion bar |
| ---: | --- | --- | --- |
| 1 | RFC42-WTBD-006 - Source-owner realized methodology depth | Promotes aggregate risk, performance, tax, FX, cash, liquidity, and execution methodology from selected adapters into auditable source-owned products. Current source-owner slices tighten `lotus-risk` non-rolling volatility, non-rolling drawdown, non-rolling Sharpe, non-rolling Sortino, non-rolling VaR, non-rolling beta, non-rolling tracking-error, non-rolling information-ratio, rolling volatility, rolling Sharpe, rolling beta, rolling maximum drawdown, rolling tracking-error, rolling information-ratio, drawdown analytics maximum-drawdown, average-drawdown, ulcer-index, and time-under-water methodology/wiki truth, and concentration position-HHI, top-position weight, top-N cumulative weight, issuer-HHI, and top-issuer weight methodology/wiki truth, `lotus-core` holdings-as-of, market-data coverage, DPM source-readiness, transaction-ledger window, cashflow-projection, liquidity-ladder, tax-lot window, client-tax profile/rule, portfolio realized-tax summary, and observed transaction-cost curve methodology/wiki truth, and `lotus-performance` MWR, contribution, and attribution methodology/wiki truth so stateful source resolution is auditable and downstream consumers cannot reconstruct `RiskMetricsReport:v1` volatility, drawdown, Sharpe, Sortino, VaR, beta, tracking error, or information ratio, rolling active-risk, rolling excess-return risk-adjusted performance, rolling benchmark sensitivity, rolling window maximum drawdown, drawdown analytics maximum drawdown, average drawdown, ulcer index, or time under water, concentration position HHI, concentration top-position weight, concentration top-N cumulative weight, concentration issuer HHI, concentration top issuer weight, rolling portfolio volatility, holdings snapshot selection, position weighting, cash-balance restatement, market price/FX freshness classification, DPM readiness family precedence, transaction row windowing/restatement, operational cash movement, cash-flow schedules, liquidity buckets, lot/cost-basis selection, explicit realized-tax aggregation, observed booked-fee cost curves, position contribution, active return, Brinson effects, or currency attribution locally. | Owning services provide methodology docs, contracts, degraded-state tests, live proof, and product-surface preservation without manage-local recalculation. |
| 2 | RFC41-WTBD-003 - Tactical house-view, risk-event, and campaign/bulk-review cohorts | Moves the rebalance wave operating model toward bank operating workflows without inventing source-owned cohorts. Risk-event source ownership, bounded manage consumption, Advise-owned tactical house-view source ownership, bounded Manage tactical house-view consumption, first-wave Manage-owned bulk-review campaign membership with optional governance evidence, immutable Manage-owned campaign definitions over source-backed candidate sets, fail-closed campaign-definition preview readiness, bounded campaign-definition launch packages, deterministic durable launch from ready definitions, append-only launch-history audit pages, append-only campaign approval-decision evidence, append-only assignment-action evidence, controlled assignment-task lifecycle evidence, append-only maker-checker control evidence with actor separation for completed reviews, bounded campaign operating queue, bounded approval-attention inbox, bounded workflow board, bounded assignment plan, bounded workflow automation readiness, bounded portfolio-memory projection for campaign definition workflow evidence, Gateway campaign-definition BFF composition through PR #212 and PR #231, and Workbench active campaign-definition list plus READY-gated launch/history rendering through PR #184 and PR #244 are now implemented. | Global portfolio-universe campaign discovery and external workflow orchestration beyond Manage-side task readiness are added only after source behavior and product evidence are proven. |

2026-05-09 validation hardening:

`make live-api-validate-core` / `scripts/validate_live_api.py` now includes a dedicated
`stateful_source_backed_construction` probe when
`LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available`. The probe exercises the live stateful
construction path and verifies that `COST_AWARE`, `LIQUIDITY_AWARE`, and `ESG_AWARE` alternatives
preserve `lotus-core` source-backed context for `TransactionCostCurve:v1`,
`PortfolioCashflowProjection:v1`, `ClientRestrictionProfile:v1`, and
`SustainabilityPreferenceProfile:v1`. This closes a proof-quality gap in the completed
RFC39-WTBD-004, RFC39-WTBD-006, RFC39-WTBD-007, RFC40-WTBD-007, and RFC40-WTBD-008 claims without
promoting any unsupported income-need, predictive execution, market-impact, or regulatory
suitability methodology.

Gold-pass assessment for the 2026-05-09 validation hardening:

1. Truly completed: live stateful construction now proves source-backed cost, liquidity,
   restriction, and sustainability context from `lotus-core` instead of stopping at stateful
   simulate lineage.
2. Quality improvements: `lotus-manage` resolves `PortfolioCashflowProjection:v1` through the
   query-plane source route, uses a configurable private-banking transaction-cost lookback for
   low-turnover portfolios, and exposes the required query-plane runtime setting in local Docker.
3. Debt removed: the previous validation blind spot around stateful construction source products is
   closed, and the canonical `lotus-core` seed now includes observed booked-fee evidence so
   `TransactionCostCurve:v1` is not an empty envelope for the governed portfolio.
4. Proven evidence: `LOTUS_MANAGE_EXPECT_STATEFUL_CORE_SOURCING=available make
   live-api-validate-core` passed 14/14 against `manage.dev.lotus`, `core-control.dev.lotus`, and
   `core-query.dev.lotus`; the saved evidence shows nine returned transaction-cost curve points,
   `PortfolioCashflowProjection:v1`, `ClientRestrictionProfile:v1`, and
   `SustainabilityPreferenceProfile:v1` in the live stateful construction diagnostics.
5. Standard reached: this slice reaches the expected production-readiness standard for the completed
   WTBD proof gap. Open items remain only where the WTBD already defers unsupported OMS,
   market-impact, client-income-need, PM-scoring, and regulatory-suitability methodology to owning
   future RFCs.

Execution rule:

Do not open a new WTBD implementation slice until the current slice has passed local validation,
GitHub required checks, PR merge, wiki publication where needed, final `git fetch origin --prune`
plus `git branch -r --no-merged origin/main`, and clean branch/status hygiene.

## RFC-0036 - DPM Stateful Core Sourcing And Endpoint Consolidation

Current closure status:

RFC-0036 is implemented and gold-pass clean for the `lotus-manage` API surface and stateful
core-sourced execution path. It removed duplicate unversioned routes and advisory/proposal runtime
remnants, made stateless execution explicit, added the gated stateful `portfolio_id` execution
envelope, composed governed `lotus-core` RFC-087 source products, preserved source lineage and
supportability, certified the implemented APIs, proved live `manage.dev.lotus` plus
`core-control.dev.lotus` / `core-query.dev.lotus`, published wiki truth, and kept stateful
capability publication behind explicit runtime gates.

2026-05-09 gold-pass audit update: completed RFC36-WTBD-001 through RFC36-WTBD-003 have been moved
back into `docs/rfcs/RFC-0036-dpm-stateful-core-sourcing-and-endpoint-consolidation.md` as
implemented follow-on truth. This WTBD ledger remains the control register, closure evidence
index, and sequencing view; RFC-0036 is now the durable narrative for the completed Gateway,
Workbench, and operations-dashboard product realization.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0036-dpm-stateful-core-sourcing-and-endpoint-consolidation.md` |
| Supported feature claims | `wiki/Supported-Features.md` stateful execution and core source-sourcing rows |
| Manage/core proof target | `make live-api-validate-core` |
| Manage implementation | `src/core/dpm_source_context.py`, `src/infrastructure/core_sourcing/`, rebalance simulate/analyze/async API paths |
| Source products proven | `DpmModelPortfolioTarget:v1`, `DiscretionaryMandateBinding:v1`, `InstrumentEligibilityProfile:v1`, `PortfolioTaxLotWindow:v1`, `MarketDataCoverageWindow:v1`, `DpmSourceReadiness:v1` |
| Live proof posture | RFC-087 core validation 7/7 and manage/core validation 11/11 with `--expect-stateful-core-sourcing available` |

### Remaining Work Summary

These items are deliberately outside RFC-0036 closure because RFC-0036 certified the service API
surface and stateful source resolver, while product composition, richer upstream source depth, and
mesh/product promotion belong to downstream or platform/source owners.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0036 |
| --- | --- | --- | --- | --- |
| RFC36-WTBD-001 | Gateway integration rebuilt against canonical `/api/v1` manage APIs | `lotus-gateway` | Completed and merged to `lotus-gateway` `main` in PR #191 (`a68181b`) | Endpoint cleanup intentionally accepted breaking stale Gateway assumptions. Gateway now consumes certified manage APIs without reintroducing aliases or monolithic context assumptions. |
| RFC36-WTBD-002 | Workbench product surfaces over stateful manage execution | `lotus-workbench` through Gateway/BFF | Completed and merged to `lotus-workbench` `main` in PR #152 (`c83ea7e`) | Workbench now surfaces Gateway-provided manage rebalance action-register supportability without direct manage calls or locally invented source readiness. |
| RFC36-WTBD-003 | Portfolio-level DPM operation dashboards over stateful executions | `lotus-gateway`, `lotus-workbench`, `lotus-manage` | Completed, merged, live-proven, and wiki-published through `lotus-gateway` PR #192/#193 and `lotus-workbench` PR #153 | RFC-0036 certified execution/source posture. This follow-up now promotes recent-run and supportability telemetry into the Gateway BFF and Workbench product surface without making Workbench call manage directly. |
| RFC36-WTBD-004 | Promote additional stateful DPM source-data products into platform mesh certification | `lotus-platform` with source producers and `lotus-manage` consumer declarations | Deferred until source-data lineage stabilizes | Current source products are live-proven; future stateful products need producer approval, declarations, trust telemetry, SLO/access/evidence policies, and certification. |
| RFC36-WTBD-005 | Additional upstream source-product depth for stateful execution | `lotus-core` and future source owners | Deferred source enrichment | RFC-0036 consumes the certified RFC-087 products. Additional portfolio, market-data, cashflow, benchmark, restriction, or execution-depth sources require explicit retrieval design. |
| RFC36-WTBD-006 | Downstream migration handling if production consumers of removed aliases are discovered | Owning consumer repo if a dependency is proven; `lotus-platform` for durable vocabulary mirrors | Completed as no-migration-required conditional closure | Cross-repo audit found no active Gateway/Workbench production dependency that requires retired manage proposal routes or unversioned manage capability aliases. The only stale durable truth found was the platform `lotus-manage` API-vocabulary mirror; `lotus-platform` PR #316 refreshed it from current manage vocabulary, removed retired route entries, and added a regression. No compatibility alias is added. |

### Detailed Follow-Up Items

#### RFC36-WTBD-001 - Gateway Integration Rebuilt Against Canonical `/api/v1` Manage APIs

Target business outcome:

Gateway composes the certified manage rebalance, supportability, capability, and stateful-source
posture through clean `/api/v1` contracts without stale aliases or retired monolithic core context.

Closure status:

Completed on 2026-05-06 through `lotus-gateway` PR #191,
`test: guard manage canonical API consumption`, merged to `main` at
`a68181bdd9b8721b5cd613709392ce0e6e89748b`.

What was delivered:

1. `lotus-gateway` already consumed manage through versioned `/api/v1` APIs for rebalance run
   lookup, supportability summary, capability posture, construction alternatives, and
   outcome-review report/AI evidence paths.
2. Added executable regression coverage in
   `lotus-gateway/tests/unit/test_upstream_clients.py::test_dpm_client_uses_only_canonical_manage_api_v1_contracts`
   to exercise every manage-facing `DpmClient` method and reject retired unversioned route
   families, platform capability aliases, and monolithic `dpm-execution-context` assumptions.
3. Tightened `lotus-gateway/docs/standards/RFC-0082-upstream-contract-family-map.md` so the
   manage upstream contract family explicitly records the canonical `/api/v1` route posture and
   boundary rule.

Validation evidence:

1. Local targeted proof:
   `python -m pytest tests/unit/test_upstream_clients.py -k "dpm_client_uses_only_canonical_manage_api_v1_contracts or dpm_client_manage_routes or dpm_client_outcome_review_command_routes or dpm_client_construction_generate_route"`
   passed with 17 selected tests.
2. Local repo gate: `make check` passed in `lotus-gateway`, including Ruff lint, Ruff format
   check, monetary-float guard, mypy, Workbench contract smoke, and 423 unit/contract tests.
3. GitHub PR #191 checks passed before merge: Feature Lane lint/typecheck/unit, Feature Lane
   workflow lint, PR Merge Gate workflow lint, lint/typecheck/unit, integration tests, coverage
   gate, Docker build validation, CI local Docker parity, and queue auto-merge.
4. Wiki synchronization check/publish for `lotus-gateway` completed with diff count 0 because no
   wiki source change was required for this developer-standards/test hardening.

Gold-pass assessment:

This WTBD has reached the expected standard for its stated scope. The owning Gateway implementation
is merged to `main`, the canonical manage route posture is protected by direct regression tests, the
developer contract map is updated, CI has passed, and no unmerged Gateway branch contains additional
durable truth for this item.

#### RFC36-WTBD-002 - Workbench Product Surfaces Over Stateful Manage Execution

Target business outcome:

Workbench can present stateful DPM execution readiness and outcomes to users through Gateway-backed
flows, while hiding the technical source-resolution complexity.

Closure status:

Completed on 2026-05-06 through `lotus-workbench` PR #152,
`feat: surface manage rebalance supportability`, merged to `main` at
`c83ea7e136dd00cae1042cb9597fd2c42b634d56`.

What was delivered:

1. Extended the Workbench overview `rebalance_snapshot` type so the UI can consume
   Gateway-provided manage action-register supportability without a direct `lotus-manage` call.
2. Rebuilt the `/workbench/{portfolioId}` rebalance status panel to render manage-owned status,
   source support state, freshness, run count, operation count, workflow decision count,
   last-run identity, and reason posture.
3. Added explicit unknown/N/A handling when Gateway omits action-register supportability so
   missing source context is not misrepresented as verified zero activity.
4. Added focused unit coverage for ready, source-incomplete, and missing-supportability postures.
5. Updated `lotus-workbench` repository context and repo-authored wiki source so product,
   operator, and engineering material reflects the implementation-backed behavior.

Validation evidence:

1. Local targeted proof:
   `npx vitest run tests/unit/rebalance-status.test.tsx` passed with 3 tests.
2. Local type proof: `npm run typecheck` passed.
3. Local repo gate: `make check` passed in `lotus-workbench`, including lint, typecheck,
   156 test files / 707 tests with coverage, and production build.
4. Live canonical proof:
   `powershell -ExecutionPolicy Bypass -File scripts/live/Start-LotusFrontOfficeCanonical.ps1 -LocalApps workbench -RunValidation -ScreenshotDirectory output/playwright/rfc36-wtbd002-rebalance-status`
   passed for `PB_SG_GLOBAL_BAL_001` after the governed seed completed.
5. Targeted live browser assertion against
   `http://workbench.dev.lotus/workbench/PB_SG_GLOBAL_BAL_001` proved the rebalance panel rendered
   status, source support, freshness, evidence counts, and the explicit missing-supportability
   message from the live Gateway payload.
6. GitHub PR #152 checks passed before merge: Feature Lane lint/typecheck/test, Feature Lane
   workflow lint, PR Merge Gate workflow lint, lint/typecheck/coverage/build, Playwright smoke,
   Docker build validation, CI local Docker parity, and queue auto-merge.
7. `lotus-workbench` wiki publication completed after merge; `Sync-RepoWikis.ps1 -CheckOnly
   -Repository lotus-workbench` passed after publishing.

Gold-pass assessment:

This WTBD has reached the expected standard for its stated scope. The Workbench implementation is
merged to `main`, the UI remains Gateway/BFF-only, source-incomplete and missing-supportability
states are explicit, the behavior is protected by unit tests and full local/GitHub gates, canonical
front-office evidence was captured, and repo-local plus published wiki material now reflects the
implementation-backed product behavior.

#### RFC36-WTBD-003 - Portfolio-Level DPM Operation Dashboards

Target business outcome:

Operations and PM users can monitor stateful DPM execution supportability, source readiness,
recent runs, errors, and workflow posture at portfolio/book level.

Closure status:

Completed on 2026-05-06 through the coordinated downstream implementation wave:

1. `lotus-gateway` PR #192, `feat: expose DPM operations dashboard data`, merged to `main` at
   `df428d62e0d54501696afcfd7014b378765e02a9`.
2. `lotus-workbench` PR #153, `feat: render DPM operations dashboard`, merged to `main` at
   `3cbc68895eb098e147d9b0f85a7ceaea5e883fb4`.
3. `lotus-gateway` corrective PR #193,
   `fix: map manage supportability into workbench snapshot`, merged to `main` at
   `8afa4d3e9e58f2d60d9e10a9c7bb92fd8fe18ca9` after canonical evidence exposed that live
   manage supportability came from `/api/v1/rebalance/supportability/summary`, not the rebalance
   run list payload.

What was delivered:

1. `lotus-gateway` now enriches the Workbench overview `rebalance_snapshot` with recent manage
   rebalance runs from `/api/v1/rebalance/runs?portfolio_id=<portfolio>&limit=5`.
2. `lotus-gateway` now fetches live manage action-register supportability from
   `/api/v1/rebalance/supportability/summary` and maps it into the same Gateway-owned
   Workbench BFF snapshot without requiring Workbench to call manage directly.
3. Gateway parsing preserves bounded telemetry: rebalance run id, status, workflow status,
   portfolio id, timestamps, source/error labels, and supportability state/count/freshness posture.
4. `lotus-workbench` extends the rebalance status panel to show operations-facing recent-run
   counts, issue counts, latest run rows, workflow posture, error/source labels, and an explicit
   no-runs state.
5. Product documentation, repository context, and repo-local/published wiki truth were updated in
   the owning Gateway and Workbench repositories. This `lotus-manage` ledger records closure only;
   no additional `lotus-manage` wiki source change is required for this slice.

Validation evidence:

1. Gateway PR #192 local targeted proof passed with 3 tests, and `make check` passed with Ruff
   lint, Ruff format check, monetary-float guard, mypy, Workbench contract smoke, and 423 tests.
2. Gateway PR #193 local targeted proof passed with 2 tests; broader focused regression proof
   passed with 54 tests across Workbench service unit, integration, and contract coverage; final
   `make check` passed with Ruff lint, Ruff format check, monetary-float guard, mypy, Workbench
   contract smoke, and 424 tests.
3. Workbench PR #153 local targeted proof passed with 7 tests; `npm run typecheck` passed; final
   `make check` passed with lint, typecheck, 156 test files / 707 tests, coverage, and production
   build.
4. GitHub CI was green before merge for Gateway PR #192, Workbench PR #153, and Gateway PR #193,
   including Feature Lane checks, PR Merge Gate checks, Docker/parity gates where configured, and
   queue auto-merge.
5. `lotus-gateway` wiki publication completed for PR #192 at wiki commit `778e992` and for PR #193
   at wiki commit `0085441`; post-publish `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-gateway`
   reported zero drift. `lotus-workbench` wiki publication completed for PR #153 at wiki commit
   `ff0b4ff`.
6. Canonical front-office validation passed after rebuilding impacted images:
   `powershell -ExecutionPolicy Bypass -File scripts/live/Start-LotusFrontOfficeCanonical.ps1 -BuildImages -LocalApps workbench -RunValidation -ScreenshotDirectory output/playwright/rfc36-wtbd003-dpm-operations-dashboard`
   produced `live-validation-summary.json`, `SHOT-INDEX.md`, and
   `dpm-outcome-review-live.png` for `PB_SG_GLOBAL_BAL_001`.
7. A focused live browser/API assertion against
   `http://workbench.dev.lotus/workbench/PB_SG_GLOBAL_BAL_001` and
   `http://gateway.dev.lotus/api/v1/workbench/PB_SG_GLOBAL_BAL_001/overview` passed after PR #193:
   the Workbench dashboard was visible, `recentRunCount` was 5, latest run
   `rr_c09f73d0` had status `PENDING_REVIEW`, `supportabilityStatus` was `ready`,
   `supportabilityRunCount` was 82, `consoleErrorCount` was 0, and `missing` was empty.

Gold-pass assessment:

This WTBD has reached the expected standard for its stated first-wave scope. The product path is
merged to `main` in the owning Gateway and Workbench repositories, the UI remains Gateway/BFF-only,
the Gateway fix was driven by live evidence rather than papering over a missing field, local tests
and GitHub gates passed, canonical Workbench proof passed on the governed stack, and owning
repo-local plus published wiki material reflects the implementation-backed capability. Richer book-
level aggregation, operations drill-down pages, alerting, and report/AI materialization remain
future product depth and should be tracked under later command-center/reporting WTBDs rather than
reopening this first-wave operations dashboard slice.

### RFC36 Gold-Pass Audit And RFC Reintegration - 2026-05-09

Current decision:

RFC36-WTBD-001, RFC36-WTBD-002, and RFC36-WTBD-003 remain complete after slice-by-slice audit.
Their implementation truth has been incorporated into RFC-0036 so completed work is not stranded
only in this WTBD ledger.

What was truly completed:

1. Gateway integration was rebuilt and guarded against stale manage aliases through canonical
   `/api/v1` route tests.
2. Workbench renders stateful DPM supportability and rebalance status only through Gateway/BFF
   data.
3. Portfolio-level DPM operations dashboard visibility is available for source supportability,
   freshness, recent runs, run issues, workflow posture, no-runs posture, and missing-supportability
   posture.

Quality improvements made:

1. Current targeted Gateway, Workbench, and documentation tests were rerun during this audit before
   claiming completion.
2. Completed WTBD truth was moved into RFC-0036, reducing durable-truth fragmentation.
3. Wiki source was enriched with current-state feature behavior, integration flow, audience-specific
   usage, and non-functional controls for the RFC36 product path.

Debt removed:

1. ledger-only closure truth for the completed downstream RFC36 follow-ons,
2. ambiguous follow-on status inside RFC-0036,
3. outdated impression that Gateway integration, Workbench realization, or the operations dashboard
   remained merely future considerations.

Testing and evidence:

1. `lotus-gateway` targeted proof passed: 23 selected tests in
   `tests/unit/test_upstream_clients.py`.
2. `lotus-workbench` targeted proof passed: 3 tests in
   `tests/unit/rebalance-status.test.tsx`.
3. `lotus-manage` documentation current-state proof passed: 14 tests in
   `tests/unit/test_documentation_current_state.py`.
4. Canonical front-office QA was rerun through the governed platform wrapper against
   `PB_SG_GLOBAL_BAL_001`; the generated summary is retained at
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260509-214551.json` and the
   screenshot evidence is retained under
   `lotus-platform/output/front-office-qa/wtbd-rfc36-audit-20260509-214550`.
5. Evidence review confirmed the DPM command-center, proof-pack, outcome-review, portfolio-memory,
   and wave command-center panels are demo-ready. It also confirmed `performance.evidence` remains
   truthfully degraded under RFC-0079 ownership and manage action-register supportability remains
   stale; those are follow-on source-supportability truths, not hidden completion claims.

Expected-standard decision:

The completed RFC36 WTBDs have genuinely reached the expected first-wave standard. No code change
was required by this audit; the remaining action was documentation closure so RFC, WTBD, and wiki
truth align with merged implementation and live validation evidence.

#### RFC36-WTBD-004 - Additional Stateful Source Products In Mesh Certification

Target business outcome:

Every stateful source product used by DPM execution has producer declarations, consumer
declarations, trust telemetry, SLO/access/evidence policies, and platform certification.

Why it cannot be done now:

RFC-0036 validated current RFC-087 source products and existing declarations. Future products must
wait for upstream producer approval and stable lineage/supportability semantics.

Dependencies before implementation:

1. source owner declares the product,
2. `lotus-manage` adds or updates consumer declarations,
3. trust telemetry and SLO/access/evidence policies are available,
4. platform mesh certification includes the product,
5. live proof shows source readiness and degraded behavior.

Expected implementation wave:

Implement product by product as new stateful source dependencies are introduced.

2026-05-20 current-state consumer declaration hardening:

`lotus-manage` now declares the full current implementation-backed source-consumer surface used by
stateful DPM execution, mandate health, source readiness, proof packs, waves, outcome evidence, PM
operating quality, and portfolio memory. The repo-native consumer declaration now includes
`DpmModelPortfolioTarget:v1`, `DiscretionaryMandateBinding:v1`,
`InstrumentEligibilityProfile:v1`, `PortfolioTaxLotWindow:v1`, `MarketDataCoverageWindow:v1`,
`DpmSourceReadiness:v1`, `PortfolioCashflowProjection:v1`,
`ClientIncomeNeedsSchedule:v1`, `LiquidityReserveRequirement:v1`,
`PlannedWithdrawalSchedule:v1`, `ClientRestrictionProfile:v1`,
`SustainabilityPreferenceProfile:v1`, `ExternalCurrencyExposure:v1`,
`ExternalHedgePolicy:v1`, `ExternalFXForwardCurve:v1`,
`ExternalEligibleHedgeInstrument:v1`, `ExternalHedgeExecutionReadiness:v1`,
`ExternalOrderExecutionAcknowledgement:v1`, `CioModelChangeAffectedCohort:v1`,
`PortfolioManagerBookMembership:v1`, `TransactionCostCurve:v1`,
`RiskEventAffectedCohort:v1`, `TacticalHouseViewAffectedCohort:v1`, and
`RegimeScenarioPackEvaluation:v1`.

This is a governance hardening slice for current truth, not a new runtime feature. It advances
RFC36-WTBD-004 by making repo-native mesh declarations match the implemented source-consumer
surface and by preserving explicit fail-closed/degraded/pending-review posture per dependency. It
does not promote `BenchmarkAssignment:v1` until the upstream source owner approves Manage as a
consumer, and it does not promote raw market-data ownership, valuation methodology, risk
methodology, performance methodology, tax advice, financial-planning advice, scenario methodology,
execution, OMS acknowledgement ingestion, fills, settlement, or treasury action.

Promotion proof:

1. producer and consumer declarations validate,
2. platform mesh certification passes,
3. manage live proof consumes the product,
4. README/wiki/context updates state the new source dependency.

#### RFC36-WTBD-005 - Additional Upstream Source-Product Depth

Target business outcome:

Stateful DPM execution can consume richer source truth, such as benchmark, cashflow, restriction,
market-data depth, execution cost, or portfolio operations data, without expanding manage into a
source-data owner.

Why it cannot be done now:

RFC-0036 proved the RFC-087 source family and explicitly states that future stateful resolution
must be added only after upstream producer approval and explicit retrieval design.

Dependencies before implementation:

1. source owner and contract for each new source family,
2. source-readiness and lineage semantics,
3. manage resolver and transformer tests,
4. feature-gated capability publication if user-visible,
5. live proof for ready, stale, missing, and incomplete source states.

Expected implementation wave:

Add only when a downstream RFC requires the source and the source owner is ready.

Promotion proof:

1. source-owner certification,
2. manage resolver tests,
3. `make live-api-validate-core` or successor live proof,
4. supported-feature/context updates.

#### RFC36-WTBD-006 - Conditional Downstream Migration Handling

Target business outcome:

If a real production consumer of removed aliases or retired routes appears, it is migrated without
polluting the strategic manage API contract.

Closure result:

Completed as a no-migration-required conditional closure on 2026-05-10. The cross-repo audit found
no active Gateway or Workbench production dependency that requires retired manage proposal routes,
unversioned manage capability aliases, or legacy camelCase manage source-query parameters. The
right outcome is to keep the strategic `/api/v1` manage contract clean rather than adding
compatibility code.

Issue found and fixed:

The audit did find stale durable platform governance truth:
`lotus-platform/platform-contracts/api-vocabulary/lotus-manage-api-vocabulary.v1.json` still
contained retired manage proposal and unversioned capability paths. `lotus-platform` PR #316
refreshed that platform mirror from the current `lotus-manage` API-vocabulary snapshot and added a
regression that rejects retired manage paths.

Validation evidence:

1. cross-repo search found no active Gateway/Workbench production use of retired manage proposal
   routes,
2. `lotus-platform` PR #316 merged to `main` with green Cross-App Vocabulary Gate, Feature Lane,
   and PR Merge Gate platform-contract checks,
3. local platform proof passed `python platform-contracts/api-vocabulary/validate_api_vocabulary_catalog.py`,
4. local platform proof passed
   `python -m pytest tests/unit/test_analytics_ui_ecosystem_final_closure.py -q`,
5. the refreshed platform vocabulary mirror no longer contains `/rebalance/proposals`,
   `/api/v1/rebalance/proposals`, or unversioned manage `/integration/capabilities` entries.

Gold-pass assessment - 2026-05-10:

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | The conditional downstream-migration item was audited and closed without adding compatibility aliases because no real consumer dependency was found. The stale platform API-vocabulary mirror was corrected and merged. |
| Quality improvements made | Durable platform contract truth now matches the certified manage `/api/v1` surface, and a regression prevents retired manage proposal routes from returning to the platform vocabulary mirror. |
| Debt removed | Stale platform vocabulary entries for removed manage proposal and unversioned capability paths were removed instead of preserving misleading compatibility history. |
| What was proven through testing and evidence | Cross-repo search, platform API-vocabulary catalog validation, focused platform contract tests, and green `lotus-platform` PR #316 checks prove the strategic manage contract remains canonical. |
| Expected-standard decision | RFC36-WTBD-006 reaches the expected standard as a no-migration-required closure. Future compatibility work requires a newly proven consumer dependency and must not add permanent aliases without an expiry/removal plan. |

### Suggested Sequencing

Recommended order:

1. rebuild Gateway integration against canonical manage APIs,
2. add Workbench product surfaces through Gateway,
3. implement portfolio-level operation dashboards if needed,
4. add new source products and mesh certification as future RFCs require them,
5. keep legacy-consumer migration closed unless an actual production dependency is proven later.

### RFC-0036 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. canonical `/api/v1` contracts remain the only supported service APIs,
2. stateful capability publication remains gated and truthful,
3. manage does not become a source-data owner,
4. Gateway and Workbench consume through the governed product path,
5. source-ready, stale, missing, unavailable, and disabled-gate states are tested,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC, wiki, supported-features, endpoint certification, and repository context are
   aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.
## RFC-0037 - DPM Operating System And Mandate Intelligence

Current closure status:

RFC-0037 is a strategic parent roadmap, not a single implementation closure. It defines the target
DPM operating-system proposition and the execution contract inherited by RFC-0038 through RFC-0043.
Implementation-backed support has advanced through RFC-0038, RFC-0039, RFC-0040, RFC-0041, and the
RFC-0042 bounded first-wave outcome-review product path. The canonical DPM sales/demo story is also
implemented and wiki-published through `lotus-platform` PR #310. RFC-0043 is partially implemented
for owner-side DPM workflow packs, while external OMS execution, PM scoring, client communication,
broader portfolio memory, full copilot workspace depth, and richer source-owner methodology depth
remain future or partial scope.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Strategic RFC | `docs/rfcs/RFC-0037-dpm-operating-system-and-mandate-intelligence.md` |
| RFC family status | `docs/rfcs/README.md` |
| Supported feature truth | `wiki/Supported-Features.md` |
| Repository current-state truth | `REPOSITORY-ENGINEERING-CONTEXT.md` |
| Implementation-backed child RFCs | RFC-0038, RFC-0039, RFC-0040, RFC-0041, RFC-0042 bounded first-wave product path, RFC-0043 owner-side DPM workflow-pack subset |
| Remaining partial child RFCs | RFC-0043 broader copilot workspace and additional workflow-pack scope |

### Remaining Work Summary

These items remain because RFC-0037 is intentionally a strategic target-state roadmap. The correct
delivery path is to complete and prove the child RFCs and downstream/source-owner implementations,
not to mark RFC-0037 complete from roadmap text alone.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0037 |
| --- | --- | --- | --- | --- |
| RFC37-WTBD-001 | Complete RFC-0042 post-trade outcome feedback loop | `lotus-manage` plus `lotus-core`, `lotus-risk`, `lotus-performance`, `lotus-gateway`, `lotus-workbench`, `lotus-report`, `lotus-render`, `lotus-archive`, `lotus-ai` | Completed for the bounded first-wave outcome-review product path; Manage now also emits explicit no-client-communication boundary evidence; richer source-owner/OMS/PM-scoring/client-communication execution scope remains | RFC-0037 identifies outcome learning as target-state. RFC-0042 now delivers manage authority, Gateway/Workbench product realization, report/archive materialization, governed AI narrative request flow, and bounded client-communication non-claim evidence. |
| RFC37-WTBD-002 | Complete RFC-0043 governed AI PM copilot | `lotus-ai`, consumed by Gateway/Workbench/manage evidence | Completed for the bounded current product path; partial for the broader copilot workspace | `lotus-ai` now owns review-gated proof-pack PM memo, wave PM memo, outcome-review narrative, operations handoff summary, exception summary, and PM quality summary packs with guardrails and provenance, plus conservative workflow-pack default-version resolution. Gateway and Workbench now expose the operations handoff, exception-summary, and PM-quality summary invocation surfaces through governed Gateway routes. Full copilot workspace and any additional product surfaces remain future work. |
| RFC37-WTBD-003 | Full front-office DPM product realization across Gateway and Workbench | `lotus-gateway`, `lotus-workbench` | Partially implemented feature-by-feature across RFC-0038 through RFC-0043 | Multiple canonical product surfaces and first-wave AI workflow-pack invocation paths are implementation-backed, but the broader RFC-0043 copilot workspace, full portfolio memory, OMS, PM scoring, and remaining source-owner depth are not complete. |
| RFC37-WTBD-004 | Source-product depth for mandate personalization, PM-book discovery, sustainability, restrictions, risk, performance, cost, cashflow, and scenarios | `lotus-core`, `lotus-risk`, `lotus-performance`, future source owners | Deferred source-authority work | RFC-0037 requires rich private-banking source truth that cannot be fabricated in manage. |
| RFC37-WTBD-005 | Report, archive, and client/internal evidence materialization | `lotus-report`, `lotus-render`, `lotus-archive`, with Gateway/Workbench and AI posture consumers | Completed for supported proof-pack, wave, and outcome-review evidence materialization | Report-input contracts, render templates, archive lifecycle, Gateway/Workbench request posture, and AI evidence handoff paths are implemented, validated, merged, and wiki-published in the owning child RFC slices. Broader client-communication execution and any new evidence catalog families remain future owner scope. |
| RFC37-WTBD-006 | Canonical sales/demo story from implementation-backed stack evidence | `lotus-platform`, `lotus-workbench`, `lotus-gateway`, participating domain apps | Completed, merged, CI-proven, and wiki-published through `lotus-platform` PR #310 | Platform now owns a governed cross-app canonical DPM demo story tied to `PB_SG_GLOBAL_BAL_001`, canonical demo-data contracts, Workbench panel registry, platform QA, merged owner evidence, audience-specific talk track, diagrams, and explicit unsupported-claim boundaries. |
| RFC37-WTBD-007 | Portfolio memory across mandate, construction, proof-pack, wave, outcome, report, AI, and generated-document events | Cross-app, with manage as workflow/evidence participant | Partially implemented first-wave read model plus bounded Manage-local search, construction alternatives, report, AI, archive, PM-quality lineage, and structured external execution boundary evidence | Manage/Gateway/Workbench portfolio memory, bounded Manage-local `GET /api/v1/rebalance/portfolio-memory/search`, persisted construction alternative set and selected-alternative lineage, report-owned source events, AI workflow-pack source events, archive generated-document/client-delivery source events, bounded PM quality score-run and review-action lineage, explicit fail-closed `ExternalOrderExecutionAcknowledgement:v1` deferred source-event posture, and `DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY` evidence exist. Full OMS execution/acknowledgement/fill/settlement event projection, global portfolio-universe discovery, and broader cross-app source-event search/discovery remain future source-owner scope. |

### RFC37 Gold-Pass Audit And RFC Reintegration - 2026-05-09

Gold-pass assessment:

1. Truly completed: RFC37-WTBD-006 is complete as an implementation-backed canonical sales/demo
   story, RFC37-WTBD-001 is complete for the bounded RFC-0042 first-wave outcome-review product
   path, and RFC37-WTBD-005 is complete for supported proof-pack, wave, and outcome-review report,
   render, archive, and evidence handoff materialization.
2. Quality improvements made: RFC-0037 now carries the current child-roadmap support posture and no
   longer presents the supported-features ledger as entirely proposed.
3. Debt removed: stale parent-roadmap language that treated RFC-0042 product support and canonical
   demo material as future-only was corrected while keeping the strategic parent unclosed.
4. Testing and evidence proven: proof is anchored in RFC-0040/RFC-0041/RFC-0042 report-input,
   render, archive, Gateway/Workbench, AI-evidence, and canonical evidence, plus `lotus-platform`
   PR #310, merge `42e0ecff3597257ac3ea63b0c59b425603eeb291`, and wiki publication commit
   `884bec3`.
5. Expected-standard decision: completed RFC37 child-roadmap items have reached the expected
   standard on merged and wiki-published owning-repository truth. RFC-0037 remains partial only
   where future source-owner depth, full portfolio memory, OMS execution, PM scoring, client
   communication, and broader copilot workspace scope are still unimplemented.

### Detailed Follow-Up Items

#### RFC37-WTBD-001 - RFC-0042 Post-Trade Outcome Feedback Loop

Target business outcome:

Expected-versus-realized outcome evidence closes the DPM loop so future construction, monitoring,
and governance can learn from actual execution, risk, and performance outcomes.

Current implementation-backed result:

RFC-0042 is done for the `lotus-manage` backend authority and the bounded first-wave product path.
Manage now provides source-backed outcome-review preview/create/retrieve/search, immutable
persistence and append-only events, source-refresh eventing, supportability diagnostics, certified
OpenAPI, bounded report-input and AI-evidence input handoffs, and structured
`DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY` evidence proving no client-contact, client-message,
client-approval, delivery-confirmation, or communication-audit claim is made. Gateway and Workbench product
support, outcome report/archive materialization, and governed AI narrative request flow are
implemented in their owning repositories. It deliberately does not claim execution/OMS integration,
PM scoring, client communication, or richer source-owner risk/performance/tax/FX/cash
methodologies.

Why work remains:

The full RFC-0037 outcome-learning business outcome still requires source-owner enrichment beyond
the first-wave product path. Richer realized risk/performance/execution/tax/FX/cash source
methodologies must come from owning apps rather than manage-local approximation, and OMS,
PM-scoring, and client-communication support require future owners.

Dependencies before remaining work:

1. Gateway outcome-review composition over certified manage APIs,
2. Workbench outcome-review UX through Gateway/BFF only,
3. source-owner contracts for any richer realized risk, performance, execution, tax, FX, cash, or
   attribution dimensions,
4. report/render/archive implementation if generated outcome artifacts are required,
5. RFC-0043 or `lotus-ai` workflow-pack implementation for governed AI narrative over outcome
   evidence,
6. canonical front-office proof before any product-surface support claim.

Expected implementation wave:

Use the RFC-0042 manage backend as the authority. Implement remaining work in the owning apps:
Gateway first, Workbench second, then report/render/archive, AI, and source-owner enrichment as
separate governed slices.

Promotion proof:

1. Gateway and Workbench API/BFF/UI tests,
2. source-owner contract and live evidence tests for any new realized dimensions,
3. canonical front-office evidence with populated and degraded outcome-review states,
4. OpenAPI certification and supported-feature updates in every owning app,
5. wiki publication and branch cleanup after merge.

#### RFC37-WTBD-002 - RFC-0043 Governed AI PM Copilot

Target business outcome:

AI assists PMs with summarization, evidence packaging, exception narratives, and review support
without becoming the source of investment truth.

Current implementation-backed status:

RFC-0043 is no longer purely proposed. Manage provides structured evidence only, while `lotus-ai`
owns the implemented review-gated workflow-pack execution paths for:

1. `dpm_pm_memo.pack@v1` over `DpmProofPackAiEvidenceInput`,
2. `dpm_wave_pm_memo.pack@v1` over `DpmWaveReportInput`,
3. `outcome_review_narrative.pack@v1` over `DpmOutcomeAiEvidenceInput`,
4. `dpm_operations_handoff_summary.pack@v1` over Manage-owned `DpmWaveReportInput`
   handoff evidence,
5. `dpm_exception_summary.pack@v1` over bounded monitoring-exception evidence and optional
   portfolio-memory context.

The implemented packs validate forbidden actions, forbidden fields, unsupported requested outputs,
source refs, no-raw-payload posture, optional bounded `portfolio_memory_context`, review-gated run
posture, and no-reconstruction source-authority policy. Gateway and Workbench have first-wave
invocation/posture surfaces for the implemented DPM memo paths where recorded under RFC40, RFC41,
and RFC42 WTBD evidence.

What remains open:

`lotus-ai` PR #66 now implements conservative workflow-pack default-version resolution through
`GET /platform/workflow-packs/registry/{pack_id}/default`. The route resolves only registered,
activation-eligible, non-superseded versions, keeps discovered or dark successor versions
unpromoted, and exposes the resolved registration, execution binding, queue policy, and
deny-without-registration posture without changing execution semantics.

`lotus-ai` PR #67 adds owner-side operations handoff summary support through
`dpm_operations_handoff_summary.pack@v1`. The pack consumes bounded wave handoff evidence only,
requires handoff refs and source refs, rejects ambiguous `memo_request` payloads, rejects forbidden
order/routing/approval/client-message outputs, preserves `external_execution_claimed=false`, and
returns review-required support-only output.

`lotus-ai` PR #68 adds owner-side exception summary support through
`dpm_exception_summary.pack@v1`. The pack consumes bounded monitoring-exception evidence only,
requires source refs and content hashes, validates optional portfolio-memory context, rejects raw
payloads and forbidden client-message, PM-scoring, routing, approval, and execution outputs, and
returns review-required support-only output.

`lotus-gateway` PR #209 exposes exception-summary invocation at
`POST /api/v1/dpm/command-center/exceptions/{exception_id}/ai-summary` and validates the
`dpm_exception_summary.pack@v1` handoff without local summary generation. `lotus-gateway` PR #210
exposes operations-handoff invocation at
`POST /api/v1/dpm/command-center/waves/{wave_id}/operations-handoff-summary` and validates the
`dpm_operations_handoff_summary.pack@v1` handoff over Manage-owned wave evidence. `lotus-workbench`
PR #182 adds Gateway-only PM/operations actions and status display for both paths without browser
prompt construction, direct manage/AI coupling, client-message generation, PM scoring, order
routing, trade approval, or execution claims.

RFC-0043 still needs the broader copilot workspace UX, additional AI-unavailable product fallbacks
where not already implemented, and any future product surfaces in their owning apps. AI behavior
remains support-only and cannot approve, recommend, execute, score PMs, route orders, or contact
clients.

Dependencies before implementation:

1. RFC-0043 tightened to execution-grade form,
2. `lotus-ai` workflow-pack and guardrail contracts,
3. evidence input contracts from RFC-0040/RFC-0041/RFC-0042,
4. Gateway/Workbench AI posture and unavailable-state rules,
5. sensitive-field and unsupported-action tests.

Expected implementation wave:

Continue in `lotus-ai` for any additional pack families, then integrate through Gateway/Workbench
after evidence contracts are stable. Do not add direct provider calls or prompt construction to
`lotus-manage`.

Promotion proof:

1. AI guardrail/eval tests,
2. provenance and evidence-hash proof,
3. unavailable/blocked fallback evidence,
4. Gateway/Workbench integration proof if surfaced.

Gold-pass assessment - 2026-05-10:

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | DPM workflow-pack execution exists for proof-pack PM memo, wave PM memo, outcome-review narrative, operations handoff summary, exception summary, and PM quality summary; `lotus-ai` exposes conservative default-version resolution; Gateway and Workbench now expose the first-wave operations handoff and exception-summary invocation surfaces through governed Gateway routes. |
| Quality improvements made | RFC37-WTBD-002 and RFC-0043 now distinguish implemented workflow packs, registry default resolution, and first-wave product invocation from future full-copilot workspace scope instead of treating all AI work as proposed. |
| Debt removed | Stale roadmap wording that ignored merged `lotus-ai`, Gateway, and Workbench DPM copilot paths was retired from the WTBD/RFC truth. The remaining boundary is now the broader workspace and future product surfaces, not the current operations-handoff or exception-summary invocation paths. |
| What was proven through testing and evidence | Existing `lotus-ai` slices prove guardrails, source refs, review posture, no-raw-payload behavior, bounded portfolio-memory lineage, and AI-owned source-event projections. `lotus-ai` PR #66 proves default-version resolution with focused registry tests, `make check`, green Feature Lane and PR Merge Gate, and wiki publication. `lotus-ai` PR #67 proves operations handoff summary support with guardrail/stub/API tests, full `make check`, live registry/execution/guardrail API proof, clean server-log scan, green Feature Lane and PR Merge Gate including coverage and Docker build, and wiki publication. `lotus-ai` PR #68 proves exception summary support with guardrail/stub/API tests, optional portfolio-memory context validation, forbidden client-message/PM-scoring/routing/action-output coverage, local 99 percent coverage-gate proof, green Feature Lane and PR Merge Gate including coverage and Docker build, merge to main, and wiki publication. `lotus-gateway` PR #209 and PR #210 prove the governed Gateway routes with contract, unit, integration, mypy, `make check`, integration, coverage, Docker/parity CI, merge to main, and wiki publication. `lotus-workbench` PR #182 proves Gateway-only invocation and display with focused Vitest tests, typecheck, lint, docs guard, `make check`, build, Playwright smoke, Docker/parity CI, merge to main, and wiki publication. |
| Expected-standard decision | The bounded current RFC37-WTBD-002 product path reaches the expected standard: owner-side DPM workflow-pack execution, registry default resolution, and Gateway/Workbench operations-handoff plus exception-summary invocation are merged, validated, and wiki-published. The broader RFC37-WTBD-002 remains partial only for full copilot workspace and additional future product-surface requirements. |

#### RFC37-WTBD-003 - Full Front-Office DPM Product Realization

Target business outcome:

The DPM operating system is visible as a coherent front-office workflow: command center,
construction lab, proof-pack review, rebalance waves, outcome feedback, and AI assistance.

Why it cannot be done now:

Manage child RFCs have delivered backend foundations, but full product realization requires
Gateway composition, Workbench UX, canonical seed data, browser proof, and audience-ready
documentation across apps.

Dependencies before implementation:

1. Gateway compositions for RFC-0038 through RFC-0043 features,
2. Workbench panels and workflows through BFF only,
3. canonical front-office seed and validation automation,
4. backend supportability and degraded states surfaced truthfully,
5. product docs and demos backed by live evidence.

Expected implementation wave:

Execute feature by feature after the owning backend contracts are stable, then close with a
cross-app product-realization proof.

Promotion proof:

1. canonical front-office evidence pack,
2. API/BFF/browser/accessibility/visual checks,
3. demo screenshots only after validation passes,
4. wiki material for developers, business users, operations, sales/pre-sales, and client demos.

#### RFC37-WTBD-004 - Source-Product Depth For Crown-Jewel DPM

Target business outcome:

DPM decisions are based on rich private-banking source truth: mandate objectives, PM books,
benchmarks, risk/performance analytics, client restrictions, sustainability, cashflow, costs,
currency policy, and scenarios.

Why it cannot be done now:

These source products belong to domain owners. RFC-0037 correctly states the ambition but does not
make manage the source authority.

Dependencies before implementation:

1. source-owner contracts and declarations,
2. producer and consumer mesh certification where applicable,
3. manage adapters and degraded-state behavior,
4. Gateway/Workbench posture rules,
5. live proof with missing/stale/partial source states.

Expected implementation wave:

Add source depth as demanded by child RFCs and product-realization slices. Do not bundle unrelated
source families into one large manage change.

Promotion proof:

1. owner API certification,
2. manage consumer tests,
3. live/canonical evidence,
4. supported-feature updates naming the exact source products.

#### RFC37-WTBD-005 - Report, Archive, And Evidence Materialization

Target business outcome:

PM, investment committee, client, compliance, and audit audiences can receive governed documents
and archives generated from DPM evidence.

Current implementation-backed result:

Completed for the supported first-wave DPM evidence paths. RFC-0040, RFC-0041, and RFC-0042 now
provide manage-owned proof-pack, wave, and outcome-review report-input contracts; `lotus-report`,
`lotus-render`, and `lotus-archive` own deterministic generated-document and archive lifecycle for
those paths; Gateway and Workbench expose governed request posture where product-surfaced; and
`lotus-ai` consumes bounded evidence inputs for review-gated narrative assistance without becoming
report authority.

Implemented scope:

1. proof-pack report materialization from `DpmProofPackReportInput` through `lotus-render` PR #11,
   `lotus-report` PR #90, and `lotus-archive` PR #23,
2. rebalance-wave report materialization from `DpmWaveReportInput` through `lotus-manage` PR #124,
   `lotus-report` PR #91, `lotus-render` PR #12, and `lotus-archive` PR #24,
3. outcome-review report/archive materialization through RFC-0042 owning-app evidence and the
   Workbench canonical audit proof,
4. generated-document/client-delivery source-event lineage through `lotus-archive` PR #25,
5. bounded portfolio-memory report lineage through `lotus-report` PR #92 and report-owned
   source-event publication through `lotus-report` PR #93,
6. governed AI evidence handoffs for proof-pack PM memo, wave PM memo, and outcome-review narrative
   packs without raw payload reconstruction or autonomous decisioning.

Explicit boundaries:

1. `lotus-manage` remains evidence and report-input authority; it does not generate, render,
   archive, retrieve, or retain documents,
2. report/render/archive do not create investment recommendations beyond the source evidence they
   receive,
3. this closure does not claim client communication execution, external OMS execution, PM quality
   scoring, autonomous AI decisions, or new evidence catalog families,
4. any future client/internal evidence artifact family still needs an owning RFC, source contract,
   generated-document lifecycle, archive policy, and product-surface proof.

Promotion proof:

1. RFC40-WTBD-004 proves proof-pack report/render/archive materialization with owning-repository
   PR evidence,
2. RFC41-WTBD-008 proves rebalance-wave report/render/archive materialization with owning-repository
   PR evidence,
3. RFC42-WTBD-004 proves outcome-review report/render/archive materialization and canonical
   product posture,
4. RFC40-WTBD-005, RFC41-WTBD-009, and RFC42-WTBD-005 prove governed AI evidence handoff paths,
5. RFC40-WTBD-010 proves bounded report-lineage source events in `lotus-report` and
   generated-document/client-delivery source events in `lotus-archive`.

Gold-pass assessment - 2026-05-10:

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | Supported proof-pack, wave, and outcome-review evidence now flow from manage-owned report inputs into generated report, render, archive, Gateway/Workbench request posture, AI evidence handoff, and report/archive lineage families. |
| Quality improvements made | RFC-0037 now names the completed report/archive evidence families explicitly instead of leaving the parent roadmap in a partial state despite child RFC completion. |
| Debt removed | Stale wording that treated report, archive, and evidence materialization as future-only was retired, while source-owner and client-communication boundaries remain explicit. |
| What was proven through testing and evidence | Proof is anchored in the merged RFC40/RFC41/RFC42 child slices, their local and GitHub gates, canonical Workbench evidence where product-surfaced, report/render/archive owning PRs, AI evidence handoff PRs, and documentation regression coverage. |
| Expected-standard decision | RFC37-WTBD-005 reaches the expected standard for supported first-wave evidence materialization. Broader client/internal evidence catalog expansion remains future owner scope and is not claimed. |

#### RFC37-WTBD-006 - Canonical Sales/Demo Story

Target business outcome:

Sales, pre-sales, marketing, client demos, operations, and engineering can show the crown-jewel DPM
story using real canonical stack evidence rather than screenshots disconnected from backend truth.

Current implementation-backed result:

Completed on merged, validated, and wiki-published platform truth through `lotus-platform` PR #310.
The platform now provides `docs/demo/canonical-dpm-demo-story.md` and
`wiki/Canonical-DPM-Demo-Story.md` as the governed cross-app demo story for
`PB_SG_GLOBAL_BAL_001`. The material is tied to the canonical demo-data contract, invariants
contract, Workbench panel registry, platform canonical front-office QA wrapper, and owning-app
implementation evidence. It includes audience-specific guidance for business users, operations,
engineering, sales/pre-sales, and client demos; diagrams for integration and demo flow; current
functional and non-functional capability matrices; and explicit no-claim boundaries for external
OMS execution, PM quality scoring, client communication execution, autonomous AI decisioning, local
Workbench recomputation, and unimplemented degraded/blocked command-center seed fixtures.

Implementation proof:

1. `lotus-platform` PR #310,
2. `lotus-platform` merge commit `42e0ecff3597257ac3ea63b0c59b425603eeb291`,
3. `lotus-platform` wiki publication commit `884bec3`,
4. focused platform proof:
   `python -m pytest tests/unit/test_canonical_dpm_demo_story.py tests/unit/test_front_office_runtime_automation_contract.py tests/unit/test_rfc_0076_canonical_demo_data_contract.py tests/unit/test_rfc_0077_panel_registry_contract.py -q`,
5. GitHub Feature Lane and PR Merge Gate checks passed for PR #310.

Ongoing operating rule:

Extend the canonical demo story as new product surfaces become implementation-backed, but do not
claim unsupported source-owner features before their owning repositories merge proof and publish
wiki truth.

Future enrichment rules:

1. screenshots remain demo-ready only after canonical API, calculation, panel, and browser
   validation pass,
2. new demo claims must link to implementation evidence in owning repositories,
3. external OMS execution, PM scoring, client communication execution, and richer source-owner
   methodology depth remain out of the demo story until separately implemented.

#### RFC37-WTBD-007 - Portfolio Memory Across The DPM Lifecycle

Target business outcome:

Lotus preserves a durable, searchable, governed decision memory across mandate health,
construction, proof packs, rebalance waves, execution outcomes, reports, and AI evidence.

Current implementation-backed result:

The first-wave portfolio-memory path is implementation-backed across Manage, Gateway, Workbench,
report, AI, archive, construction alternatives, and PM operating quality score-run lineage. Manage
composes persisted mandate health snapshots, monitoring exceptions, construction alternative set
generation, selected-alternative decisions, proof packs, proof-pack decision timeline events,
rebalance wave events, internal operations handoffs, outcome-review events, and bounded
`PM_QUALITY_SCORE_RUN` lineage into a deterministic no-raw-payload timeline. Report, AI, and
archive publish their own source-event family postures, while Manage records source-family posture
without reconstructing their events.

Manage now also exposes `GET /api/v1/rebalance/portfolio-memory/search` as a bounded
Manage-local portfolio-memory index over persisted proof packs, rebalance waves, monitoring
exceptions, outcome reviews, and explicit caller-supplied portfolio identifiers. The index returns
summary counts, latest event posture, supportability, source systems, reason codes, and content
hashes without discovering the global portfolio universe, querying external source-owner event
stores, projecting OMS acknowledgement/fill/settlement events, or recalculating source truth.

The construction-memory slice adds `CONSTRUCTION_ALTERNATIVE_SET` and
`CONSTRUCTION_ALTERNATIVE_SELECTED` events from the persisted RFC-0039 construction repository.
The projection preserves alternative set id, selected alternative id, method counts, input mode,
request hash/content hash posture, source-supportability state, actor, correlation id, and bounded
selection reason without copying raw request payloads, raw selection payloads, or recalculating
construction, risk, performance, tax, cash, FX, or execution methodology.

The read model now also names `external_order_execution_acknowledgement` as a deferred
source-event family tied to Core `ExternalOrderExecutionAcknowledgement:v1`. That source product
is consumed only as fail-closed construction and outcome evidence. The portfolio-memory response
now also emits structured `DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY` evidence with blocked
capabilities, required future execution/OMS owner, required
`ExternalOrderExecutionAcknowledgement:v1` source product, and deterministic content hash;
portfolio memory does not project acknowledgement, fill, settlement, or execution-status events
until bank-owned OMS acknowledgement ingestion publishes a certified no-raw-payload source-event
family.

Why work remains:

RFC-0037's full portfolio-memory ambition still needs global portfolio-universe discovery, broader
cross-app source-event discovery and search, source-owner events outside persisted Manage evidence,
and bank-owned OMS execution/acknowledgement/fill/settlement event families. Those cannot be
fabricated in Manage from source-product supportability posture.

Dependencies before implementation:

1. event identity and retention policy across child RFCs,
2. broader cross-app event discovery beyond first-wave family posture,
3. certified source-owner construction and execution event families,
4. richer Gateway/Workbench timeline/search UX,
5. bank-owned OMS acknowledgement, fill, settlement, and reconciliation source-event contracts.

Expected implementation wave:

Continue as small owner-scoped slices. Manage can harden timeline composition, evidence posture,
and no-raw-payload family declarations; report, AI, archive, Gateway, Workbench, and future OMS
owners must own their source events and product surfaces.

Promotion proof:

1. event reconciliation tests,
2. timeline/search API and UI proof,
3. access/redaction tests,
4. canonical evidence and documentation.

### Suggested Sequencing

Recommended order:

1. tighten and implement RFC-0042,
2. tighten and implement RFC-0043 with `lotus-ai`,
3. complete Gateway/Workbench realization for RFC-0038 through RFC-0043,
4. add source-product depth in owning apps as specific product claims require it,
5. implement report/render/archive evidence materialization,
6. extend the canonical sales/demo story as new supported surfaces land,
7. close portfolio-memory as a cross-RFC product capability.

### RFC-0037 Promotion Checklist For Any Future Item

Before any RFC-0037 target-state item moves into a supported-feature claim:

1. owning child RFC or downstream/source-owner RFC is implementation-backed,
2. source ownership remains explicit,
3. Gateway and Workbench consume through the governed product path,
4. proof exists beyond roadmap language,
5. docs/wiki/supported-features distinguish backend foundation from full product realization,
6. canonical evidence supports demo/pitch material,
7. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.

## RFC-0038 - Mandate Digital Twin, Health Score, And DPM Command Center Foundation

Current closure status:

RFC-0038 delivered the implementation-backed `lotus-manage` backend foundation for mandate digital
twins, deterministic mandate health, monitoring exceptions, monitoring runs, and a bounded DPM
command-center summary. The supported scope is backend/API foundation: source-mapped refresh/read,
version, diff, health read/recalculate, monitoring run, exception, and command-center APIs with
in-memory and PostgreSQL persistence, OpenAPI certification, local live proof, local canonical
manage plus live `lotus-core` proof, README/wiki/supported-feature updates, and published wiki
truth.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0038-mandate-digital-twin-health-and-command-center.md` |
| Source-data field map | `docs/rfcs/RFC-0038-source-data-field-map.md` |
| Supported feature claims | `wiki/Supported-Features.md` mandate digital-twin, monitoring, exceptions, and command-center rows |
| Manage live proof | `output/rfc0038-live-proof/20260503T063617Z/summary.json` |
| Manage implementation | `src/core/mandates.py`, `src/core/mandate_repository.py`, `src/api/services/mandate_service.py`, `src/api/routers/mandates.py`, `src/api/routers/monitoring.py`, `src/infrastructure/mandates/` |
| Tests | `tests/unit/dpm/core/test_mandate_health.py`, `tests/unit/dpm/api/test_mandates_api.py`, `tests/unit/dpm/api/test_monitoring_api.py`, `tests/unit/dpm/supportability/test_dpm_mandate_repository.py` |
| Downstream handoff | `docs/architecture/dpm-command-center-gateway-workbench-handoff.md`, `sgajbi/lotus-gateway#180`, `sgajbi/lotus-workbench#140`, `sgajbi/lotus-platform#294` |

### Remaining Work Summary

These items are deliberately not done in RFC-0038 because the RFC delivered manage backend
foundation, while full command-center product realization, PM-book discovery, richer source
products, and canonical seed automation belonged to downstream or source-owning applications.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0038 |
| --- | --- | --- | --- | --- |
| RFC38-WTBD-001 | Gateway DPM command-center composition | `lotus-gateway` | Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #194 | Gateway now composes RFC-0038 mandate command-center, monitoring, exception, and mandate drill-down truth from manage without becoming mandate-health authority. |
| RFC38-WTBD-002 | Workbench DPM cockpit panels | `lotus-workbench` | Completed, merged, CI-proven, live-proven, and wiki-published through `lotus-workbench` PR #154 | Workbench consumes Gateway/BFF command-center contracts only, renders manage-owned supportability/source readiness/health truth without recomputation, and originally recorded the canonical seed gap that RFC38-WTBD-003 later resolved for the populated governed portfolio. |
| RFC38-WTBD-003 | Platform canonical seed automation for populated command-center proof | `lotus-platform` with source-app seeds | Completed, merged, CI-proven, live-proven, wiki-published, and hardened locally for populated ready/partial/empty seed posture checks | Platform canonical automation refreshes the governed DPM mandate from core through manage, runs one monitoring pass for command-center evidence, verifies Manage and Gateway mandate/health/summary reads, and runs canonical Workbench validation with `dpm.command_center` classified from Manage supportability. The current hardening adds platform seed `posture_checks` for populated source-ready `ready`, selector-driven `partial`, and empty-date `empty` command-center states. Degraded and blocked canonical fixtures remain source-owner follow-up rather than demo-ready claims. |
| RFC38-WTBD-004 | PM-book discovery for monitoring and command-center cohorts | `lotus-core` source authority consumed by `lotus-manage`, surfaced through `lotus-gateway` and `lotus-workbench` | Completed in this slice for populated source-owned PM-book monitoring cohorts | Manage monitoring run-once can now resolve PM-book cohorts from `PortfolioManagerBookMembership:v1` when callers omit mandate IDs. Workbench command-center monitoring uses that source-owned path by default. Populated ready/partial/empty seed-posture checks are now covered by RFC38-WTBD-003 hardening; degraded/blocked fixtures remain source-owner follow-up, not a blocker for populated PM-book monitoring support. |
| RFC38-WTBD-005 | Mandate objective, benchmark, review cadence, and model-change source products | `lotus-core` source authority consumed by `lotus-manage`; CIO/model source authority via RFC-0041 | Completed for first-wave source-owned mandate twin enrichment | Core `DiscretionaryMandateBinding:v1` now exposes mandate objective, review cadence, last review date, and next review due date with supportability degradation when missing. Manage consumes those fields into the mandate twin and review-cadence health scoring, consumes `BenchmarkAssignment:v1` for `benchmark_id`, and keeps fallback gap codes explicit when source fields are absent. CIO model-change source ownership is already implementation-backed through `CioModelChangeAffectedCohort:v1` and RFC-0041. Broader performance benchmark analytics remain a separate risk/performance enrichment boundary. |
| RFC38-WTBD-006 | Client restriction, sustainability, cashflow, income-needs, reserve, and withdrawal source products | `lotus-core` source authority consumed by `lotus-manage` | Completed for first-wave manage mandate-health consumption | Mandate refresh consumes `ClientRestrictionProfile:v1`, `SustainabilityPreferenceProfile:v1`, `PortfolioCashflowProjection:v1`, `ClientIncomeNeedsSchedule:v1`, `LiquidityReserveRequirement:v1`, and `PlannedWithdrawalSchedule:v1` when available, preserves source lineage, removes only fulfilled field-gap codes, degrades explicitly when optional profiles are unavailable, blocks restricted active model targets, flags sustainability preferences as review-required, and raises bounded cash-liquidity attention from source-owned cashflow evidence. Manage preserves client-liquidity reference products as supportability evidence only; issuer/sector restriction joins, security-level sustainability classification, financial-planning advice, funding recommendations, client liability planning, OMS instruction, regulatory suitability approval, and downstream UI profile-detail presentation remain outside this support claim. |
| RFC38-WTBD-007 | Broader risk and performance health enrichment | `lotus-risk`, `lotus-performance` | Deferred unless owning-service contracts are consumed | Manage health cannot clone risk or performance methodology. Risk/performance attention must come from certified owners. |
| RFC38-WTBD-008 | Full front-office command-center product support | `lotus-gateway`, `lotus-workbench`, `lotus-platform`, with manage as backend foundation | Completed, merged, live-proven, and wiki-published | Backend authority, Gateway composition, Workbench cockpit rendering, canonical seed automation, PM-book discovery, populated ready proof, selector-driven partial proof, empty-date proof, and demo-ready screenshot evidence are implementation-backed. Degraded/blocked canonical fixtures, richer source-product details, and profile-detail UI remain separate source-owner or product-depth scope. |

### Detailed Follow-Up Items

#### RFC38-WTBD-001 - Gateway DPM Command-Center Composition

Target business outcome:

Gateway exposes a product-facing DPM command-center contract that composes mandate digital twins,
health, monitoring runs, active exceptions, supportability, and drill-down links while preserving
`lotus-manage` as the health and monitoring authority.

Closure status:

Completed on 2026-05-06 through `lotus-gateway` PR #194,
`feat: expose DPM mandate command center`, merged to `main` at
`ee2d80684e9219c1ff42f8660f4a0ff4e97abf08`.

What was delivered:

1. Gateway now exposes a Workbench-facing RFC-0038 route family under
   `/api/v1/dpm/command-center`, `/api/v1/dpm/command-center/monitoring/*`,
   `/api/v1/dpm/command-center/exceptions*`, and
   `/api/v1/dpm/command-center/mandates*`.
2. `lotus-gateway` added typed `DpmClient` methods for manage command-center summary, monitoring
   run/create/search/detail, exception search/resolution, mandate-by-portfolio, mandate detail,
   mandate health, and mandate diff APIs.
3. Gateway wraps manage responses in a product BFF envelope with upstream status, correlation id,
   and manage-derived supportability while preserving the authoritative manage payload.
4. Gateway does not discover PM-book membership, calculate mandate health, reconstruct health
   dimensions, infer source readiness, merge exceptions across monitoring runs, or resolve
   exceptions locally.
5. Gateway repository context, RFC-0098, and repo-authored wiki source were updated. The
   `lotus-gateway` wiki was published after merge at wiki commit `5901cd8` and check-only
   verification reported zero drift.

Validation evidence:

1. Focused local proof passed:
   `python -m pytest tests/contract/test_dpm_command_center_contract.py tests/unit/test_dpm_command_center_service.py tests/integration/test_dpm_command_center_router.py tests/unit/test_upstream_clients.py::test_dpm_client_rfc38_command_center_routes -q`
   with 36 tests.
2. Local repo gate `make check` passed in `lotus-gateway`, including Ruff lint, Ruff format check,
   monetary-float guard, mypy, Workbench contract smoke, and 439 unit/contract tests.
3. GitHub PR #194 checks passed before merge: Feature Lane lint/typecheck/unit, Feature Lane
   workflow lint, PR Merge Gate workflow lint, lint/typecheck/unit, integration tests, coverage
   gate, Docker build validation, CI local Docker parity, and queue auto-merge.
4. `Sync-RepoWikis.ps1 -Publish -Repository lotus-gateway` published the changed API,
   integrations, and supported-feature pages after merge; `Sync-RepoWikis.ps1 -CheckOnly
   -Repository lotus-gateway` then reported diff count 0.

Gold-pass assessment:

This WTBD has reached the expected standard for the Gateway composition slice. The route family is
merged to `main`, pinned by client/service/router/OpenAPI tests, documented in Gateway RFC/wiki
truth, and published to the Gateway wiki. Full Workbench cockpit product support is not claimed
here and remains RFC38-WTBD-002.

#### RFC38-WTBD-002 - Workbench DPM Cockpit Panels

Target business outcome:

PMs and operations users can view mandate health, source readiness, attention queues, recommended
actions, latest monitoring run, and mandate drill-downs through a populated Workbench cockpit.

Closure status:

Completed on 2026-05-06 through `lotus-workbench` PR #154,
`Implement RFC38 DPM command-center cockpit`, merged to `main` at
`2fbfac5dd00104cee2b1da7923efe0c64940a9f5`.

What was delivered:

1. `/workbench/{portfolioId}` now renders an embedded DPM Command Center cockpit for the canonical
   front-office portfolio.
2. Workbench consumes the Gateway command-center route family only:
   `GET /api/v1/dpm/command-center`,
   `POST /api/v1/dpm/command-center/monitoring/run-once`,
   `GET /api/v1/dpm/command-center/exceptions`,
   `GET /api/v1/dpm/command-center/mandates/by-portfolio/{portfolio_id}`, and
   `GET /api/v1/dpm/command-center/mandates/{mandate_id}/health`.
3. The Workbench view model preserves Gateway/manage supportability, source readiness, health
   distribution, attention buckets, recommended actions, active exceptions, latest monitoring-run
   lineage, and mandate-health dimensions without calculating mandate health, supportability, or
   source readiness in browser code.
4. The run-monitoring action calls the Gateway BFF mutation path and sends governed DPM context
   for tenant `default`, PM `PM_SG_DPM_001`, book `BOOK_SG_BALANCED_DPM`, and as-of date
   `2026-05-03`.
5. Bounded observability surfaces were added for command-center summary, monitoring, exception,
   mandate binding, and mandate-health operations without leaking portfolio ids, PM ids, mandate
   ids, run ids, or exception ids into metric labels.
6. `lotus-workbench` repository context, RFC-0098, and repo-authored wiki source were updated.
   The `lotus-workbench` wiki was published after merge at wiki commit `86b6ee7`; check-only
   verification then reported zero drift.

Validation evidence:

1. Focused Workbench proof passed:
   `npx vitest run tests/unit/live-canonical-validation-script.test.ts tests/unit/live-validation-browser-workflows.test.ts tests/unit/dpm-command-center-panel.test.tsx tests/unit/dpm-command-center-view-model.test.ts tests/unit/workbench-api.test.ts`
   with 60 tests.
2. Local repo gate `make check` passed in `lotus-workbench`, including lint, typecheck, coverage
   tests, and production build.
3. Canonical front-office live validation passed:
   `powershell -ExecutionPolicy Bypass -File scripts/live/Start-LotusFrontOfficeCanonical.ps1 -LocalApps workbench,gateway -RunValidation -ScreenshotDirectory output/rfc38-wtbd002-command-center-cockpit-command-center-validated`.
4. Structured live evidence:
   `lotus-workbench/output/rfc38-wtbd002-command-center-cockpit-command-center-validated/live-validation-summary.json`
   proves Gateway command-center summary status 200, active exceptions status 200, and populated UI
   checks for DPM command-center health distribution, attention queue, active exceptions, and
   mandate health dimensions.
5. GitHub PR #154 checks passed before merge: Feature Lane workflow lint, Feature Lane lint/typecheck/test,
   PR Merge Gate workflow lint, lint/typecheck/coverage/build, Playwright smoke, Docker build
   validation, and CI local Docker parity.

Seed gap resolution:

The historical canonical
`GET /api/v1/dpm/command-center/mandates/by-portfolio/PB_SG_GLOBAL_BAL_001` seed gap was resolved
by RFC38-WTBD-003 platform automation on 2026-05-07. Workbench still preserves `seed_gap`
classification for non-populated or incomplete environments, but the governed canonical runtime now
proves the populated command-center path as `ready`.

Gold-pass assessment:

This WTBD has reached the expected standard for the Workbench cockpit slice. The implementation is
merged to `lotus-workbench` `main`, proven by Feature Lane and PR Merge Gate, locally live-proven
through the canonical Workbench runtime, and documented in repo context plus published wiki source.
The Workbench cockpit panel itself is implementation-backed. RFC38-WTBD-003 later resolved the
populated canonical seed gap; later richer product slices still govern PM-book discovery and
partial/empty command-center fixture depth.

#### RFC38-WTBD-003 - Platform Canonical Seed Automation

Target business outcome:

The canonical front-office stack can reliably seed and validate a populated DPM command-center state
for demo, QA, and regression proof.

Closure status:

Completed on 2026-05-07 through coordinated PRs:

1. `lotus-platform` PR #304 merged to `main` as `cdbc489` and published
   `lotus-platform.wiki` commit `fa3216a`,
2. `lotus-workbench` PR #155 merged to `main` as `cad5302`,
3. `lotus-manage` PR #113 merged to `main` as `7579a01` and published
   `lotus-manage.wiki` commit `27b1071`.

What was delivered:

1. `lotus-platform` added canonical DPM command-center seed identity to
   `canonical-front-office-demo-data-contract.json` for `PB_SG_GLOBAL_BAL_001`,
   `MANDATE_PB_SG_GLOBAL_BAL_001`, `PM_SG_DPM_001`, `BOOK_SG_BALANCED_DPM`, tenant `default`,
   booking center `Singapore`, model `MODEL_PB_SG_GLOBAL_BAL_DPM`, policy pack
   `POLICY_DPM_SG_BALANCED_V1`, and as-of date `2026-05-03`.
2. `lotus-platform` added `Invoke-DpmCommandCenterSeed.ps1`, which refreshes the canonical mandate
   from `lotus-core` through `lotus-manage`, verifies manage lookup by portfolio, verifies Gateway
   mandate lookup by portfolio, verifies Gateway mandate health, and verifies the Gateway
   command-center summary.
3. `Invoke-Canonical-FrontOffice-QA.ps1` now runs the DPM command-center seed before Workbench
   validation by default and records DPM seed evidence in the canonical front-office QA summary.
4. The canonical data invariants, Workbench panel registry, analytics UI observability readiness
   contract, and platform automation docs were updated to include `dpm.command_center`.
5. `lotus-workbench` live validation now classifies `dpm.command_center` as a governed ready panel
   and captures the registered DPM command-center screenshot during canonical browser validation.

Validation evidence:

1. Platform focused tests passed:
   `python -m pytest tests/unit/test_analytics_ui_rollout_readiness.py tests/unit/test_rfc_0076_canonical_demo_data_contract.py tests/unit/test_rfc_0077_panel_registry_contract.py tests/unit/test_front_office_runtime_automation_contract.py -q`
   with 15 tests.
2. Workbench focused tests passed:
   `npm test -- --run tests/unit/live-canonical-validation-script.test.ts tests/unit/live-validation-browser-workflows.test.ts`
   with 13 tests.
3. Governed canonical runtime proof passed:
   `powershell -ExecutionPolicy Bypass -File automation\Invoke-Canonical-FrontOffice-QA.ps1 -BringUp -LotusAiEnvFile .env.example -SeedWaitSeconds 1200`.
4. Structured DPM seed evidence:
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260507-013324.json` and
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-latest.json` show status `ok`
   for manage refresh, manage lookup, Gateway mandate lookup, Gateway mandate health, and Gateway
   command-center summary.
5. Structured canonical QA evidence:
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-012800.json` and
   `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json` prove live
   canonical Workbench validation passed for `PB_SG_GLOBAL_BAL_001`, with screenshots under
   `lotus-workbench/output/playwright/live-canonical`.

Remaining governed follow-up:

Populated ready, selector-driven partial, and empty command-center state automation is now claimed
at the platform seed contract layer. The canonical Workbench panel records the current canonical
PM/book/as-of command center as `READY` while preserving degraded and blocked states as explicit
non-ready behavior. Degraded and blocked canonical seed fixtures require source-owner fixture
support before they can be promoted as durable demo or regression scenarios.

#### RFC38-WTBD-004 - PM-Book Discovery For Monitoring And Command-Center Cohorts

Target business outcome:

The DPM command center can populate by PM book or portfolio-manager cohort without requiring
callers to supply every mandate or portfolio id manually.

Current status:

Completed in this slice for populated, source-owned PM-book monitoring cohorts.
`PortfolioManagerBookMembership:v1` already exists in `lotus-core`; `lotus-manage` now consumes it
directly when `/api/v1/dpm/monitoring/run-once` receives no explicit `mandate_ids` and has a
`portfolio_manager_id` selector. The command-center run records the PM, book, tenant, booking
center, core product, core product version, supportability state, snapshot id, and source content
hash in the monitoring-run filters so command-center reads can tie the populated cohort back to
source authority.

What was delivered:

1. Manage preserves the existing explicit mandate-id path for backward-compatible bounded runs.
2. Manage requires either explicit `mandate_ids` or `portfolio_manager_id`, and rejects missing
   selectors with `DPM_MONITORING_SELECTOR_REQUIRED`.
3. Manage resolves source-owned PM-book members through `lotus-core`
   `PortfolioManagerBookMembership:v1` with tenant, booking-center, as-of date, eligible portfolio
   type, and `include_inactive=false` filters.
4. Manage maps source unavailability to dependency errors instead of fabricating a cohort.
5. Manage blocks non-ready PM-book membership, empty PM-book membership, and PM-book members whose
   refreshed RFC-0038 mandate twin is not present.
6. Workbench command-center monitoring no longer sends a single mandate fallback; the embedded
   command-center action lets Gateway/Manage resolve the PM-book cohort from source truth.
7. Gateway remains a pass-through product BFF for the monitoring body and does not become PM-book
   authority.

Validation evidence:

1. Manage focused proof:
   `python -m pytest tests/unit/dpm/api/test_monitoring_api.py -q`.
2. Manage static proof:
   `python -m ruff check src/api/routers/monitoring.py src/api/services/mandate_service.py tests/unit/dpm/api/test_monitoring_api.py`.
3. Workbench focused proof:
   `npm test -- --run tests/unit/workbench-api.test.ts tests/unit/dpm-command-center-panel.test.tsx`.
4. Documentation and API-governance proof are required before merge through the docs current-state
   tests, API vocabulary/no-alias gate, wiki check-only, and PR CI.

Remaining governed follow-up:

This WTBD closes the source-owned populated PM-book monitoring path. The separate command-center
seed hardening now proves populated ready, selector-driven partial, and empty platform seed
postures. It still does not claim degraded, blocked, or permission-denied PM-book fixtures because those require
source-owner fixture support, Workbench browser assertions, and screenshot/evidence registration
beyond the populated command-center path.

### RFC38 Gold-Pass Audit And RFC Reintegration - 2026-05-09

Current decision:

RFC38-WTBD-001, RFC38-WTBD-002, RFC38-WTBD-003, and RFC38-WTBD-004 remain complete after
slice-by-slice audit. Their implementation truth has been incorporated into RFC-0038 so the
completed command-center product path is not stranded only in this WTBD ledger.

What was truly completed:

1. Gateway composes the manage-owned DPM command-center route family without becoming mandate,
   source-readiness, or monitoring authority.
2. Workbench renders the DPM command-center cockpit through Gateway/BFF only, including health
   distribution, attention queue, active exceptions, mandate-health dimensions, and monitoring
   action posture.
3. Platform canonical seed automation proves the populated command-center path and records
   ready, partial, and empty seed posture checks.
4. Manage PM-book monitoring can resolve populated cohorts from lotus-core
   `PortfolioManagerBookMembership:v1` instead of requiring caller-supplied mandate lists.

Quality improvements made:

1. RFC-0038 now reflects completed Gateway, Workbench, platform seed, and PM-book follow-ons
   instead of pointing to stale downstream issue links.
2. Wiki source now contains an audience-aware command-center flow diagram, current feature
   behavior, non-functional controls, and demo boundaries.
3. The documentation regression guard now pins RFC38 WTBD reintegration, exact canonical evidence
   artifacts, and wiki command-center material.

Debt removed:

1. stale RFC wording that treated merged downstream command-center work as open,
2. ambiguity between backend-only RFC closure and full first-wave product realization,
3. screenshot-only proof risk by tying demo readiness to machine-readable seed and panel evidence.

Testing and evidence:

1. `lotus-manage` RFC38 focused proof passed: 61 tests across mandate health, mandates API,
   monitoring API, and mandate repository supportability tests.
2. `lotus-manage` PM-book core-sourcing proof passed: 1 selected PM-book test in
   `tests/unit/dpm/infrastructure/test_core_sourcing_client.py`.
3. Ruff static proof passed for command-center routers/services, core-sourcing client, and related
   tests.
4. Canonical front-office QA passed at
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260509-214551.json` with
   DPM command-center seed status `ok`.
5. Screenshot evidence is retained at
   `lotus-platform/output/front-office-qa/wtbd-rfc36-audit-20260509-214550/dpm-command-center-live.png`.
6. Seed evidence is retained at
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260509-220332.json` and proves
   populated ready, selector-driven partial, and empty-date command-center postures.

Expected-standard decision:

The completed RFC38 WTBDs have genuinely reached the expected first-wave standard for backend
authority, Gateway composition, Workbench command-center product realization, platform seed
automation, and PM-book cohort discovery. Remaining source-product, degraded-fixture,
permission-denied fixture, and richer health-enrichment work stays separate WTBD scope.

#### RFC38-WTBD-005 - Mandate Objective, Benchmark, Review Cadence, And Model-Change Sources

Target business outcome:

Mandate twins and health scores can use source-backed objective profiles, benchmark bindings,
review cadence, last/next review dates, and CIO model-change lifecycle rather than local defaults or
gap-coded nulls.

Implementation result:

Completed for first-wave source-owned mandate twin enrichment on 2026-05-10.
`lotus-core` enriches `DiscretionaryMandateBinding:v1` with mandate objective, review cadence,
last review date, and next review due date; missing objective or review-cycle fields degrade
supportability rather than appearing source-ready. `lotus-manage` consumes those fields into
`DpmMandateDigitalTwin`, removes the corresponding field-gap codes only when source fields are
present, and uses `next_review_due_date` for review-cadence health scoring.

Implemented behavior:

1. `mandate_objective` becomes the source-backed twin `investment_objective`,
2. absent objective preserves `LONG_TERM_TOTAL_RETURN` only with
   `MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED`,
3. `review_cadence`, `last_review_date`, and `next_review_due_date` populate
   `DpmMandateReviewPolicy`,
4. absent cadence or next due date preserves explicit
   `MANDATE_REVIEW_SCHEDULE_NOT_YET_SOURCED`,
5. `BenchmarkAssignment:v1` sets `DpmMandateDigitalTwin.benchmark_id` and adds benchmark lineage,
6. CIO model-change source ownership remains the completed `CioModelChangeAffectedCohort:v1`
   source path consumed by RFC-0041 waves.

Explicit boundaries:

1. manage does not calculate benchmark performance, active return, attribution, or risk impact,
2. benchmark analytics remain `lotus-performance` / `lotus-risk` enrichment scope,
3. manage-owned review workflow history beyond source review dates remains future operational
   workflow depth,
4. the fallback objective is retained only as a gap-coded compatibility posture.

Promotion proof:

1. `lotus-core` focused source-product proof passed with 156 tests,
2. `lotus-core` OpenAPI, source-data, domain-product, route-family, and API-vocabulary guards
   passed,
3. `lotus-manage` focused source-consumption proof passed with 94 tests,
4. platform domain-product mirror validation passed after syncing the core declaration.

Gold-pass assessment:

| Question | Assessment |
| --- | --- |
| What was truly completed | First-wave mandate objective, review-cycle, benchmark-binding, and model-change source truth is implementation-backed across core and manage. |
| Quality improvements | Manage no longer treats source-ready mandate objective/review fields as local defaults, and benchmark id now comes from a source product. |
| Debt removed | Stale field-map and WTBD wording that treated objective/review/benchmark as wholly unsourced has been retired. |
| What was proven | Focused core tests, manage tests, source-product guards, OpenAPI/API-vocabulary guards, and platform domain-product validation passed. |
| Expected-standard decision | RFC38-WTBD-005 reaches the expected first-wave standard for source-owned mandate twin enrichment; broader risk/performance analytics remain RFC38-WTBD-007. |

#### RFC38-WTBD-006 - Client Restriction, Sustainability, And Cashflow Source Products

Target business outcome:

Mandate health can assess restriction, sustainability, liquidity, income-need, and cashflow risks
from source-backed client and portfolio profiles.

Implementation result:

Completed for first-wave manage mandate-health consumption on 2026-05-10. `lotus-core` now owns
the implemented source products `ClientRestrictionProfile:v1`,
`SustainabilityPreferenceProfile:v1`, and `PortfolioCashflowProjection:v1`; `lotus-manage`
mandate refresh consumes them opportunistically, preserves lineage, and keeps explicit gap codes
only when a source product is absent.

Implemented behavior:

1. active client restriction profile instrument restrictions are copied to the mandate twin and
   assessed against active model targets,
2. restricted active model targets block `ELIGIBILITY_RESTRICTIONS` with
   `RESTRICTED_INSTRUMENT_HELD`,
3. active sustainability preference profiles preserve framework and preference codes on the twin,
4. sustainability allocation, exclusion, or positive-tilt preferences move workflow readiness to
   `PENDING_REVIEW` with `SUSTAINABILITY_REVIEW_REQUIRED`,
5. negative `PortfolioCashflowProjection:v1.total_net_cashflow` creates
   `PROJECTED_CASHFLOW_PRESSURE` when current cash is otherwise within mandate bands,
6. unavailable optional source products degrade source readiness and keep gap codes instead of
   fabricating client-governance or cashflow facts.

Explicit boundaries:

1. `PortfolioCashflowProjection:v1` is not a client income-needs profile,
2. manage does not infer issuer, sector, jurisdiction, or ESG-security classifications without a
   source-owned join,
3. manage does not claim regulatory suitability approval or automatic ESG compliance,
4. downstream Gateway/Workbench profile-detail presentation remains a product-surface follow-up.

Promotion proof:

1. `lotus-manage` PR #180 merged to `main` on 2026-05-10 with green Feature Lane and PR Merge Gate
   checks, including unit, integration, e2e, 99 percent coverage, and Docker build validation,
2. local proof passed `python -m pytest tests/unit/dpm/construction/test_enrichment.py
   tests/unit/dpm/infrastructure/test_core_sourcing_client.py
   tests/unit/dpm/core/test_mandate_health.py -q` with 68 tests,
3. local full coverage proof passed `python -m pytest --cov=src --cov-report=term
   --cov-fail-under=99 -q` with 1,264 tests, 2 warnings, and 99.03 percent total coverage,
4. tests prove lineage preservation, gap-code removal, optional-source degradation, restricted
   target blocking, sustainability review posture, projected cashflow pressure, source-context
   lifting into construction evidence, restriction-scope matching, and source-safe resolver errors,
5. RFC-0038 and `docs/rfcs/RFC-0038-source-data-field-map.md` now contain the completed WTBD truth,
6. `lotus-manage` wiki publication completed from repo-authored source and
   `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-manage` returned zero drift.

Gold-pass assessment:

| Question | Assessment |
| --- | --- |
| What was truly completed | First-wave mandate-health consumption of `ClientRestrictionProfile:v1`, `SustainabilityPreferenceProfile:v1`, and `PortfolioCashflowProjection:v1` is implemented, merged, CI-green, and wiki-published. |
| Quality improvements made | Optional source products now have source-safe degraded handling, source lineage preservation, explicit field-gap behavior, private-banking reason codes, and high-value regression tests across mandate health, construction evidence, and core resolver edge cases. |
| Debt removed | Stale ledger wording that treated RFC38-WTBD-006 as unimplemented is retired, and completed truth is anchored in RFC-0038 instead of living only in the WTBD ledger. |
| What was proven through testing and evidence | Focused tests, full 99 percent coverage proof, lint, typecheck, OpenAPI, API vocabulary, mesh contract validation, documentation current-state tests, GitHub PR Merge Gate, Docker build validation, and wiki publish/check evidence all passed. |
| Expected-standard decision | RFC38-WTBD-006 reaches the expected first-wave backend standard for source-backed mandate-health consumption, including optional core income-needs, reserve, and planned-withdrawal evidence when available. Remaining RFC38 work is limited to broader risk/performance health enrichment and downstream profile-detail product presentation. |

#### RFC38-WTBD-007 - Broader Risk And Performance Health Enrichment

Target business outcome:

Mandate health can incorporate benchmark-aware risk and performance attention from authoritative
analytics services.

Why it cannot be done now:

Risk and performance methodology belong to `lotus-risk` and `lotus-performance`. RFC-0038 keeps
health dimensions deterministic and source-aware without cloning those analytics.

Dependencies before implementation:

1. risk health/attention contract from `lotus-risk`,
2. performance under-review/benchmark-relative attention contract from `lotus-performance`,
3. benchmark identity and period semantics,
4. manage adapter tests for ready/degraded/stale/partial analytics,
5. Gateway/Workbench supportability presentation rules.

Expected implementation wave:

Implement after analytics contracts exist. Manage should consume supportability and reason codes
from the owners.

Promotion proof:

1. owning-service API certification,
2. manage health and command-center tests,
3. live mixed-readiness proof,
4. supported-feature updates naming supported analytics.

#### RFC38-WTBD-008 - Full Front-Office Command-Center Product Support

Target business outcome:

DPM command-center becomes a complete front-office product surface across manage, Gateway, and
Workbench, backed by canonical data and demo-ready documentation.

Current implementation-backed result:

Completed for the first-wave populated DPM command-center product path. RFC38-WTBD-001 through
RFC38-WTBD-004 delivered the required backend authority, Gateway composition, Workbench cockpit,
canonical seed automation, and PM-book discovery path. The supported-features wiki now documents
the command-center product path with business-readable flow, non-functional posture, audience use,
and demo boundaries.

Implemented scope:

1. manage owns mandate twins, mandate health, monitoring runs, active exceptions, and
   command-center summary,
2. Gateway exposes the command-center BFF without recalculating health, source readiness, or
   PM-book membership,
3. Workbench renders the cockpit through Gateway/BFF only,
4. platform canonical seed automation proves populated `ready`, selector-driven `partial`, and
   empty-date `empty` postures,
5. canonical evidence includes `canonical-front-office-qa-20260509-214551.json`,
   `dpm-command-center-seed-20260509-220332.json`, and demo-ready screenshot evidence at
   `lotus-platform/output/front-office-qa/wtbd-rfc36-audit-20260509-214550/dpm-command-center-live.png`.

Explicit boundaries:

1. degraded and blocked canonical fixtures remain future source-owner/product-depth work,
2. profile-detail presentation for restriction, sustainability, cashflow, risk, and performance
   enrichments remains separate scope,
3. manage does not claim OMS execution, PM scoring, client communication execution, autonomous AI,
   local Workbench recomputation, or unsupported source-owner enrichment.

Promotion proof:

1. canonical front-office evidence pack,
2. API/BFF/browser/accessibility/visual checks,
3. demo screenshots tied to validated backend proof,
4. wiki material suitable for business, operations, sales/pre-sales, and demos.

Gold-pass assessment - 2026-05-10:

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | The first-wave DPM command-center product path is complete across manage backend authority, Gateway composition, Workbench cockpit rendering, platform seed automation, PM-book discovery, and demo-ready canonical screenshot evidence. |
| Quality improvements made | RFC-0038 now records the product realization as part of the originating command-center RFC, while retaining clear no-claim boundaries for degraded fixtures, profile-detail UI, OMS, PM scoring, and autonomous behavior. |
| Debt removed | Stale WTBD wording that treated Gateway, Workbench, and platform proof as future work was retired after those owning slices merged and published. |
| What was proven through testing and evidence | Proof is anchored in the merged RFC38-WTBD-001 through WTBD-004 slices, 61 manage RFC38 tests, focused PM-book source-client proof, Ruff checks, platform canonical front-office QA, command-center seed evidence, and Workbench screenshot evidence. |
| Expected-standard decision | RFC38-WTBD-008 reaches the expected first-wave product standard. Remaining RFC38 work is limited to source-owner enrichment and richer product-depth fixtures, not the populated command-center path. |

### Suggested Sequencing

Recommended order:

1. implement Gateway DPM command-center composition,
2. implement platform canonical seed automation or the minimum needed for populated product proof,
3. implement Workbench DPM cockpit panels,
4. prove full front-office command-center support,
5. add PM-book discovery when a source authority exists,
6. add objective, restriction, sustainability, cashflow, risk, and performance enrichments from
   owning services.

Rationale:

Gateway and Workbench can realize the already-supported backend foundation before every enrichment
source exists. Source enrichments should improve quality later without blocking product visibility,
provided unsupported fields remain explicit and degraded.

### RFC-0038 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and source contract are explicit,
2. manage does not invent mandate, book, risk, performance, restriction, sustainability, or
   cashflow facts,
3. Gateway and Workbench consume through the governed product path,
4. degraded, empty, partial, stale, unavailable, and permission-denied states are tested,
5. OpenAPI/Swagger quality is certified for every API added or changed,
6. live or canonical front-office evidence is captured and critically reviewed,
7. README, RFC/source-map, wiki, supported-features, endpoint certification, and repository context
   are aligned,
8. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.

## RFC-0039 - Advanced Portfolio Construction And Rebalance Alternatives

Current closure status:

RFC-0039 delivered the implementation-backed `lotus-manage` backend foundation for construction
alternative generation, comparison, retrieval, persistence, and actor-attributed selection. The
supported manage backend methods are `DO_NOTHING_BASELINE`, `HEURISTIC_EXPLAINABLE`,
`MIN_TURNOVER`, `TAX_AWARE`, `SOLVER_CONSTRAINED`, `RISK_AWARE`, `LIQUIDITY_AWARE`,
`CURRENCY_OVERLAY`, `REGIME_STRESS_AWARE`, and source-backed `ESG_AWARE`.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md` |
| Source-data and method map | `docs/rfcs/RFC-0039-source-data-and-method-map.md` |
| Supported feature claim | `wiki/Supported-Features.md` construction rows |
| Live proof | `output/rfc0039-proof/20260503-193842-authority-backed-canonical/summary.json` |
| Manage implementation | `src/core/construction/`, `src/api/services/construction_service.py`, `src/api/routers/construction.py`, `src/infrastructure/construction/`, `src/infrastructure/risk_authority/` |
| Tests | `tests/unit/dpm/api/test_construction_api.py`, `tests/unit/dpm/infrastructure/test_risk_authority_client.py` |
| Downstream handoff | `docs/architecture/dpm-construction-alternatives-gateway-workbench-handoff.md`, Gateway/Workbench RFC-0098 construction addenda |

### Remaining Work Summary

These items are deliberately not done in RFC-0039 because manage owns construction-alternative
truth, while product realization and several richer source authorities belong outside manage.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0039 |
| --- | --- | --- | --- | --- |
| RFC39-WTBD-001 | Gateway construction-alternatives composition | `lotus-gateway` | Implemented, merged, CI-proven, and wiki-published through `lotus-gateway` PR #190 | Gateway consumes manage alternatives without recomputing construction truth or choosing alternatives. First-wave Workbench product support is now implemented and live-proven; lifecycle, OMS, report, AI, and approval depth remain later work. |
| RFC39-WTBD-002 | Workbench construction lab / alternatives comparison UX | `lotus-workbench` | Implemented, merged, CI-proven, live-proven, and wiki-published through `lotus-workbench` PR #150 and PR #151 | Workbench consumes Gateway/BFF construction contracts only, sends governed DPM context, renders manage-owned alternatives and traces without browser optimization, and is proven by focused canonical Workbench live evidence. |
| RFC39-WTBD-003 | Full front-office construction-lab product realization | `lotus-gateway`, `lotus-workbench`, with manage as backend authority | First-wave Gateway/Workbench realization implemented and wiki-published through `lotus-gateway` PR #190 plus `lotus-workbench` PR #150/#151 | The current PM-facing path is implementation-backed for generated alternatives, supportability, comparison, and selection controls. Bounded lifecycle depth through proof packs, waves, report input, and AI evidence input is now covered by RFC39-WTBD-010; external OMS execution and autonomous PM decisions remain unsupported. |
| RFC39-WTBD-004 | ESG/restriction-aware construction support | `lotus-core` source authority consumed by manage | Completed for source-backed restriction and sustainability profile consumption | `ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1` are consumed through stateful core sourcing. Manage degrades when profiles are missing, blocks candidate trades that violate hard client restrictions, preserves sustainability preferences and source lineage, and keeps classification evidence gaps in `PENDING_REVIEW` rather than claiming automatic ESG approval. |
| RFC39-WTBD-005 | Broader risk/performance alternative enrichment | `lotus-risk`, `lotus-performance` | Deferred beyond current seams/authority-backed concentration support | Current `RISK_AWARE` consumes concentration authority; broader tracking error, drawdown, stress contribution, attribution, and benchmark-relative performance need owning-service contracts. |
| RFC39-WTBD-006 | Authoritative transaction-cost and cost-aware alternatives | `lotus-core` source authority consumed by `lotus-manage` | Completed for source-owned observed-cost comparison methods | `TransactionCostCurve:v1` is consumed in stateful construction and proof packs. The `COST_AWARE` method applies observed average cost bps to candidate trade notionals, records an `ESTIMATED_COST` objective/constraint trace, and degrades when source evidence is absent or incomplete. Predictive execution quotes, market-impact modelling, venue routing, and broader execution methodology remain outside this support claim. |
| RFC39-WTBD-007 | Cashflow/income-need aware liquidity construction | `lotus-core` source authority consumed by `lotus-manage` | Completed for bounded source-product consumption in stateful construction and mandate-health lineage | `LIQUIDITY_AWARE` accepts `lotus-core` `PortfolioCashflowProjection:v1` total net cashflow evidence and now also preserves optional `ClientIncomeNeedsSchedule:v1`, `LiquidityReserveRequirement:v1`, and `PlannedWithdrawalSchedule:v1` supportability evidence from stateful core sourcing. Manage records source identity, counts, hashes, currencies, horizons, and reason codes for liquidity-aware diagnostics and mandate lineage, but does not compute financial-planning advice, funding recommendations, client liability plans, OMS instructions, or treasury actions. |
| RFC39-WTBD-008 | External treasury/currency overlay source boundary | `lotus-core` ingestion of external bank treasury/currency products, consumed by `lotus-manage` | External-source contracts plus active fail-closed hedge-readiness, currency-exposure, hedge-policy, eligible-hedge-instrument, and FX forward-curve posture merged in `lotus-core`; Manage consumes the unavailable postures; runtime external treasury ingestion remains pending | Current support uses FX readiness and bounded currency-overlay context. Lotus will not introduce a `lotus-treasury` app. `lotus-core` PR #365 (`c7fa07b0`, wiki `067f919`) declares contracts for external currency exposure, hedge policy, FX forward curves, and eligible hedge instruments. `lotus-core` PR #366 (`9e86df3b`, wiki `617e4e6`) exposes `ExternalHedgeExecutionReadiness:v1` as an active fail-closed `UNAVAILABLE` route. `lotus-core` PR #367 (`3d0a7bbd`, wiki `d719c74`) exposes `ExternalCurrencyExposure:v1` as an active fail-closed `UNAVAILABLE` route. `lotus-core` PR #368 (`763db4c1`, wiki `50fff30`) exposes `ExternalHedgePolicy:v1` as an active fail-closed `UNAVAILABLE` route, `lotus-core` PR #369 (`89225766`, wiki `72dc91d`) exposes `ExternalFXForwardCurve:v1` as an active fail-closed `UNAVAILABLE` route, and `lotus-core` PR #370 (`bacad356`, wiki `6e7c706`) exposes `ExternalEligibleHedgeInstrument:v1` as an active fail-closed `UNAVAILABLE` route; `lotus-platform` PR #334 (`ae4f707`) and PR #335 (`72be854`) mirror the first active postures. Manage now consumes all five routes through stateful core sourcing and preserves empty exposure/policy/eligible-instrument/forward-curve rows, exposure count, policy-rule count, eligible-instrument count, curve-point count, missing external treasury data families, blocked capabilities, lineage, source hashes, and reason codes in currency-overlay diagnostics so hedge realization remains blocked while ingestion is unavailable. Manage still must not claim FX attribution, price forwards, approve hedge policy, select eligible hedge instruments, approve suitability, recommend products, choose counterparties, claim best execution, produce OMS acknowledgements, claim fills/settlement, or perform autonomous treasury action. |
| RFC39-WTBD-009 | First-class regime scenario-pack source | `lotus-risk` / CIO scenario authority, consumed by `lotus-manage` | First-wave implemented for `RegimeScenarioPackEvaluation:v1`; bounded construction-lab posture is downstream-visible | `lotus-risk` now owns a certified scenario-pack evaluation source product, and manage consumes it for `REGIME_STRESS_AWARE` when `DPM_RISK_BASE_URL` is configured. Optional reconciled per-security contribution rows and v3 scenario/contribution methodology are now source-owned in `lotus-risk`; CIO approval workflow, portfolio/mandate applicability evidence, and richer scenario-specific UX remain future depth. |
| RFC39-WTBD-010 | Construction alternative lifecycle across proof packs, waves, reports, and AI | `lotus-manage`, `lotus-report`, `lotus-ai`, `lotus-gateway`, `lotus-workbench` | Completed for bounded first-wave lifecycle support | Selected construction alternatives flow into RFC-0040 proof packs, RFC-0041 wave item selection and optional proof-pack linkage, proof-pack and wave report inputs, proof-pack AI evidence inputs, and outcome expected-snapshot assembly without downstream reconstruction of construction truth. External OMS execution, autonomous PM choice, approval beyond manage wave controls, and client communication remain unsupported. |

### RFC39 Gold-Pass Audit And RFC Reintegration - 2026-05-09

The 2026-05-09 audit moved completed RFC39 WTBD truth into
`RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md` and refreshed the wiki
source so the implementation record is not stranded in this WTBD ledger.

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | Manage owns generation/read/selection, source posture, method status, objective/constraint traces, persisted selected alternative state, and authority-backed construction methods. Gateway composes those contracts through PR #190. Workbench renders a first-wave construction lab through PR #150/#151 and the PR #171 retry-identity hardening. Completed WTBD items now sit in the owning RFC as post-closure integrated truth. |
| Quality improvements made | The audit verified manage construction with 65 focused backend tests and static checks, then exercised the canonical front-office stack instead of relying on stale documentation. Live testing found Workbench repeated-generation identity defects that normal unit proof had missed; merged PR #171 adds unique per-generation idempotency and correlation identifiers plus deterministic unit-test injection. |
| Debt removed | Stale wording that treated Gateway/Workbench realization as future was removed from the RFC and wiki source. The Workbench deterministic idempotency/correlation assumption was removed because it broke repeated PM generation against persisted manage run records. Unsupported claims around OMS execution, predictive execution pricing, automatic suitability, security-level ESG classification, and local browser optimization remain explicit boundaries. |
| What was proven through testing and evidence | Manage focused proof passed `tests/unit/dpm/api/test_construction_api.py`, core-sourcing/risk-authority client tests, method registry tests, and construction vocabulary tests with 65 passing tests. Canonical Workbench validation passed for `PB_SG_GLOBAL_BAL_001`. Focused construction live proof first failed with HTTP 409 at `output/rfc39-wtbd-audit-20260509-construction-live/construction-alternatives-live-summary.json`, then failed with HTTP 500 at `output/rfc39-wtbd-audit-20260509-construction-live-fixed/construction-alternatives-live-summary.json`, and finally passed after merged PR #171 at `output/rfc39-wtbd-audit-20260509-construction-live-fixed2/construction-alternatives-live-summary.json`. |
| Expected-standard decision | `lotus-workbench` PR #171 is merged as `8de42e0` with a green Pull Request Merge Gate, and the RFC/WTBD/wiki truth has been merged to `lotus-manage` `main` with synchronized wiki publication and clean final branch hygiene. The first-wave construction product path is accepted for this completed slice. |

### Detailed Follow-Up Items

#### RFC39-WTBD-001 - Gateway Construction-Alternatives Composition

Target business outcome:

Gateway exposes construction-alternative sets, comparison metrics, selected-alternative state,
supportability, and action posture to Workbench while preserving manage as construction authority.

Why it cannot be done now:

Completed on 2026-05-06 through `lotus-gateway` PR #190 after RFC-0039 stabilized manage
alternative contracts, selection events, source-supportability posture, and live evidence.

Implemented scope:

1. Gateway RFC-0098 construction addendum is used as execution guide.
2. typed Gateway client consumes manage generate/read/select APIs:
   `POST /api/v1/construction/alternative-sets/generate`,
   `GET /api/v1/construction/alternative-sets/{alternative_set_id}`, and
   `POST /api/v1/construction/alternative-sets/{alternative_set_id}/selections`.
3. Gateway exposes Workbench-facing BFF routes:
   `POST /api/v1/dpm/command-center/construction/alternative-sets/generate`,
   `GET /api/v1/dpm/command-center/construction/alternative-sets/{alternative_set_id}`, and
   `POST /api/v1/dpm/command-center/construction/alternative-sets/{alternative_set_id}/selections`.
4. Gateway preserves alternative IDs, method statuses, objective terms, constraint traces,
   comparison metrics, source supportability, and selected state,
5. Gateway does not run optimizer, recompute metrics, infer source readiness, execute orders, or
   choose alternatives,
6. Gateway documents construction composition as an implementation-backed feature in README, RFC,
   repo context, and published wiki.

Validation and merge evidence:

1. `lotus-gateway` PR #190 merged to `main`.
2. PR checks passed: Feature Lane lint/typecheck/unit and workflow lint; PR Merge Gate
   lint/typecheck/unit, integration, coverage, Docker build, Docker parity, workflow lint, and queue
   checks.
3. Post-merge local validation passed on `main`:
   `python -m pytest tests\unit\test_dpm_construction_service.py tests\integration\test_dpm_construction_router.py tests\contract\test_dpm_construction_contract.py -q`
   with 10 tests passed.
4. Gateway wiki published from repo source with zero drift after publication.
5. Gateway branch cleaned after merge.

Remaining dependency:

Workbench construction lab and canonical front-office proof were completed afterward through
`lotus-workbench` PR #150 and PR #151. Gateway remains the composition boundary and does not
convert construction support into order execution, proof-pack lifecycle, or AI/report lifecycle
claims.

#### RFC39-WTBD-002 - Workbench Construction Lab / Alternatives Comparison UX

Target business outcome:

PMs can compare construction alternatives, inspect objective/constraint traces, understand degraded
source posture, and select an alternative through a governed Workbench journey.

Completion status:

Complete for the current Workbench construction-lab scope on 2026-05-06. `lotus-workbench`
PR #150 merged the Gateway-backed construction alternatives panel and PR #151 merged the
follow-up live-proof hardening that remained on the feature branch after PR #150 auto-merged.

Implemented scope:

1. `/workbench/{portfolioId}` renders a Construction Alternatives panel for the canonical DPM
   workflow,
2. Workbench uses the BFF/Gateway route family only:
   `POST /api/v1/dpm/command-center/construction/alternative-sets/generate`,
   `GET /api/v1/dpm/command-center/construction/alternative-sets/{alternative_set_id}`, and
   `POST /api/v1/dpm/command-center/construction/alternative-sets/{alternative_set_id}/selections`,
3. Workbench sends governed DPM source context instead of relying on page-level reporting dates:
   `MANDATE_PB_SG_GLOBAL_BAL_001`, `MODEL_PB_SG_GLOBAL_BAL_DPM`, `booking_center_code=Singapore`,
   and canonical construction source date `2026-04-10`,
4. generated alternatives, method status, drift/turnover metrics, objective trace count,
   constraint trace count, reason codes, correlation id, selected alternative state, and manage
   authority are rendered from Gateway/manage truth,
5. the panel keeps Gateway mediation visible after generation while showing `lotus-manage` as the
   data authority,
6. browser code does not optimize, auto-select, recompute construction metrics, infer source
   supportability, or clone manage methodology,
7. a focused live Playwright proof was added as `npm run live:validate:construction`,
8. README and wiki validation material now document the live proof command and evidence path.

Validation and merge evidence:

1. `lotus-workbench` PR #150 merged to `main` as merge commit
   `d96bc0eada11e8ecb5ac224cc04d9c9a155935ac`,
2. follow-up `lotus-workbench` PR #151 merged to `main` as
   `ac951d5` after the unmerged live-proof commit was found on the feature branch,
3. PR #150 checks passed: Feature Lane, PR Merge Gate lint/typecheck/coverage/build, Playwright
   smoke, Docker build, Docker parity, workflow lint, and queue checks,
4. PR #151 checks passed: Feature Lane and PR Merge Gate including Docker parity, Playwright
   smoke, Docker build, coverage/build, and workflow lint,
5. local targeted tests passed:
   `npx vitest run tests/unit/workbench-api.test.ts tests/unit/domain-product-discovery-client.test.tsx tests/unit/construction-alternatives-panel.test.tsx`
   with 46 tests passed,
6. local full Workbench gate passed before merge:
   `make check` with lint, typecheck, coverage 155 files / 704 tests, and Next production build,
7. focused live proof passed:
   `npm run live:validate:construction` against canonical `PB_SG_GLOBAL_BAL_001`,
8. live proof generated `output/rfc39-wtbd002-construction-lab/construction-live/construction-alternatives-live-summary.json`
   with response status `200`, source service `lotus-manage`, authority `lotus-manage:RFC-0039`,
   correlation `corr-workbench-construction-PB_SG_GLOBAL_BAL_001-2026-04-10`, three alternatives,
   visible Gateway mediation, and no local optimizer/methodology claim,
9. the 2026-05-09 WTBD audit found two repeated-generation defects through live testing:
   deterministic idempotency returned HTTP 409 and deterministic correlation later returned HTTP 500
   from persisted run identity collision,
10. `lotus-workbench` PR #171 merged as `8de42e0` and fixes both defects by issuing unique
   per-generation idempotency and correlation identifiers while preserving deterministic injection
   for unit tests,
11. rebuilt live proof passed at
   `output/rfc39-wtbd-audit-20260509-construction-live-fixed2/construction-alternatives-live-summary.json`
   with response status `200`, source service `lotus-manage`, authority `lotus-manage:RFC-0039`,
   supportability `PENDING_REVIEW`, alternative set `cas_ca8c4e1351aa`, three alternatives,
   visible Gateway mediation, and no local optimizer/methodology claim,
12. Workbench wiki was published from repo source after merge as `lotus-workbench.wiki` commit
   `a908bab`, and `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-workbench` returned clean.

Quality improvements made during closure:

1. fixed the Workbench construction request context after live proof exposed a real
   `DPM_CORE_CONTEXT_INCOMPLETE` failure caused by missing mandate/model context and a mismatched
   booking-center/source-date posture,
2. initially aligned construction idempotency and correlation keys with the governed construction
   source date rather than the page/reporting as-of date, then the 2026-05-09 audit corrected that
   approach by making mutation identity unique per generation while retaining deterministic test
   injection and source-date provenance in the identifier prefix,
3. made Gateway mediation persistent in the panel after successful generation,
4. hardened a flaky domain-product discovery test by waiting on loaded catalog data instead of a
   static page heading,
5. added a repeatable live proof command so future verification is not a one-off manual browser
   exercise.

Remaining dependency:

Richer construction lifecycle depth remains outside RFC39-WTBD-002. Bounded proof-pack linkage,
wave selection/proof-pack posture, report input, and AI evidence input are now covered by
RFC39-WTBD-010. OMS handoff, autonomous decisions, client communication, and broader command-center
choreography remain later owner/RFC-0098 work.

#### RFC39-WTBD-003 - Full Front-Office Construction-Lab Product Realization

Target business outcome:

Construction alternatives become a complete front-office PM workflow across manage, Gateway, and
Workbench, suitable for demos and real operating use.

Completion status:

Complete for first-wave product realization on 2026-05-06. Manage owns construction authority,
Gateway composes it, and Workbench renders a canonical PM-facing construction-lab path with live
proof. The later bounded lifecycle expansion is now closed under RFC39-WTBD-010.

Implemented scope:

1. `lotus-manage` owns alternative generation, comparison metrics, source supportability, method
   posture, and selection state,
2. `lotus-gateway` PR #190 exposes Workbench-facing construction BFF routes without recomputing
   construction truth,
3. `lotus-workbench` PR #150/#151 renders the PM construction alternatives panel, generation
   action, comparison table, reason codes, traces, and selection controls,
4. README/wiki material in Gateway and Workbench describes the current implementation-backed
   product path,
5. canonical live proof shows a real `PB_SG_GLOBAL_BAL_001` construction alternative set generated
   through the Workbench/Gateway/manage path.

Not included in this first wave:

1. external OMS or order-staging handoff,
2. autonomous PM choice,
3. client communication execution,
4. richer command-center drawers and demo choreography beyond the embedded Workbench panel.

Those items remain tracked under later RFC-0098 command-center realization or future owner RFCs.

#### RFC39-WTBD-004 - ESG/Restriction-Aware Construction Support

Target business outcome:

Construction alternatives can enforce client restrictions, sustainability preferences, product
eligibility, and ESG exclusions from source-backed profiles.

Current implementation-backed status:

Completed for manage backend consumption. `lotus-core` publishes source-backed
`ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1`; `lotus-manage` resolves
both through the stateful core-sourcing client and attaches them to
`ConstructionAuthorityContext`.

Implemented scope:

1. `ESG_AWARE` no longer relies on a blanket deferred method status when the source profiles are
   available,
2. missing client restriction or sustainability profiles degrade explicitly with source-specific
   reason codes,
3. hard client restriction rules block candidate buy/sell intents that match restricted
   instruments, issuers, asset classes, sectors, or regions,
4. sustainability min/max allocation preferences can move the method to `PENDING_REVIEW`,
5. exclusion and positive-tilt sustainability preferences require separate security-level
   classification evidence and therefore remain `PENDING_REVIEW` instead of unsupported ESG
   approval,
6. construction traces include client restriction and sustainability preference source terms,
7. selected-alternative proof packs preserve source refs, hashes, reason codes, restriction rules,
   and sustainability preferences without recomputing client-governance or ESG methodology.

Validation evidence:

1. core-sourcing client tests prove both source-product calls, selector payloads, and attached
   profile state,
2. construction API tests prove source-ready ESG-aware generation and hard-restriction blocking,
3. proof-pack builder tests prove restriction and sustainability source preservation,
4. README, RFC, context, and wiki updates avoid unsupported ESG approval or greenwashing claims.

Remaining boundary:

Gateway/Workbench product presentation for this new profile surface and richer security-level ESG
classification source evidence remain separate downstream/source-owner work. Manage does not infer
issuer sustainability classifications, claim regulatory suitability completion, execute orders, or
turn preferences into automatic client approval.

#### RFC39-WTBD-005 - Broader Risk/Performance Alternative Enrichment

Target business outcome:

Alternative comparisons include source-backed tracking error, volatility, drawdown, stress
contribution, attribution, and benchmark-relative performance context where available.

Why it cannot be done now:

Current support consumes `lotus-risk` concentration authority for `RISK_AWARE`, but broader risk
and performance analytics need certified owner contracts. Manage must not recalculate risk or
performance methodology.

Dependencies before implementation:

1. `RiskAlternativeEnrichment:v1` or equivalent from `lotus-risk`,
2. `PerformanceBenchmarkContext:v1` or equivalent from `lotus-performance`,
3. benchmark identity, as-of date, period vocabulary, freshness, and supportability semantics,
4. manage adapter tests,
5. Gateway/Workbench posture if displayed.

Expected implementation wave:

Implement after analytics source products exist. Preserve degraded supportability when unavailable.

Promotion proof:

1. owning-service API certification,
2. manage alternative-enrichment tests,
3. live proof with ready and degraded analytics,
4. OpenAPI/endpoint-certification updates,
5. supported-feature wording naming the exact analytics supported.

#### RFC39-WTBD-006 - Authoritative Transaction-Cost And Cost-Aware Alternatives

Target business outcome:

PMs can compare alternatives using source-owned observed transaction-cost evidence rather than
unlabelled local diagnostics, while preserving a clear boundary between observed booked-fee history
and predictive execution quotes.

Current implementation status:

Completed for source-owned observed-cost comparison methods. `lotus-core` owns
`TransactionCostCurve:v1`, `lotus-manage` stateful construction consumes it, and the
`COST_AWARE` construction method applies source-owned observed average cost bps to candidate
security-trade notionals. The method adds an `ESTIMATED_COST` objective term, a transaction-cost
constraint trace, method reason codes, and an `estimated_transaction_cost` comparison metric only
when the source curve covers the candidate trades. Missing, degraded, or inapplicable cost evidence
keeps the method `DEGRADED` with explicit reason codes.

Implemented scope:

1. `COST_AWARE` is a source-aware construction method and is not part of the default stateless
   first-wave method set.
2. `COST_AWARE` requires `TRANSACTION_COST` source-family supportability.
3. Ready source curves produce a bounded comparison estimate by applying observed average bps to
   candidate trade notionals.
4. Missing source curves produce a degraded method with `TRANSACTION_COST_CURVE_UNAVAILABLE` and
   `AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE`.
5. Missing traded-security coverage produces degraded posture instead of silently treating uncovered
   securities as zero-cost.
6. The method does not claim predictive spread, market impact, venue routing, execution timing, or
   order-placement cost optimization.

Production boundary:

This WTBD is complete for source-owned observed-cost construction comparison. It is not a
predictive transaction-cost model, market-impact model, venue-routing service, or external OMS
execution methodology. Those remain future execution/source-owner work and must not be presented as
supported functionality from this slice.

Implementation proof:

1. `src/core/construction/vocabulary.py` adds `COST_AWARE` and `TRANSACTION_COST` method-family
   linkage.
2. `src/core/construction/method_registry.py` declares the cost-aware method support gate.
3. `src/api/services/construction_service.py` computes source-observed cost comparison metrics and
   degraded-state reason codes.
4. `tests/unit/dpm/api/test_construction_api.py` proves ready and degraded cost-aware behavior.
5. `tests/unit/dpm/construction/test_method_registry.py` and
   `tests/unit/dpm/construction/test_vocabulary.py` preserve method registry and source-family
   governance.

#### RFC39-WTBD-007 - Cashflow/Income-Need Aware Liquidity Construction

Current implementation status:

First-wave implementation is complete for source-backed cashflow projection liquidity posture.
`lotus-core` now owns `PortfolioCashflowProjection:v1`, and `lotus-manage` `LIQUIDITY_AWARE`
construction accepts that source product through `AuthoritativeLiquidityContext.cashflow_projection`.
Manage uses the source-owned `total_net_cashflow`, currency, projection window, projected-row
posture, source fingerprint, data-quality status, latest evidence timestamp, and bounded reason
codes to evaluate projected cash pressure against the liquidity policy. If the projected net
cashflow would reduce adjusted post-trade cash below the minimum cash weight, the method moves to
`PENDING_REVIEW` with `CASHFLOW_PROJECTION_ADJUSTED_CASH_BELOW_POLICY`. If the projection is stale,
wrong-currency, lacks projected rows, or otherwise degraded by the source, the method degrades
truthfully and preserves source reason codes.

Target business outcome:

Liquidity-aware alternatives can account for client income needs, expected cashflows, and future
liquidity events rather than only current cash, settlement, and minimum cash policy.

Implementation decision:

Client income-need planning and forecast methodology remain unsupported in the current
implementation, but the source-owner decision is now explicit. `lotus-core` should publish
`ClientIncomeNeedsSchedule:v1`, `LiquidityReserveRequirement:v1`, and optional
`PlannedWithdrawalSchedule:v1` because these are client/portfolio reference facts needed by
multiple applications. External bank planning/reference systems may feed these Core products in
deployment. `PortfolioCashflowProjection:v1` remains a source-owned projection of portfolio
cashflows; it is not a client income-need profile, spending plan, liability ladder, or
wealth-planning forecast. Manage must not fabricate income needs or liability timing from current
cash, transactions, or projection totals.

Dependencies before implementation:

Completed first-wave dependencies:

1. `lotus-core` certified `PortfolioCashflowProjection:v1`,
2. source-owned currency, projection-window, projected-row, freshness, fingerprint, and reason-code
   posture,
3. manage liquidity objective tests for ready, degraded, currency-mismatch, no-projected-row, and
   below-policy cash pressure cases.

Remaining dependencies before full income-need support:

1. `lotus-core` contracts for `ClientIncomeNeedsSchedule:v1`,
   `LiquidityReserveRequirement:v1`, and optional `PlannedWithdrawalSchedule:v1`,
2. income need, reserve, recurrence, priority, currency, and forecast-horizon semantics distinct
   from portfolio cashflow projection,
3. ready, stale, missing, partial, entitlement-blocked, unsupported, and confidence/freshness
   posture for client planning inputs,
4. manage adapters and tests that consume Core products without financial-planning advice or
   funding-recommendation claims,
5. proof-pack and Workbench presentation alignment if surfaced as client income-need support.

Expected implementation wave:

The source-backed cashflow projection wave is implemented in manage after core source proof. The
income-need planning wave must wait for an owning source product.

Promotion proof:

1. source-owner certification for `PortfolioCashflowProjection:v1`,
2. manage liquidity/cashflow tests,
3. local and PR-gate evidence for ready, pending-review, degraded, and unsupported client-income
   posture,
4. supported-feature update.

#### RFC39-WTBD-008 - External Treasury/Currency Overlay Source Boundary

Target business outcome:

Currency-overlay construction can use bank-owned treasury policy, forward curves, hedge
instruments, currency exposure, and execution readiness rather than FX spot readiness and bounded
policy context alone.

Implementation decision:

Lotus will not create a `lotus-treasury` application. Treasury/currency overlay should follow the
same boundary pattern as external OMS integration: Lotus defines contracts, ingestion,
supportability, and DPM consumption, while deployed bank systems supply the authoritative treasury
data. `lotus-core` is the preferred Lotus-side ingestion owner for factual/reference-like external
treasury products because it already owns portfolio facts, holdings, base currency, restrictions,
market-data coverage, and source-readiness composition. `lotus-manage` consumes the resulting
products for construction and rebalance evidence only.

Dependencies before implementation:

1. external-source contracts such as `ExternalCurrencyExposure:v1`,
   `ExternalHedgePolicy:v1`, `ExternalFXForwardCurve:v1`,
   `ExternalEligibleHedgeInstrument:v1`, and `ExternalHedgeExecutionReadiness:v1`,
2. `lotus-core` ingestion and source-readiness posture for ready, stale, missing, partial,
   blocked-by-entitlement, and unsupported external treasury evidence,
3. `lotus-manage` overlay adapters that preserve source refs and supportability without pricing
   forwards, approving hedge policy, choosing counterparties, or claiming hedge execution,
4. manage overlay tests for ready/degraded/blocked states and explicit non-claims,
5. Gateway/Workbench display rules if surfaced.

Current implementation status:

`lotus-core` PR #365 merged to `main` as `c7fa07b0` and published wiki commit `067f919`. That
slice defines source-product and security-profile boundaries for `ExternalCurrencyExposure:v1`,
`ExternalHedgePolicy:v1`, `ExternalFXForwardCurve:v1`, and
`ExternalEligibleHedgeInstrument:v1`. `lotus-core` PR #366 merged to `main` as `9e86df3b` and
published wiki commit `617e4e6`. It promotes `ExternalHedgeExecutionReadiness:v1` to an active
fail-closed route at
`/integration/portfolios/{portfolio_id}/external-hedge-execution-readiness` that returns
`UNAVAILABLE` with required missing external treasury data families, blocked capabilities,
source-data product metadata, security metadata, lineage, and deterministic fingerprints until
bank-owned treasury ingestion is certified. The Core proof passed focused route/service/catalog
tests, source-product/security/docs/domain-product tests, `make source-data-product-contract-guard`,
`make domain-product-validate`, lint, typecheck, OpenAPI gate, API vocabulary gate, no-alias gate,
full `make test`, context validators, Feature Lane, and PR Merge Gate including Docker, E2E,
latency, fast load, and coverage gates.

`lotus-core` PR #367 merged to `main` as `3d0a7bbd` and published wiki commit `d719c74`. It
promotes `ExternalCurrencyExposure:v1` to an active fail-closed route at
`/integration/portfolios/{portfolio_id}/external-currency-exposure` that returns `UNAVAILABLE`,
empty exposures, missing `external_currency_exposure`, `external_hedge_policy`,
`external_fx_forward_curve`, and `external_eligible_hedge_instrument` data families, blocked
FX-attribution, hedge-advice, treasury-instruction, execution-readiness, OMS, fill, settlement, and
autonomous-treasury-action capabilities, plus external-bank-treasury lineage. `lotus-platform` PR
#333 merged as `c46d581` and mirrors the active domain-product posture in platform discovery
artifacts. Manage now consumes `ExternalCurrencyExposure:v1` through stateful core sourcing and
preserves the unavailable posture in currency-overlay diagnostics without making a local exposure,
FX-attribution, hedge advice, treasury instruction, execution-readiness, OMS, fill, or settlement
claim.

`lotus-core` PR #368 merged to `main` as `763db4c1` and published wiki commit `50fff30`. It
promotes `ExternalHedgePolicy:v1` to an active fail-closed route at
`/integration/portfolios/{portfolio_id}/external-hedge-policy` that returns `UNAVAILABLE`, empty
policy rules, missing `external_hedge_policy` data family, blocked hedge-policy approval,
hedge-advice, treasury-instruction, counterparty-selection, OMS, fill, settlement, and
autonomous-treasury-action capabilities, plus external-bank-treasury lineage. `lotus-platform` PR
#334 merged as `ae4f707` and mirrors the active domain-product posture in platform discovery
artifacts. Manage now consumes `ExternalHedgePolicy:v1` through stateful core sourcing and
preserves the unavailable posture in currency-overlay diagnostics without making a local
hedge-policy approval, hedge advice, treasury instruction, counterparty-selection, OMS, fill, or
settlement claim.

`lotus-core` PR #369 merged to `main` as `89225766` and published wiki commit `72dc91d`. It
promotes `ExternalFXForwardCurve:v1` to an active fail-closed route at
`/integration/market-data/external-fx-forward-curve` that returns `UNAVAILABLE`, empty forward-curve
points, missing `external_fx_forward_curve` data family, blocked forward-pricing,
FX-valuation-methodology, hedge-advice, treasury-instruction, counterparty-selection,
best-execution, OMS, fill, settlement, and autonomous-treasury-action capabilities, plus
external-bank-treasury lineage. `lotus-platform` PR #335 merged as `72be854` and mirrors the active
domain-product posture in platform discovery artifacts. Manage now consumes
`ExternalFXForwardCurve:v1` through stateful core sourcing and preserves the unavailable posture in
currency-overlay diagnostics without making a local forward-pricing, FX valuation-methodology,
hedge advice, treasury instruction, counterparty-selection, best-execution, OMS, fill, or
settlement claim.

`lotus-core` PR #370 merged to `main` as `bacad356` and published wiki commit `6e7c706`. It
promotes `ExternalEligibleHedgeInstrument:v1` to an active fail-closed route at
`/integration/portfolios/{portfolio_id}/external-eligible-hedge-instruments` that returns
`UNAVAILABLE`, empty eligible-instrument rows, missing `external_eligible_hedge_instrument` data
family, blocked eligible-instrument-selection, suitability-approval, product-recommendation,
counterparty-selection, treasury-instruction, best-execution, OMS, fill, settlement, and
autonomous-treasury-action capabilities, plus external-bank-treasury lineage. Manage now consumes
`ExternalEligibleHedgeInstrument:v1` through stateful core sourcing and preserves the unavailable
posture in currency-overlay diagnostics without making a local eligible-instrument selection,
suitability approval, product recommendation, hedge advice, treasury instruction,
counterparty-selection, best-execution, OMS, fill, or settlement claim.

Manage now consumes those fail-closed postures through stateful core sourcing: the core resolver
posts to `/integration/portfolios/{portfolio_id}/external-hedge-execution-readiness` and
`/integration/portfolios/{portfolio_id}/external-currency-exposure` and
`/integration/portfolios/{portfolio_id}/external-hedge-policy` and
`/integration/portfolios/{portfolio_id}/external-eligible-hedge-instruments`, and posts to
`/integration/market-data/external-fx-forward-curve`; it derives exposure currencies from the
resolved source context and attaches `ExternalHedgeExecutionReadiness:v1`,
`ExternalCurrencyExposure:v1`, `ExternalHedgePolicy:v1`,
`ExternalEligibleHedgeInstrument:v1`, and `ExternalFXForwardCurve:v1` to the DPM execution context.
Construction enrichment lifts all five postures into `currency_overlay_context` with source refs,
content hashes, empty exposure/policy/eligible-instrument/forward-curve rows, exposure count,
policy-rule count, eligible-instrument count, curve-point count, missing external treasury data
families, blocked capabilities, and reason codes.
`UNAVAILABLE` maps to `BLOCKED`, so `CURRENCY_OVERLAY` alternatives preserve fail-closed external
treasury readiness, exposure, hedge-policy, eligible-instrument, and FX forward-curve diagnostics
instead of deriving local hedge-readiness, FX-attribution, hedge-policy approval,
eligible-instrument selection, suitability approval, product recommendation, forward-pricing, or
valuation claims.

This advances RFC39-WTBD-008 from source-owner fail-closed runtime posture to Manage consumption of
unavailable external treasury readiness, currency-exposure, hedge-policy, eligible-instrument, and
FX forward-curve postures. It does not certify an external treasury ingestion table or add FX
attribution, hedge-policy approval, eligible-instrument selection, suitability approval, product
recommendation, hedge advice, forward pricing, FX valuation methodology, treasury instruction,
counterparty selection, best execution, OMS acknowledgement, fills, settlement, or autonomous
treasury action.

Expected implementation wave:

Implement external treasury ingestion for the planned currency exposure, hedge policy, FX forward
curve, eligible hedge instrument, and readiness source families before promoting ready hedge
execution support. Bank deployment maps local treasury systems into those contracts.

Promotion proof:

1. source-owner tests,
2. manage overlay tests and live proof,
3. documentation distinguishing policy-backed from treasury-backed overlay support.

#### RFC39-WTBD-009 - First-Class Regime Scenario-Pack Source

Target business outcome:

Regime-stress-aware alternatives can consume governed scenario packs from risk/CIO authority with
explicit assumptions, approvals, applicability, and stress result lineage.

Current implementation status:

First-wave implementation is complete for source-backed regime scenario evaluation.
`lotus-risk` owns `RegimeScenarioPackEvaluation:v1` and exposes
`POST /analytics/risk/regime-scenario-pack/evaluate`. `lotus-manage` consumes that source product
through the bounded `LotusRiskAuthorityClient` when `DPM_RISK_BASE_URL` is configured and
`REGIME_STRESS_AWARE` is requested without caller-supplied scenario context. Manage sends
post-construction asset-class exposure weights, portfolio id, business as-of date, governed
scenario pack id, and policy maximum loss threshold to `lotus-risk`; it uses only the returned
supportability, source service, scenario pack id, worst-case loss, policy threshold, and reason
codes to govern method posture. Excess loss remains `PENDING_REVIEW`; unavailable or invalid risk
responses fail closed into degraded manage supportability rather than locally calculating stress
methodology.

What remains deferred:

Broader scenario-pack maturity remains future depth. The first-wave source product evaluates a
governed pack against exposure weights; it does not yet expose per-security stress contribution,
CIO approval workflow evidence, portfolio applicability exceptions beyond bounded reason codes, or
Gateway/Workbench product surfaces.

Completed first-wave dependencies:

1. `lotus-risk` source product and API for `RegimeScenarioPackEvaluation:v1`,
2. platform domain-data-product mirror for `RegimeScenarioPackEvaluation:v1`,
3. manage risk-authority adapter tests for request shape, supportability, breach posture, invalid
   responses, and retries,
4. manage construction API tests proving automatic source-backed `REGIME_STRESS_AWARE` resolution,
5. README, RFC source map, wiki, supported-features, and repository context alignment.

Remaining dependencies before full product realization:

1. Gateway construction-alternatives composition,
2. Workbench construction lab UX,
3. scenario contribution or CIO-approval source fields if future product claims require them,
4. canonical browser proof after Gateway/Workbench support exists.

Expected implementation wave:

The source-product and manage-consumer wave is implemented. Product realization follows
RFC39-WTBD-001 through RFC39-WTBD-003.

Promotion proof:

1. source-owner certification in `lotus-risk`,
2. platform mirror PR for `RegimeScenarioPackEvaluation:v1`,
3. manage scenario method tests and proof,
4. supported-feature update distinguishing backend support from downstream product support.

#### RFC39-WTBD-010 - Construction Lifecycle Across Proof Packs, Waves, Reports, And AI

Target business outcome:

A selected construction alternative flows coherently into proof packs, rebalance waves, reports,
and governed AI evidence without any app reconstructing construction truth.

Implementation result:

Completed for bounded first-wave lifecycle support on 2026-05-10. RFC-0040 proof packs consume
selected construction alternatives; RFC-0041 waves persist item-level selected-alternative refs and
can generate linked proof packs; proof-pack and wave report-input contracts preserve source hashes
and lifecycle refs for `lotus-report`; proof-pack AI evidence input preserves bounded construction
and proof-pack truth for `lotus-ai`; and outcome expected-snapshot assembly reconciles alternative,
selection, proof-pack, wave, handoff, and outcome lineage without reconstructing construction facts.

Implemented scope:

1. `POST /api/v1/rebalance/proof-packs` supports selected-alternative generation from
   `alternative_set_id` and `selected_alternative_id`,
2. proof-pack report-input and AI-evidence endpoints expose deterministic handoff contracts,
3. wave item selection delegates selection to the construction repository and optionally generates
   an RFC-0040 proof pack,
4. wave proof-pack posture and wave report input expose selected-alternative, proof-pack, and
   internal handoff refs,
5. outcome expected-snapshot assembly validates that selected alternative, proof pack, wave item,
   and handoff identity agree before outcome learning consumes them.

Explicit boundaries:

1. manage still does not execute orders or claim OMS acknowledgement,
2. approval is limited to manage wave state transitions and does not become client approval,
3. report rendering, archive records, and AI workflow execution remain owned by their respective
   apps,
4. Gateway and Workbench remain product composition surfaces and do not reconstruct construction
   truth,
5. autonomous PM choice, predictive execution pricing, market impact, venue routing, and regulatory
   suitability approval remain unsupported.

Promotion proof:

1. `python -m pytest tests/unit/dpm/api/test_proof_pack_api.py
   tests/unit/dpm/proof_packs/test_proof_pack_service.py
   tests/unit/dpm/proof_packs/test_proof_pack_handoffs.py tests/unit/dpm/api/test_waves_api.py
   tests/integration/dpm/test_outcome_expected_snapshot_assembly.py -q` passed with 101 tests,
2. tests prove selected-alternative proof-pack generation, proof-pack report/AI evidence handoffs,
   wave item selection, optional proof-pack linkage, wave report input, no-external-execution handoff
   posture, and expected-snapshot identity reconciliation,
3. RFC-0039 now contains this completed WTBD truth as the owning business-change record,
4. README/wiki/supported-feature material remains explicit that OMS execution, autonomous PM choice,
   predictive execution pricing, market impact, venue routing, and regulatory suitability approval
   are not supported.

Gold-pass assessment:

| Question | Assessment |
| --- | --- |
| What was truly completed | Bounded construction lifecycle support from selected alternative into proof packs, wave item selection/proof-pack linkage, report input, AI evidence input, and outcome expected-snapshot reconciliation. |
| Quality improvements made | The audit replaced stale proposed wording with implementation-backed boundaries and pinned the lifecycle claim to existing service, handoff, wave, and integration tests. |
| Debt removed | The WTBD ledger no longer treats already-implemented RFC-0040/RFC-0041/report/AI handoff paths as future strategic extension. |
| What was proven through testing and evidence | 101 focused tests passed across proof-pack API/service/handoff, wave API, and outcome expected-snapshot assembly. The tests cover identity matching, proof-pack linkage, report/AI evidence contracts, handoff refs, and failure paths. |
| Expected-standard decision | RFC39-WTBD-010 reaches the expected bounded first-wave standard. Remaining lifecycle depth is explicitly outside this claim where it requires OMS execution, autonomous PM decisioning, client communication, or richer RFC-0098 command-center choreography. |

### Suggested Sequencing

Recommended order:

1. implement Gateway construction composition,
2. implement Workbench construction lab,
3. prove full front-office construction-lab product support,
4. implement ESG/restriction source products and promote `ESG_AWARE`,
5. add broader risk/performance, cost, cashflow, currency, and scenario source depth,
6. close cross-RFC construction lifecycle after proof packs, waves, reports, AI, Gateway, and
   Workbench are live.

Rationale:

Gateway and Workbench can expose the supported manage backend methods immediately once downstream
composition exists. Enrichment items should be promoted later from source-authoritative contracts
instead of blocking the product surface or creating manage-local methodology clones.

### RFC-0039 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and source contract are explicit,
2. manage does not clone risk, performance, cost, sustainability, restriction, cashflow, treasury,
   scenario, report, AI, Gateway, or Workbench behavior,
3. method status remains truthful: `READY`, `PENDING_REVIEW`, `BLOCKED`, or `DEGRADED`,
4. Gateway and Workbench consume through the governed product path,
5. degraded, blocked, stale, partial, unavailable, inapplicable, and solver-fallback states are
   tested where applicable,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC/source-map, wiki, supported-features, endpoint certification, and repository context
   are aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.
## RFC-0040 - Pre-Trade Proof Pack And Evidence Fabric

Current closure status:

RFC-0040 is `DONE` for the `lotus-manage` owned backend proof-pack authority. The delivered scope
includes `DpmPreTradeProofPack` generation from direct rebalance runs and selected construction
alternatives, immutable JSON persistence, deterministic Markdown, section states, section and
content hashes, lineage, retention metadata, append-only report/AI handoff refs, certified APIs,
bounded report-input and AI-evidence-input adapters, forbidden-field/action guardrails, and
source-backed RFC-0038 mandate-context attachment when mandate evidence exists.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0040-pre-trade-proof-pack-and-evidence-fabric.md` |
| Source-map and gap analysis | `docs/rfcs/RFC-0040-source-map-and-gap-analysis.md` |
| Supported feature claim | `wiki/Supported-Features.md` |
| Live proof | `output/rfc0040-proof/20260503-145818/manifest.json` and `critical-review.json` |
| Manage implementation | `src/core/proof_packs/`, `src/api/routers/proof_packs.py`, `src/infrastructure/proof_packs/` |
| Tests | `tests/unit/dpm/proof_packs/`, `tests/unit/dpm/api/test_proof_pack_api.py` |
| Downstream RFC alignment | `lotus-gateway` PR #181 merge `b2c3734`, `lotus-workbench` PR #142 merge `b63981b` |
| First-wave proof-pack product realization | `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-124405.json`, `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json` |

### Remaining Work Summary

These items are deliberately not done in RFC-0040 because proof-pack backend authority is
manage-owned, while full product realization, document materialization, AI narrative generation,
analytics enrichment, and broader source coverage belong to other Lotus apps.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0040 |
| --- | --- | --- | --- | --- |
| RFC40-WTBD-001 | Gateway proof-pack composition | `lotus-gateway` | Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #195 | Gateway consumes stable manage proof-pack generate/read/Markdown/report-input/AI-evidence APIs without reconstructing sections, hashes, report refs, or AI refs. Workbench UX and full canonical product proof remain separate WTBDs. |
| RFC40-WTBD-002 | Workbench proof-pack review UX | `lotus-workbench` | Completed, merged, CI-proven, and wiki-published through `lotus-workbench` PR #156 | Workbench now consumes Gateway/BFF proof-pack contracts only, renders proof-pack identity, supportability, sections, source hashes, Markdown/report/AI posture, and action eligibility without reconstructing sections, hashes, report input, or AI evidence. |
| RFC40-WTBD-003 | Full front-office proof-pack product realization | `lotus-gateway`, `lotus-workbench`, with manage as backend authority | Completed, merged, CI-proven, live-proven, and wiki-published through `lotus-gateway` PR #195, `lotus-workbench` PR #156, `lotus-workbench` PR #164, `lotus-manage` PR #117, and platform canonical QA | The first-wave product path now generates and replays proof-pack evidence through Gateway/BFF, renders Workbench proof-pack review over live manage truth, and passes governed canonical front-office QA with `dpm.proof_pack` classified `ready`. Governed AI memo generation, richer source-owner enrichment, client restrictions, sustainability profiles, and cross-RFC portfolio memory are now also implementation-backed in their bounded first-wave forms; richer lifecycle depth remains future source-owner/product scope. |
| RFC40-WTBD-004 | Report materialization from `DpmProofPackReportInput` | `lotus-report`, `lotus-render`, `lotus-archive` | Completed, merged, CI-proven, and wiki-published through `lotus-render` PR #11, `lotus-report` PR #90, and `lotus-archive` PR #23 | Manage produces deterministic report input; `lotus-report` consumes it without reconstructing proof-pack evidence, `lotus-render` renders the governed `proof-pack` template, and `lotus-archive` governs the resulting `proof_pack` artifact lifecycle with retention, legal hold, retrieval, purge, and access audit. |
| RFC40-WTBD-005 | AI PM memo generation from `DpmProofPackAiEvidenceInput` | `lotus-ai`, consumed through Gateway/Workbench | Completed, merged, CI-proven, live-proven, and wiki-published through `lotus-ai` PR #61, `lotus-gateway` PR #198, `lotus-workbench` PR #166, and rebuilt platform canonical QA | Manage produces bounded AI evidence with guardrails; `lotus-ai` owns review-gated `dpm_pm_memo.pack@v1` execution, Gateway composes the handoff, and Workbench exposes only a governed request action without prompt construction or autonomous decisioning. |
| RFC40-WTBD-006 | Broader risk and performance proof-pack enrichment | `lotus-risk`, `lotus-performance`, consumed by manage/Gateway | Completed in this slice for manage proof-pack authority | RFC-0040 selected-alternative proof packs now preserve source-owned risk and performance context from construction authority metadata, including supportability state, source refs, source hashes, reason codes, and bounded source-emitted measures. Manage still does not calculate risk or performance methodology locally. |
| RFC40-WTBD-007 | Authoritative transaction-cost curve | `lotus-core` source authority consumed by `lotus-manage` | Completed for proof-pack evidence authority | `lotus-core` publishes `TransactionCostCurve:v1` observed booked-fee evidence and `lotus-manage` consumes it through stateful core sourcing, attaches `AuthoritativeTransactionCostContext` to selected construction alternatives, and preserves source-owned supportability, source refs, content hashes, reason codes, evidence windows, missing securities, and bounded curve points in `turnover_and_cost` proof-pack evidence. Manage still labels local construction estimates separately and does not claim predictive execution quotes or min-cost optimization. |
| RFC40-WTBD-008 | Sustainability preferences and client restriction profiles | `lotus-core` source authority consumed by `lotus-manage` | Completed for manage proof-pack evidence authority | `ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1` are consumed through stateful core sourcing, attached to selected construction alternatives, and preserved in proof-pack `eligibility_and_restrictions` and `sustainability_controls` sections with source refs, content hashes, reason codes, and review/block posture. Security-level sustainability classification remains a pending-review boundary when source evidence is absent. |
| RFC40-WTBD-009 | Scenario-pack authority beyond supplied context | `lotus-risk` / CIO authority, consumed by `lotus-manage` construction and proof-pack evidence | Completed for bounded source-owned scenario-pack governance and manage proof-pack preservation | `RegimeScenarioPackEvaluation:v1` supplies first-wave scenario-pack evaluation for `REGIME_STRESS_AWARE` alternatives. Proof packs now preserve that selected-alternative context in `scenario_and_regime_evidence` with source refs, source hashes, bounded facts, metrics, supportability state, reason codes, source-owned CIO approval/effective-period/portfolio-applicability `governance_evidence`, and bounded `scenario_evidence_posture` for missing, stale/effective-period-exception, inapplicable, and contribution-partial source evidence. Per-security scenario contribution rows, v3 scenario/contribution methodology, and bounded scenario-pack governance posture are source-owned in `lotus-risk`; Manage consumes and preserves the source response without local scenario, approval, effective-period, applicability, or contribution calculation. |
| RFC40-WTBD-010 | Decision timeline and portfolio memory across mandate, exception, wave, handoff, outcome, report, AI, and generated-document events | `lotus-manage` with downstream/source participants | Completed for the current bank-buyable support claim: manage backend authority plus first-wave Gateway/Workbench product realization are merged, live-proven, and wiki-published; mandate health, monitoring-exception, event identity, retention, redaction, access, audit policy, and source-event family posture are implemented in manage; `lotus-report` PR #92 implements the report-side bounded context consumer; `lotus-report` PR #93 implements the report-owned source-event family for report lifecycle, snapshot, render, and archive evidence; `lotus-ai` PR #62 implements bounded DPM memo/narrative consumers; `lotus-ai` PR #64 implements the AI-owned workflow-pack source-event family; `lotus-archive` PR #25 implements the archive-owned generated-document/client-delivery reissue source-event family | Manage exposes a deterministic source-backed portfolio-memory read model over persisted mandate health snapshots, monitoring exceptions, proof packs, proof-pack-local timeline events, RFC-0041 wave events, internal handoff refs, and RFC-0042 outcome-review events. Gateway composes that read model and Workbench renders the first-wave timeline panel with canonical browser proof. `lotus-report` can carry Manage-owned `portfolio_memory_context` into proof-pack, wave, and outcome report snapshot/render lineage without reconstruction and now exposes stable report-owned event identities for downstream portfolio-memory ingestion. `lotus-ai` validates that same context for DPM PM memo and outcome-review narrative packs without reconstructing timeline facts and now exposes no-raw-payload AI workflow-pack source events at `/platform/workflow-packs/source-events` and `/platform/workflow-packs/runs/{run_id}/source-events`. `lotus-archive` now exposes stable generated-document archive, supersession, correction, and client-delivery reissue source events at `/documents/{document_id}/source-events` with checksum-backed content hashes, retention/redaction/access/audit policy, bounded artifact refs, and no raw document bytes, storage keys, raw report payloads, or raw client references. The manage API publishes OMS execution as deferred source-owner posture and points PM scoring to the separate Manage-owned score-run lifecycle product without projecting hidden portfolio-memory score events. |

### RFC40 Gold-Pass Audit And RFC Reintegration - 2026-05-09

The 2026-05-09 audit moved completed RFC40 WTBD truth into
`RFC-0040-pre-trade-proof-pack-and-evidence-fabric.md` and refreshed the wiki source so the
current implementation record is available from the owning RFC.

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | Manage owns immutable proof-pack generation, section states, hashes, Markdown, report input, AI evidence input, and source-context preservation. Gateway proof-pack composition, Workbench proof-pack review, first-wave canonical product proof, report/render/archive materialization, governed AI PM memo handoff, source-owned risk/performance/cost/restriction/sustainability preservation, and first-wave portfolio-memory consumers are implemented in their owning repositories. |
| Quality improvements made | The audit removed stale backend-only RFC wording and replaced it with an implementation-backed support boundary. It keeps manage as evidence authority while recognizing downstream product truth and explicitly separates completed first-wave support from future OMS, PM-scoring, client communication execution, direct scenario contribution, and richer profile presentation. |
| Debt removed | Stale language that treated Gateway/Workbench/report/AI realization as future was retired from the owning RFC. The WTBD now records proof-pack product realization as wiki-published rather than merely wiki-ready. Unsupported product claims remain explicit instead of being hidden in broad "full product" wording. |
| What was proven through testing and evidence | Existing backend proof remains anchored in `output/rfc0040-proof/20260503-145818` and `output/rfc0040-proof/20260507-230235`. First-wave product proof remains anchored in `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-124405.json`, Workbench `live-validation-summary.json`, and `dpm-proof-pack-live.png`. The 2026-05-09 audit reran canonical front-office QA successfully with report `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260509-225912.json`, Markdown summary `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260509-225912.md`, DPM seed evidence `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260509-230635.json`, and screenshots in `lotus-platform/output/front-office-qa/wtbd-rfc40-audit-20260509`. |
| Expected-standard decision | RFC40 reaches the expected standard for manage-owned proof-pack authority and the bounded first-wave product path on merged `lotus-manage` `main` truth with synchronized wiki publication and clean final branch hygiene. |

### Detailed Follow-Up Items

#### RFC40-WTBD-001 - Gateway Proof-Pack Composition

Target business outcome:

Gateway exposes a Workbench-facing proof-pack contract that preserves manage-owned evidence while
adding experience-layer posture for entitlements, availability, report status, AI status, archive
status, and command-center context.

Current implementation-backed status:

Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #195. Gateway now
exposes `/api/v1/dpm/command-center/proof-packs*` routes for generate, read, deterministic
Markdown, report-input, and AI-evidence-input access. The implementation preserves manage-owned
`proof_pack_id`, section states, reason codes, source refs, content/source hashes, report refs, and
AI refs in a Gateway envelope without reconstructing proof-pack evidence.

Implementation evidence:

1. `lotus-gateway` merge commit `f706853`,
2. `src/app/routers/dpm_proof_packs.py`,
3. `src/app/services/dpm_proof_pack_service.py`,
4. `src/app/contracts/dpm_proof_packs.py`,
5. `src/app/clients/dpm_client.py`,
6. `tests/unit/test_dpm_proof_pack_service.py`,
7. `tests/integration/test_dpm_proof_pack_router.py`,
8. `tests/contract/test_dpm_proof_pack_contract.py`,
9. `tests/unit/test_upstream_clients.py`,
10. `lotus-gateway` wiki publication commit `7b97aac`.

Validation evidence:

1. `make check` passed in `lotus-gateway` with lint, format, monetary-float guard, mypy, and `452`
   unit/contract tests,
2. `make test-integration` passed in `lotus-gateway` with `164` integration tests,
3. focused proof-pack and upstream-client checks passed with `110` tests,
4. GitHub Feature Lane and PR Merge Gate passed for `lotus-gateway` PR #195, including coverage,
   integration, Docker build, and Docker parity checks,
5. `Sync-RepoWikis.ps1 -Publish -Repository lotus-gateway` published repo-authored wiki source,
   and post-publish check-only reported zero drift.

Remaining governed follow-up:

Workbench review UX, full canonical front-office proof, report materialization, archive lifecycle,
AI memo generation, and richer source-owner enrichment remain governed by RFC40-WTBD-002 through
RFC40-WTBD-010. This item is a Gateway composition support claim only.

#### RFC40-WTBD-002 - Workbench Proof-Pack Review UX

Target business outcome:

Portfolio managers, reviewers, operations, and client-facing teams can inspect proof packs in
Workbench with section readiness, evidence drawers, Markdown preview, report/AI posture, lineage,
hashes, and action eligibility backed by Gateway truth.

Current implementation-backed status:

Completed, merged, CI-proven, and wiki-published through `lotus-workbench` PR #156. Workbench now
embeds a `Proof-Pack Evidence` panel in `/workbench/{portfolioId}` and uses Gateway/BFF routes under
`/api/v1/dpm/command-center/proof-packs*` for proof-pack generation, detail, Markdown, report-input,
and AI-evidence-input actions. The server prefetch path uses the Gateway server target, while client
actions use the client BFF target. The panel preserves Gateway and manage truth for proof-pack
identity, mandate/run/alternative lineage, supportability, section state counts, source hashes,
Markdown availability, report-input availability, and AI-evidence availability without rebuilding
proof-pack sections, recomputing hashes, or constructing report/AI payloads in browser code.

Implementation evidence:

1. `lotus-workbench` merge commit `8acf276`,
2. `src/features/workbench/api.ts` proof-pack Gateway/BFF wrappers,
3. `src/features/workbench/proof-pack-view-model.ts`,
4. `src/features/workbench/components/proof-pack-panel.tsx`,
5. `src/app/workbench/[portfolioId]/page.tsx`,
6. `scripts/live/validate-canonical-workbench-live.mjs`,
7. `scripts/live/validation/browser-workflows.mjs`,
8. `tests/unit/proof-pack-view-model.test.ts`,
9. `tests/unit/proof-pack-panel.test.tsx`,
10. `tests/unit/workbench-api.test.ts`,
11. `tests/integration/workbench-page.test.tsx`,
12. `lotus-workbench` wiki publication commit `1b4b095`.

Validation evidence:

1. focused Workbench proof-pack, API, metrics, and page tests passed with `70` tests,
2. RFC-0098 documentation regression passed in `lotus-workbench`,
3. `npm run typecheck`, `npm run lint`, and `make check` passed locally in `lotus-workbench`,
   including `725` tests, coverage, and production Next build,
4. GitHub Feature Lane and PR Merge Gate passed for `lotus-workbench` PR #156, including lint,
   typecheck, tests, coverage/build, Playwright smoke, Docker build, and Docker parity,
5. `Sync-RepoWikis.ps1 -Publish -Repository lotus-workbench` published repo-authored wiki source,
   and post-publish check-only reported zero drift.

Remaining governed follow-up:

This closed the Workbench review UX slice only at PR #156 merge time. RFC40-WTBD-003 later closed
the first-wave full product-realization slice after canonical front-office proof across the complete
Gateway/Workbench proof-pack path, audience-ready documentation, and explicit treatment of
report/AI downstream posture. Report
materialization, AI memo generation, richer source-owner enrichment, transaction-cost authority,
client restriction/sustainability profiles, and cross-RFC portfolio memory remain governed by
RFC40-WTBD-004 through RFC40-WTBD-010.

#### RFC40-WTBD-003 - Full Front-Office Proof-Pack Product Realization

Target business outcome:

Proof packs are available as an end-to-end product workflow across manage, Gateway, and Workbench,
with validated backend evidence, composed experience APIs, browser proof, and demo-ready material.

Current implementation-backed status:

Completed for the first-wave full front-office proof-pack product path on 2026-05-07. The proof
pack workflow is now realized across manage backend authority, Gateway/BFF composition, Workbench
review UX, and governed platform canonical QA for `PB_SG_GLOBAL_BAL_001`.

What was delivered:

1. `lotus-gateway` PR #195 exposes Gateway-owned proof-pack routes under
   `/api/v1/dpm/command-center/proof-packs*` without reconstructing manage evidence.
2. `lotus-workbench` PR #156 renders the proof-pack review panel from Gateway/BFF truth and
   preserves proof-pack identity, section states, source hashes, Markdown/report/AI posture, and
   action eligibility.
3. `lotus-workbench` PR #164 aligned live validation proof-pack preflight idempotency with the
   Workbench UI path so canonical browser proof uses the same generated evidence flow.
4. `lotus-manage` PR #117 made proof-pack generation replay deterministic source identities before
   rebuilding a proof pack, preventing immutable-content conflicts when a canonical run already
   exists under a different idempotency key.
5. Platform canonical front-office QA rebuilt the merged images, seeded the canonical portfolio,
   refreshed DPM command-center data, generated proof-pack evidence through Gateway, validated
   Workbench browser panels, captured screenshots, and stopped the governed runtime cleanly.

Validation evidence:

1. `lotus-manage` PR #117 merged to `main` at `78b04eba6c83a35c1ea3f0c89d7740e667bfb576` after
   Feature Lane and PR Merge Gate checks passed.
2. Post-merge manage focused proof passed:
   `python -m pytest tests/unit/dpm/proof_packs/test_proof_pack_service.py tests/unit/dpm/proof_packs/test_proof_pack_repository.py tests/unit/dpm/proof_packs/test_proof_pack_postgres_repository.py tests/unit/dpm/api/test_proof_pack_api.py -q`
   with `29` tests passing.
3. Post-merge governed platform proof passed:
   `powershell -ExecutionPolicy Bypass -File automation\Invoke-Canonical-FrontOffice-QA.ps1 -BringUp -BuildImages -LotusAiEnvFile .env.example -SeedWaitSeconds 1200`.
4. Canonical QA evidence:
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-124405.json` and
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-124405.md`.
5. DPM seed evidence:
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260507-125141.json` reported
   status `ok` after manage refresh, manage lookup, Gateway mandate lookup, Gateway mandate
   health, and Gateway command-center summary checks.
6. Workbench live evidence:
   `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json` classified
   `dpm.proof_pack` as `ready` with proof pack `dpp_c09f73d0`, business state `PENDING_REVIEW`,
   `27` sections, and `3` source hashes.
7. Browser screenshot evidence:
   `lotus-workbench/output/playwright/live-canonical/dpm-proof-pack-live.png` and
   `lotus-workbench/output/playwright/live-canonical/dpm-command-center-live.png` were captured
   after backend/API/panel validation passed.

Gold-pass assessment:

This WTBD is complete for the stated first-wave product-realization scope. The full path is merged
to owning `main` branches, replay-safe, CI-proven, browser-proven, and supported by canonical
runtime evidence. The closure does not promote report materialization, governed AI memo generation,
richer source-owner enrichment, transaction-cost authority, client restriction/sustainability
profiles, or cross-RFC portfolio memory; those remain RFC40-WTBD-004 through RFC40-WTBD-010.

#### RFC40-WTBD-004 - Report Materialization From `DpmProofPackReportInput`

Target business outcome:

A proof pack can be materialized into a governed report with deterministic rendering, archive
records, retention, legal hold, retrieval, and access audit.

Closure status:

Completed on 2026-05-07 across the owning repositories:

1. `lotus-render` PR #11 added the governed `proof-pack` render template, template manifest,
   deterministic contract tests, and wiki-published render support posture.
2. `lotus-report` PR #90 added `POST /reports/proof-packs`, persisted
   `DpmProofPackReportInput` snapshots, lineage back to `lotus-manage`, render-package handoff to
   `lotus-render`, archive handoff metadata, OpenAPI support posture, and wiki-published
   proof-pack report documentation.
3. `lotus-archive` PR #23 tightened generated-report type validation to include `proof_pack` and
   proved the proof-pack archive lifecycle through create, Gateway download, legal hold,
   blocked-purge response, release, purge, and access-audit events.

Ownership boundary:

`lotus-manage` remains the proof-pack evidence authority and deterministic report-input owner. It
does not generate, render, archive, retain, or retrieve report documents. Report materialization is
owned by `lotus-report`, deterministic rendering by `lotus-render`, and document lifecycle by
`lotus-archive`.

Implementation-backed proof:

1. `lotus-render`: `54 passed` focused render/template tests and wiki check-only drift `0` after
   publication.
2. `lotus-report`: GitHub Feature Lane and PR Merge Gate passed, including unit, integration, e2e,
   combined coverage, Docker build, and wiki publication.
3. `lotus-archive`: GitHub Feature Lane and PR Merge Gate passed, including unit, integration,
   e2e, combined coverage, Docker build, and wiki publication.

Remaining boundaries:

Gateway/Workbench report request UX for pre-trade proof-pack reports is not promoted by this WTBD
unless a separate product-surface slice exposes it. Governed AI PM memo generation is now closed
separately by RFC40-WTBD-005.

#### RFC40-WTBD-005 - AI PM Memo Generation From `DpmProofPackAiEvidenceInput`

Target business outcome:

PMs can request governed AI assistance over proof-pack evidence while preserving provenance,
guardrails, forbidden-field protections, and unsupported-action blocking.

Closure basis:

Completed on 2026-05-07 across the owning repositories:

1. `lotus-ai` PR #61 merged as `942d618a41ae7375fc790995974f8e16db4e2a8b`, adding the
   review-gated `dpm_pm_memo.pack@v1` workflow-pack execution path for manage-owned
   `DpmProofPackAiEvidenceInput`,
2. `lotus-gateway` PR #198 merged as `dc891266ad1dd567f4a0b0d1729d1c60db6cce7a`, adding
   `POST /api/v1/dpm/command-center/proof-packs/{proof_pack_id}/ai-pm-memo` without
   reconstructing proof-pack evidence or generating PM memos locally,
3. `lotus-workbench` PR #166 merged as `243855743380a24e9f7622a1ed7839a50e5604f5`, adding the
   governed proof-pack panel action and live validation for the Gateway memo handoff without
   browser prompt construction,
4. wiki source was synchronized for `lotus-ai`, `lotus-gateway`, and `lotus-workbench`, with
   `lotus-gateway` wiki publication commit `4d5b9d1` and `lotus-workbench` wiki publication
   commit `5d8d763`,
5. rebuilt platform canonical QA passed at
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-210641.json`.

Runtime proof:

The rebuilt canonical QA run validated the canonical proof pack `dpp_c09f73d0`, classified
`dpm.proof_pack` as `ready`, and called
`POST /api/v1/dpm/command-center/proof-packs/dpp_c09f73d0/ai-pm-memo` through Gateway with HTTP
200. The live Workbench summary recorded `lotus-ai` as source service and workflow-pack run
`packrun_dpm_pm_memo_air_b69bcfd16d7341b889b0037f884839fa` in `AWAITING_REVIEW` /
`ACTION_REQUIRED` posture.

Supported boundaries:

1. `lotus-manage` remains evidence authority only and does not construct AI prompts, generate
   memos, score PMs, approve trades, or issue recommendations,
2. `lotus-gateway` reads manage-owned AI evidence input and invokes `lotus-ai` as the composition
   owner without rebuilding proof-pack sections, hashes, or report refs,
3. `lotus-workbench` exposes a bounded request action and renders workflow-pack posture only,
4. the supported state is review-gated narrative assistance, not autonomous investment advice,
   client contact, order approval, or execution.

2026-05-12 boundary-hardening result:

`DpmProofPackAiEvidenceInput` now explicitly lists `score_portfolio_manager` and
`generate_client_message` in `forbidden_actions`, aligning proof-pack AI evidence with the
outcome-review and RFC-0043 guardrail posture. Focused API and handoff tests pin the boundary so
proof-pack evidence cannot be misread as permission for PM scoring, client-message generation,
trade approval, order placement, control override, or invented evidence.

#### RFC40-WTBD-006 - Broader Risk And Performance Proof-Pack Enrichment

Target business outcome:

Proof packs include source-backed risk and performance context beyond the first manage-backed
evidence, with clear degraded states when analytics are missing, stale, or partial.

Current implementation-backed status:

Completed in this slice for `lotus-manage` proof-pack authority. Selected-alternative proof packs
now consume source-owned risk and performance authority context already attached to the selected
RFC-0039 construction alternative. The `risk_impact` and `performance_context` sections preserve
the source owner's supportability state, lineage refs, content hashes, reason codes, and bounded
source-emitted measures such as tracking error, concentration posture, benchmark identity, active
return, and underperformance flag. Direct run proof packs and selected alternatives without source
analytics continue to degrade those sections truthfully.

Implemented controls:

1. `src/core/proof_packs/source_analytics.py` isolates risk/performance extraction from the
   proof-pack builder and validates attached contexts against the existing
   `AuthoritativeRiskContext` and `AuthoritativePerformanceContext` models,
2. `src/core/proof_packs/builder.py` uses that module to populate `risk_impact` and
   `performance_context` sections, source refs, and `risk_context` / `performance_context` source
   hashes without adding manage-local analytics methodology,
3. report and AI handoff adapters inherit the enriched sections and sanitized metrics from the
   immutable proof pack without reconstructing analytics,
4. `scripts/generate_rfc0040_proof_pack_evidence.py` now proves a mixed-readiness selected
   alternative where risk is `READY` and performance remains `DEGRADED`,
5. tests pin ready/degraded section states, source hash keys, source refs, JSON-safe source
   measures, AI/report handoff preservation, and evidence-script critical-review checks.

Proof:

1. targeted proof-pack/evidence tests:
   `python -m pytest tests/unit/dpm/proof_packs/test_proof_pack_builder.py tests/unit/dpm/proof_packs/test_proof_pack_handoffs.py tests/unit/dpm/proof_packs/test_proof_pack_markdown.py tests/unit/test_rfc0040_evidence_script.py -q`,
2. live proof is generated by
   `python scripts/generate_rfc0040_proof_pack_evidence.py --base-url http://127.0.0.1:8001`;
   this slice records `output/rfc0040-proof/20260507-230235/manifest.json` with selected
   proof-pack `risk_source_state=READY`, `performance_source_state=DEGRADED`, `risk_context` and
   `performance_context` source hashes, and `critical-review.json` passed,
3. full repository proof remains `make check` before PR publication.

Remaining bounded gaps:

1. Gateway and Workbench may choose to surface the enriched risk/performance posture, but manage
   closure does not claim downstream rendering,
2. richer attribution, contribution, stress, and scenario methodology remains source-owner work in
   `lotus-risk` and `lotus-performance`,
3. transaction-cost authority, client restriction profiles, sustainability preferences, and
   portfolio memory remain separate WTBDs.

#### RFC40-WTBD-007 - Authoritative Transaction-Cost Curve

Target business outcome:

Proof packs can distinguish labelled estimates from source-backed transaction-cost evidence and
show cost supportability clearly.

Implementation-backed status:

Completed for RFC-0040 proof-pack evidence authority. `lotus-core` now owns
`TransactionCostCurve:v1` as observed booked-fee transaction-cost evidence, and `lotus-manage`
consumes that source product through the stateful core-sourcing path. Manage converts the response
into `AuthoritativeTransactionCostContext`, attaches it to construction alternatives, and preserves
the source-owned evidence in the proof-pack `turnover_and_cost` section without blending it into
local construction estimates.

Implemented boundary:

1. source owner: `lotus-core`,
2. source product: `TransactionCostCurve:v1`,
3. route: `/integration/portfolios/{portfolio_id}/transaction-cost-curve`,
4. consumer: `lotus-manage` stateful core-sourcing client,
5. evidence shape: supportability state, reason code, as-of date, transaction-date window,
   missing securities, request fingerprint/source id, source content hash, bounded curve points,
   represented observation count, observed average/min/max bps, total notional, total cost, and
   sample source transaction ids,
6. proof-pack behavior: `turnover_and_cost` carries local estimated cost separately from
   source-owned observed cost evidence.

Production boundary:

This WTBD does not claim predictive transaction-cost quotes, market-impact modeling, venue
selection, spread forecasts, execution-price estimation, or min-cost portfolio construction. Those
remain RFC39-WTBD-006 / broader execution-methodology work. `TransactionCostCurve:v1` is observed
booked-fee evidence suitable for audit, supportability, and proof-pack review.

Implementation evidence:

1. `lotus-core` source-owner implementation and tests for `TransactionCostCurve:v1`,
2. `src/infrastructure/core_sourcing/client.py`,
3. `src/core/dpm_source_context.py`,
4. `src/core/construction/models.py`,
5. `src/api/services/construction_service.py`,
6. `src/core/proof_packs/source_analytics.py`,
7. `src/core/proof_packs/builder.py`,
8. `tests/unit/dpm/infrastructure/test_core_sourcing_client.py`,
9. `tests/unit/dpm/api/test_construction_api.py`,
10. `tests/unit/dpm/proof_packs/test_proof_pack_builder.py`.

#### RFC40-WTBD-008 - Sustainability Preferences And Client Restriction Profiles

Target business outcome:

Proof packs can explain client restrictions, sustainability preferences, and ESG/restriction
controls from source-backed client governance profiles.

Current implementation-backed status:

Completed for manage proof-pack evidence authority. Proof packs can now cite source-backed client
restriction and sustainability preference profiles when the selected construction alternative
carries those profiles through the stateful core-sourcing path.

Implemented scope:

1. `AuthoritativeClientRestrictionContext` and
   `AuthoritativeSustainabilityPreferenceContext` carry source system, product name/version,
   source id, source ref, content hash, supportability status, as-of/effective dates, reason codes,
   and bounded profile entries,
2. the core-sourcing client resolves `ClientRestrictionProfile:v1` and
   `SustainabilityPreferenceProfile:v1` with the same selector payload and correlation posture as
   other DPM source products,
3. `ESG_AWARE` alternatives emit client restriction and sustainability constraint traces and use
   source profile supportability to derive ready/degraded/blocked/pending-review posture,
4. selected-alternative proof packs preserve restriction and sustainability source analytics in
   `eligibility_and_restrictions` and `sustainability_controls`,
5. missing source profiles remain degraded, hard restriction violations remain blocked, and
   sustainability classification evidence gaps remain pending review.

Validation evidence:

1. `tests/unit/dpm/infrastructure/test_core_sourcing_client.py`,
2. `tests/unit/dpm/api/test_construction_api.py`,
3. `tests/unit/dpm/proof_packs/test_proof_pack_builder.py`,
4. docs/wiki/context updates naming the exact source products and avoiding unsupported ESG approval
   claims.

Remaining boundary:

Full front-office presentation of restriction/sustainability profile detail requires Gateway and
Workbench product-surface work. Security-level sustainability classification and regulatory
suitability methodology remain source-owner responsibilities; manage only preserves the source
profiles and blocks or flags the construction evidence it can justify.

#### RFC40-WTBD-009 - Scenario-Pack Authority Beyond Supplied Context

Target business outcome:

Proof packs can cite governed CIO/risk scenario packs and regime stress context without relying on
caller-supplied metadata alone.

Current implementation status:

First-wave scenario-pack authority exists through `lotus-risk`
`RegimeScenarioPackEvaluation:v1`, and manage can consume it through RFC-0039
`REGIME_STRESS_AWARE` alternatives. RFC-0040 proof packs now preserve that source context in
`scenario_and_regime_evidence` when the selected construction alternative carries it. They can also
accept a generation-time `regime_stress_context` payload for direct proof-pack enrichment when the
selected alternative does not already carry regime-stress authority. Both paths preserve
`RegimeScenarioPackEvaluation` source refs, canonical `regime_stress_context` source hashes,
scenario pack id, worst-case loss, maximum allowed loss, supportability state, bounded reason
codes, source-supplied `governance_evidence` for CIO approval, effective-period, and portfolio
applicability posture, and bounded `scenario_evidence_posture` without manage-local scenario
methodology, approval, effective-period, applicability, or contribution calculation.
The `lotus-risk` source product now also supports
optional reconciled `exposure_components` and emits per-security `position_contributions` for each
governed scenario when callers supply those components. `lotus-risk` PR #141 adds the source-owned
governance posture registry and fail-closed reason-code/supportability behavior for bounded
CIO-approval, effective-period, and portfolio-applicability evidence.

Boundary:

RFC-0040 deliberately does not call `lotus-risk` directly to enrich proof packs; callers must
provide source-owned `RegimeScenarioPackEvaluation:v1` context when using the direct proof-pack
path. It preserves source-owned CIO approval, effective-period, and portfolio applicability fields
when present, but does not calculate scenario methodology, contribution rows, approval workflow
state, effective-period posture, or portfolio applicability locally. Broader external CIO workflow
UX/integration, mandate-level applicability beyond the source response, and any richer
scenario-specific UI remain future product depth, not a blocker for this bounded WTBD closure.

Completed implementation wave:

The source product, selected-alternative preservation path, generation-time direct proof-pack
enrichment path, and bounded proof-pack section posture mapping are implemented and audited,
including source-owned CIO approval status/reference, approval body/time, effective-period
posture, portfolio applicability posture/scope/ref, and methodology reference preservation.
Missing CIO approval/effective-period/applicability evidence is projected as `PENDING_REVIEW`,
stale/effective-period-exception source reason codes as `DEGRADED`, inapplicable source reason
codes as `BLOCKED`, and contribution-partial source reason codes as `PENDING_REVIEW`. Richer CIO
workflow UX or mandate-specific applicability should be handled only if a future product RFC
requires those workflows and the source owner exposes the required product.

Promotion proof:

1. `tests/unit/dpm/api/test_construction_api.py` and
   `tests/unit/dpm/infrastructure/test_risk_authority_client.py` cover source-owner consumption,
2. `tests/unit/dpm/proof_packs/test_proof_pack_builder.py` and
   `tests/unit/dpm/api/test_proof_pack_api.py` cover source preservation, direct
   `regime_stress_context` enrichment, supportability state mapping, source refs, source hashes,
   `approval_evidence_projected`, `effective_period_projected`,
   `applicability_evidence_projected`, `scenario_evidence_posture`,
   `REGIME_SCENARIO_EFFECTIVE_PERIOD_EXCEPTION`,
   `REGIME_SCENARIO_APPLICABILITY_NOT_CONFIRMED`,
   `REGIME_SCENARIO_CONTRIBUTION_EVIDENCE_PARTIAL`, and malformed context rejection,
3. documentation and supported-feature updates distinguish source-owned direct enrichment from
   future scenario approval evidence.
4. `lotus-risk` PR #116 (`2570e7589b51db05cf409aa022a247d56858eeda`) adds optional
   reconciled per-security scenario contribution rows to `RegimeScenarioPackEvaluation:v1`; the
   platform mirror landed through `lotus-platform` PR #321 (`026a87fe05c0cbd9e8d6d5e8d0843bbfc326188f`),
   and the `lotus-risk` wiki was published at `7bd5f03`.
5. `lotus-risk` PR #140 (`5395091612d06f1516c076390257f1cdfbc8bb94`) adds v3 auditable
   methodology truth for `RegimeScenarioPackEvaluation:v1`, including scenario formulas,
   contribution formulas, validation and failure behavior, deterministic ordering, worked
   contribution examples, Feature Lane / PR Merge Gate proof, Main Releasability Gate
   `26096158553`, and wiki publication commit `67390cc`.
6. `lotus-risk` PR #141 (`978f441ef2023d178e6c3ba4f0f361c84b856427`) adds source-owned
   `governance_evidence` for CIO approval, effective-period, and portfolio-applicability posture,
   passes Feature Lane / PR Merge Gate, publishes wiki commit `c2c6560`, and passes Main
   Releasability Gate `26098602664`.

Gold-pass assessment - 2026-05-10:

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | Manage proof packs preserve selected-alternative `RegimeScenarioPackEvaluation:v1` context in `scenario_and_regime_evidence` instead of degrading when the chosen alternative already carries source-owned regime-stress context. They also accept generation-time direct `regime_stress_context` enrichment when the selected alternative does not already carry that authority, including source-owned `governance_evidence` for CIO approval, effective-period, and portfolio-applicability posture. The proof-pack section now emits bounded `scenario_evidence_posture` and maps missing, stale/effective-period-exception, inapplicable, and contribution-partial source evidence to explicit section states and reason codes. `lotus-risk` now also owns optional reconciled per-security scenario contribution rows, v3 auditable methodology truth, and bounded scenario-pack governance posture in the same source product. |
| Quality improvements made | Scenario/regime proof-pack handling now follows the same source-owned analytics pattern as risk, performance, transaction cost, client restriction, and sustainability preference evidence. The source product now separates aggregate scenario posture from optional component-level contribution evidence and pins the scenario/contribution formulas without moving scenario methodology into manage. |
| Debt removed | The misleading gap where construction could consume scenario-pack evidence but proof packs still reported missing scenario context was removed. |
| What was proven through testing and evidence | Focused proof-pack and risk-authority tests passed and now assert source refs, source hashes, bounded scenario facts, nested `governance_evidence` consumption, scenario metrics, reason codes, direct source-context enrichment, degraded fallback behavior, `scenario_evidence_posture`, missing governance/applicability pending-review posture, source stale/effective-period-exception degraded posture, source inapplicable blocked posture, source contribution-partial pending-review posture, and malformed-context rejection. `lotus-risk` PR #116 passed Feature Lane and PR Merge Gate checks, local live API proof for contribution rows, negative 422 validation for unreconciled components, risk log review, and canonical Workbench validation for `PB_SG_GLOBAL_BAL_001`; `lotus-risk` PR #140 passed Feature Lane, PR Merge Gate, Main Releasability Gate `26096158553`, and wiki drift returned to `0`; `lotus-risk` PR #141 passed Feature Lane, PR Merge Gate, Main Releasability Gate `26098602664`, and wiki drift returned to `0`. |
| Expected-standard decision | RFC40-WTBD-009 reaches the expected standard for selected-alternative evidence preservation, direct generation-time source-context enrichment, source-owned CIO approval/effective-period/portfolio-applicability evidence projection, source-owned scenario/contribution/governance methodology posture, and bounded proof-pack state/reason-code posture. Manage does not calculate scenario methodology, approval workflow state, effective-period posture, applicability, or contribution rows locally; broader external CIO workflow UX/integration remains future product depth outside this bounded WTBD closure. |

#### RFC40-WTBD-010 - Decision Timeline And Portfolio Memory

Target business outcome:

Lotus can show a durable portfolio-management memory across mandate health, monitoring exceptions,
construction alternatives, proof packs, rebalance waves, approvals, operations handoff, and
post-trade outcomes.

Current implementation-backed scope:

The completed first-wave scope adds a source-owned portfolio-memory product path without inventing
source truth:

1. `GET /api/v1/rebalance/portfolio-memory/{portfolio_id}` returns a deterministic event timeline
   for one portfolio,
2. source events are composed from persisted RFC-0038 mandate health snapshots, RFC-0038
   monitoring exceptions, RFC-0040 proof packs, proof-pack-local decision timelines, RFC-0041
   rebalance wave events, internal operations handoff refs, and RFC-0042 outcome-review events,
3. proof-pack persistence now supports bounded portfolio/mandate/status search in both in-memory
   and PostgreSQL repository implementations,
4. event nodes preserve source systems, source types, source ids, content hashes, reason codes,
   supportability state, and bounded metadata,
5. the read model does not compute risk, performance, execution, tax, cash, FX, or source-owner
   methodology locally,
6. `lotus-gateway` PR #199 composes the manage read model at
   `/api/v1/dpm/command-center/portfolios/{portfolio_id}/memory` without reconstructing memory
   facts,
7. `lotus-workbench` PR #167 renders the first-wave `Portfolio Memory` panel from Gateway truth,
   including source system, source refs, content hash, supportability, event type counts, and
   timeline order,
8. `lotus-platform` PR #307 registers `dpm.portfolio_memory` in the governed Workbench panel
   registry and analytics observability rollout contract,
9. Workbench wiki publication commit `00c8279` published the repo-authored portfolio-memory
   feature, integration, and observability truth after merge,
10. the mandate-memory event slice adds `MANDATE_HEALTH_SNAPSHOT` and
    `MANDATE_MONITORING_EXCEPTION` event
    nodes from the existing mandate repository, preserving source lineage, supportability state,
    reason codes, monitoring run refs, and deterministic content hashes without recalculating
    mandate health,
11. this manage policy slice adds stable `event_identity` values plus aggregate and event-level
    `DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y`, `NO_RAW_PAYLOADS`, `AUDIT_READ_AND_EXPORT`, and
    `CLIENT_CONFIDENTIAL_INTERNAL` policy fields so downstream consumers inherit retention,
    redaction, audit, and access posture from the source-backed API contract,
    event identity, retention, redaction, access, and audit policy are implemented in manage,
12. `lotus-report` PR #92 adds the report-side bounded `portfolio_memory_context` consumer for
    proof-pack, rebalance-wave, and outcome-review report jobs, carrying event identity, content
    hash, supportability, retention, redaction, access, and audit posture into immutable snapshot
    lineage and render-package lineage without reconstructing portfolio-memory events,
13. `lotus-report` PR #93 adds the report-owned source-event family at
    `GET /reports/jobs/{job_id}/portfolio-memory-events`, mapping report lifecycle, snapshot,
    render, and archive evidence into stable support-safe event identities, source refs, artifact
    refs, content hashes, and retention/redaction/access/audit policy without exposing raw snapshot
    payloads or storage references,
14. this manage report-input context slice attaches bounded `portfolio_memory_context` to
    proof-pack, rebalance-wave, and outcome-review report inputs while keeping the context hash
    separate from recursive report-input evidence hashes,
15. `lotus-ai` PR #62 adds bounded portfolio-memory consumers for `dpm_pm_memo.pack@v1` and
    `outcome_review_narrative.pack@v1`; those consumers validate matching portfolio identity,
    capped event refs, source content hash, `NO_RAW_PAYLOADS`, and no-reconstruction
    source-authority policy before exposing compact lineage summaries in generated support output,
16. `lotus-ai` PR #64 adds the AI-owned workflow-pack source-event family at
    `GET /platform/workflow-packs/source-events` and
    `GET /platform/workflow-packs/runs/{run_id}/source-events`, projecting AI run, review, and
    lineage events from workflow-pack run-ledger truth with stable event identity, run/pack
    identity, workflow-authority owner, supportability posture, artifact refs, bounded source refs,
    portfolio-memory status/count/hash when supplied, `AI_WORKFLOW_PACK_SOURCE_EVENT_7Y`,
    `NO_RAW_PAYLOADS`, `AUDIT_READ_AND_EXPORT`, and `CLIENT_CONFIDENTIAL_INTERNAL` while omitting
    raw prompts, raw generated output, raw source payloads, and raw portfolio-memory event bodies,
17. `lotus-archive` PR #25 adds the archive-owned
    `lotus-archive.generated_document_client_communication.v1` source-event family at
    `GET /documents/{document_id}/source-events`, projecting generated-document archive,
    supersession, correction, and client-delivery reissue lineage with stable event ids,
    portfolio/report/render/archive refs, checksum-backed content hashes, retention/redaction/
    access/audit policy, and bounded artifact refs while omitting raw document bytes, storage keys,
    raw report payloads, and raw client references,
18. this source-event posture slice adds `source_event_family_posture` to the manage
    portfolio-memory API so the contract names supported manage, report, AI, and archive
    source-event families, explicitly marks external OMS execution as `DEFERRED_SOURCE_OWNER`, and
    points PM scoring to the separate Manage-owned score-run lifecycle product without projecting
    hidden portfolio-memory score events.

Remaining dependencies before full support claim:

None for the current source-backed portfolio-memory support claim. Future OMS execution remains a
separate source-owner roadmap scope and is explicitly published as deferred posture rather than
hidden manage support. Persisted PM operating quality score runs are supported separately; portfolio
memory still projects no PM-scoring events until a separate source-event family is governed.

Implementation proof:

1. `tests/unit/dpm/api/test_portfolio_memory_api.py`,
2. `tests/unit/dpm/proof_packs/test_proof_pack_repository.py`,
3. `tests/unit/dpm/proof_packs/test_proof_pack_postgres_repository.py`,
4. `lotus-gateway` PR #199,
5. `lotus-workbench` PR #167,
6. `lotus-platform` PR #307,
7. `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json`,
8. `lotus-workbench/output/playwright/live-canonical/dpm-portfolio-memory-live.png`,
9. `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260508-090145.json`,
10. `tests/unit/dpm/api/test_portfolio_memory_api.py` mandate health and monitoring-exception
    event assertions,
11. `tests/unit/dpm/api/test_portfolio_memory_api.py` event identity, retention, redaction,
    access, and audit policy assertions,
12. `lotus-report` PR #92,
13. `lotus-report` wiki publication commit `c743ba7`,
14. `lotus-report` PR #93,
15. `lotus-report` wiki publication commit `3d502c2`,
16. `lotus-report` post-merge focused test proof for report-owned source events:
    `REPORT_JOB_LEDGER_DATABASE_URL=postgresql://lotus_report:lotus_report@localhost:5439/lotus_report make ci`,
17. earlier `lotus-report` focused context-consumer proof:
    `python -m pytest tests/unit/reporting_render/test_service.py tests/unit/reporting_lineage/test_capture_service.py tests/unit/report_batch_orchestrator/test_boundary.py -q`,
18. Manage report-input context tests:
    `python -m pytest tests/unit/dpm/proof_packs/test_proof_pack_handoffs.py tests/unit/core/test_outcome_handoffs.py tests/unit/dpm/api/test_proof_pack_api.py tests/unit/dpm/api/test_waves_api.py -q`,
19. `lotus-ai` PR #62,
20. `lotus-ai` wiki publication commit `5267759`,
21. `lotus-ai` post-merge focused test proof:
    `python -m pytest tests/unit/test_outcome_review_narrative_guardrails.py tests/unit/test_proof_pack_pm_memo_guardrails.py tests/unit/test_workflow_pack_execution.py -q`,
22. `lotus-ai` PR #64 merge commit `7d73564`,
23. `lotus-ai` wiki publication commit `a4e70d3`,
24. `lotus-ai` focused source-event proof:
    `python -m pytest tests/integration/test_workflow_pack_run_api_contract.py::test_workflow_pack_source_events_project_ai_run_without_raw_payloads tests/integration/test_workflow_pack_run_api_contract.py::test_workflow_pack_source_event_catalog_filters_and_reports_review_lineage tests/integration/test_workflow_pack_run_api_contract.py::test_workflow_pack_run_source_events_reject_unknown_run -q`,
25. `lotus-ai` PR-grade local proof:
    `make check`,
26. `lotus-archive` PR #25 merge commit `aa3a3a8f28b666cb85100c0859f77ff2dab9cede`,
27. `lotus-archive.wiki` publication commit `d5e5918`,
28. `lotus-archive` local and GitHub proof:
    `make check`, `make ci`, `make docker-build`, PR Feature Lane, PR Merge Gate, coverage gate,
    security audit with no known vulnerabilities, Docker validation, and post-merge focused proof
    `python -m pytest tests/unit/test_archive_document_service.py tests/integration/test_archive_documents_api.py tests/unit/test_archive_openapi_contract.py tests/unit/test_documentation_posture.py tests/e2e/test_smoke.py -q`,
29. manage source-event posture proof:
    `python -m pytest tests/unit/dpm/api/test_portfolio_memory_api.py -q`,
30. manage API governance proof:
    `make openapi-gate`, `make api-vocabulary-gate`.

Promotion proof still required:

1. source-owner tests, API documentation, and canonical proof for any future OMS execution or
   PM-scoring product before those separate deferred families can move to `SUPPORTED`.

### Suggested Sequencing

Recommended order:

1. implement Gateway proof-pack composition,
2. implement Workbench proof-pack review UX,
3. resolve canonical front-office readiness blockers and prove full product realization,
4. implement report materialization in report/render/archive owners,
5. implement AI PM memo generation in `lotus-ai` under RFC-0043 controls,
6. add broader risk/performance enrichment from owning analytics services,
7. add transaction-cost, sustainability/restriction, and scenario-pack source products,
8. extend portfolio memory with future OMS/PM-scoring source events as those owning products
   mature.

Rationale:

Gateway and Workbench can realize the already-supported manage proof-pack backend before broader
source enrichment exists. Report and AI should follow their owning-service controls. Risk,
performance, cost, sustainability, restriction, and scenario enrichment should be promoted only
after source authorities are certified. Portfolio memory now has a manage-owned read model plus
first-wave Gateway/Workbench product realization because mandate health, monitoring exceptions,
proof-pack, wave, handoff, and post-trade outcome events exist. Manage also owns event identity,
retention, redaction, access, audit policy, and source-event family posture for the projected
timeline. Report now has an owning-app consumer seam for bounded portfolio-memory context, AI now
has an owning-app source-event family over workflow-pack run/review/lineage posture, and archive
now has an owning-app generated-document/client-delivery reissue source-event family. The broader
WTBD is complete for the current bank-buyable support claim because external OMS execution and PM
scoring are visible deferred source-owner boundaries, not implicit manage functionality.

### RFC-0040 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and API/source contract are explicit,
2. manage remains proof-pack authority and does not clone report, AI, Gateway, Workbench, risk,
   performance, cost, sustainability, restriction, or scenario behavior,
3. Gateway and Workbench consume through the governed product path,
4. report/AI/archive products preserve proof-pack hashes and lineage,
5. degraded, blocked, stale, partial, unavailable, permission-denied, redacted, and
   human-review-required states are tested where applicable,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC/source-map, wiki, supported-features, endpoint certification, and repository context
   are aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.
## RFC-0041 - Rebalance Wave Orchestration And CIO Model Change Impact

Current closure status:

RFC-0041 is `DONE` for the `lotus-manage` owned backend authority over explicit portfolio-list
rebalance waves. The delivered scope includes durable preview/create, source-check,
RFC-0039-backed ready-item simulation, item selection, RFC-0040 proof-pack linkage,
approval-with-exceptions, staging, internal operations handoff evidence with
`external_execution_claimed=false`, pre-execution cancellation, wave search/detail/item/proof-pack
posture/supportability read models, OpenAPI certification, Postgres-backed persistence, live proof,
hardening, documentation, wiki publication, and supported-feature promotion.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md` |
| Source-map and gap analysis | `docs/rfcs/RFC-0041-source-map-and-gap-analysis.md` |
| Supported feature claim | `wiki/Supported-Features.md` |
| Live proof | `output/rfc0041-wave-proof/20260504-231914/manifest.json` and `critical-review.json` |
| Manage implementation | `src/core/waves/`, `src/api/services/wave_service.py`, `src/api/routers/waves.py`, `src/infrastructure/waves/` |
| Tests | `tests/unit/dpm/api/test_waves_api.py`, `tests/unit/dpm/waves/test_wave_domain.py`, `tests/unit/dpm/waves/test_source_readiness.py` |

### Remaining Work Summary

These items are deliberately not done in RFC-0041 because they require source-owned data products,
downstream product-surface implementation, or owning-service materialization outside
`lotus-manage`.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0041 |
| --- | --- | --- | --- | --- |
| RFC41-WTBD-001 | Automatic PM-book / portfolio-manager cohort discovery | `lotus-core` source authority consumed by `lotus-manage` | Completed, merged, CI-proven, and wiki-published through `lotus-core` PR #339 and `lotus-manage` PR #126 | `lotus-core` now owns `PortfolioManagerBookMembership:v1`; `lotus-manage` consumes it for `PM_BOOK_REVIEW` wave preview/create without caller-supplied portfolio fabrication. |
| RFC41-WTBD-002 | Automatic CIO model-change affected-mandate discovery | `lotus-core` source authority consumed by `lotus-manage` | Completed in this slice for source-owned affected-cohort waves | `lotus-core` now owns `CioModelChangeAffectedCohort:v1`; `lotus-manage` consumes it for `CIO_MODEL_CHANGE` preview/create without caller-supplied portfolio fabrication. |
| RFC41-WTBD-003 | Tactical house-view, risk-event, and campaign/bulk-review cohorts | CIO/risk/campaign source owners, with `lotus-risk` owning the first risk-event cohort source product, `lotus-advise` owning the first tactical house-view cohort source product, `lotus-manage` owning the first campaign membership and discovery envelope, `lotus-gateway` owning campaign-definition BFF composition, and `lotus-workbench` owning bounded campaign-definition rendering | Partial: `lotus-risk` `RiskEventAffectedCohort:v1` is merged, CI-proven, wiki-published, and mirrored in platform mesh governance; `lotus-manage` consumes it for `RISK_EVENT` preview/create. `lotus-advise` `TacticalHouseViewAffectedCohort:v1` is merged, CI-proven, and wiki-published as source-owned affected-cohort evidence; `lotus-manage` consumes it for bounded `TACTICAL_HOUSE_VIEW` preview/create. `lotus-manage` now also supports bounded `BULK_REVIEW_CAMPAIGN` preview/create through `BulkReviewCampaignMembership:v1` over source-backed candidate portfolios with optional approval, expiry, and actor-entitlement governance evidence, plus persisted `BulkReviewCampaignDiscovery:v1` summaries at `GET /api/v1/rebalance/waves/campaign-discovery`, bounded campaign operating queue at `GET /api/v1/rebalance/waves/campaign-operating-queue`, bounded read-only campaign approval-attention inbox at `GET /api/v1/rebalance/waves/campaign-approval-inbox`, bounded read-only workflow board at `GET /api/v1/rebalance/waves/campaign-workflow-board`, bounded read-only assignment plan at `GET /api/v1/rebalance/waves/campaign-assignment-plan`, bounded read-only workflow automation readiness at `GET /api/v1/rebalance/waves/campaign-workflow-automation`, fail-closed campaign-definition preview readiness at `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness`, bounded campaign-definition launch packages at `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package`, deterministic durable launch at `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch`, paged launch-history audit evidence at `GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-history`, append-only campaign approval-decision evidence at `POST`/`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions`, append-only assignment-action evidence, controlled assignment-task lifecycle evidence at `POST`/`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks` plus transition evidence at `POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions`, and append-only maker-checker control evidence at `POST`/`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls`. `lotus-gateway` PR #212 exposes campaign-definition list/get/upsert BFF routes under `/api/v1/dpm/command-center/waves/campaign-definitions*`; PR #231 (`ea6c036`, Main Releasability Gate `25989936539`) extends bounded lifecycle-events, launch-history, launch-package, durable launch, and campaign-discovery BFF preservation without local cohort, readiness, order, or OMS calculation. `lotus-workbench` PR #184 renders the active campaign-definition list through Gateway/BFF; PR #244 (`31ea877`, Main Releasability Gate `25989936388`) validates Gateway-only READY-gated launch and paged launch-history/empty-state/no-order/no-OMS boundary rendering without browser-side cohort, membership, readiness, or execution calculation. | Global portfolio-universe campaign discovery and external workflow orchestration beyond Manage-side task readiness remain future depth. |
| RFC41-WTBD-004 | Risk and performance aggregate enrichment for waves | `lotus-risk`, `lotus-performance`, consumed by `lotus-manage` and later `lotus-gateway` | Completed in this slice for manage aggregate authority | RFC-0041 aggregate impact is carried from source-owned risk/performance authority context into wave aggregate metrics with supportability, lineage refs, source reason codes, and source-emitted scalar values. Manage does not calculate risk or performance methodology locally. |
| RFC41-WTBD-005 | Gateway wave composition | `lotus-gateway` | Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #196 | Completed after manage contracts stabilized. Gateway composes manage truth without becoming wave authority or reconstructing state. |
| RFC41-WTBD-006 | Workbench wave command center | `lotus-workbench` with `lotus-gateway`, `lotus-platform`, and `lotus-manage` support | Completed, merged, CI-proven, live-proven, and wiki-published through Manage PR #120, Gateway PR #197, Platform PR #306, and Workbench PR #165 | Workbench now consumes Gateway/BFF routes only and provides the PM operating cockpit over explicit portfolio-list waves. |
| RFC41-WTBD-007 | Full front-office command-center product support | `lotus-gateway`, `lotus-workbench`, with manage as backend authority | Completed for first-wave wave command-center product support through Manage PR #120, Gateway PR #197, Platform PR #306, Workbench PR #165, and canonical QA | The canonical front-office path now renders the wave command center from Gateway/manage truth and captures validated screenshot evidence. Risk-event, tactical house-view, bounded campaign membership, and active campaign-definition list rendering are supported separately; global campaign discovery, broader campaign workflow surfaces, richer source-owner cohorts, and external OMS execution remain separate WTBDs. |
| RFC41-WTBD-008 | Report materialization from wave/proof-pack evidence | `lotus-manage`, `lotus-report`, `lotus-render`, `lotus-archive` | Completed, merged, CI-proven, and wiki-published through `lotus-manage` PR #124, `lotus-report` PR #91, `lotus-render` PR #12, and `lotus-archive` PR #24 | Manage exposes deterministic wave report input while report/render/archive own generated report, template, and archive lifecycle. |
| RFC41-WTBD-009 | AI PM memo generation from wave evidence | `lotus-ai`, governed by RFC-0043 direction; `lotus-gateway` and `lotus-workbench` as product consumers | Completed, merged, CI-proven, live-proven, and wiki-published where changed through `lotus-ai` PR #63, `lotus-gateway` PR #201, and `lotus-workbench` PR #168 | `lotus-ai` owns `dpm_wave_pm_memo.pack@v1` for bounded `DpmWaveReportInput` memo assistance. Gateway preserves Manage evidence identity and AI guardrails, while Workbench exposes report-input and AI memo request posture without constructing prompts or memo content locally. |
| RFC41-WTBD-010 | External execution integration | Future execution/OMS owner or governed operations integration | Out of RFC-0041 scope | RFC-0041 intentionally stops at internal operations handoff evidence and preserves `external_execution_claimed=false`. |

### RFC41 Gold-Pass Audit And RFC Reintegration - 2026-05-09

The 2026-05-09 audit moved completed RFC41 WTBD truth into
`RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md` and refreshed the wiki
source so the current implementation record is available from the owning RFC.

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | Manage owns wave preview/create/source-check/simulate/select/approve/stage/handoff/cancel/search/supportability/proof-pack/report-input authority. Source-owned PM-book and CIO model-change cohorts are implemented. Gateway wave composition, Workbench wave command center, governed wave report materialization, and review-gated wave PM memo handoff are implemented in owning repositories. |
| Quality improvements made | The audit removes stale backend-only RFC wording and keeps manage as wave authority while acknowledging the merged first-wave product path. It separates completed wave command-center support from future tactical/risk/campaign cohorts and external OMS execution. |
| Debt removed | Stale WTBD wording that listed full front-office wave support as proposed was retired. Unsupported execution and source-owner cohort claims remain explicit instead of being hidden behind broad command-center wording. |
| What was proven through testing and evidence | Existing manage proof remains anchored in `output/rfc0041-wave-proof/20260504-231914` and `output/rfc0041-wave-proof/20260507-224144`. First-wave product proof remains anchored in `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-142715.json`, `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260507-143459.json`, and `lotus-workbench/output/playwright/live-canonical/dpm-wave-command-center-live.png`. The 2026-05-09 audit reran canonical front-office QA successfully with report `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260509-225912.json`, Markdown summary `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260509-225912.md`, DPM seed evidence `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260509-230635.json`, and screenshots in `lotus-platform/output/front-office-qa/wtbd-rfc40-audit-20260509`. |
| Expected-standard decision | RFC41 reaches the expected standard for manage-owned wave authority and the bounded first-wave product path on merged `lotus-manage` `main` truth with synchronized wiki publication and clean final branch hygiene. |

### Detailed Follow-Up Items

#### RFC41-WTBD-001 - Automatic PM-Book / Portfolio-Manager Cohort Discovery

Target business outcome:

Portfolio managers can start a rebalance wave for their governed book without manually supplying
every portfolio id, and the resulting cohort is source-backed, permission-aware, fresh, and
reconcilable.

Implementation status:

`lotus-core` source ownership is merged through PR #339 with `PortfolioManagerBookMembership:v1`.
`lotus-manage` now consumes that source product for `PM_BOOK_REVIEW` wave preview/create. Callers
supply the portfolio manager selector, as-of date, tenant/booking-center filters, and eligible
portfolio types; manage rejects caller-supplied portfolios for this trigger and builds wave items
only from lotus-core membership evidence. Explicit portfolio-list waves remain supported.

Support boundary:

1. supported: `PM_BOOK_REVIEW` backed by lotus-core `PortfolioManagerBookMembership:v1`,
2. supported: explicit source refs on each resolved item plus trigger-level PM-book snapshot refs,
3. supported: source dependency failures return blocked dependency posture instead of fabricating
   a cohort,
4. supported: `CIO_MODEL_CHANGE` backed by lotus-core `CioModelChangeAffectedCohort:v1`,
5. supported separately: risk-event, tactical house-view, and bounded bulk-review campaign waves
   through their owning source products or manage-owned campaign envelope,
6. unsupported: global portfolio-universe campaign discovery, permission-denied, and stale-book
   cohort semantics until owning source products exist,
7. unsupported: external OMS execution.

Promotion proof:

1. source-owner foundation merged and wiki-published in `lotus-core` PR #339,
2. manage implementation merged in PR #126 and CI-proven by Feature Lane and PR Merge Gate,
3. manage focused tests prove source-product client, PM-book preview/create, invalid selector,
   unavailable/incomplete/empty dependency handling, and source-owned empty-cohort validation,
4. full local coverage proof passed with `make check-all`: 1173 tests passed and coverage reached
   99.02%,
5. repo-local wiki source was published after merge and `Sync-RepoWikis.ps1 -CheckOnly
   -Repository lotus-manage` returned diff count 0,
6. README/wiki/supported-features state the exact promoted trigger path.

#### RFC41-WTBD-002 - Automatic CIO Model-Change Affected-Mandate Discovery

Target business outcome:

A CIO model change can produce a governed wave over the affected mandates without manually
supplying every portfolio id, with clear explanation of why each mandate is in scope.

Implementation status:

`lotus-core` source ownership is implemented in this slice with
`CioModelChangeAffectedCohort:v1`. The source product resolves the approved model definition for
the requested as-of date, emits a deterministic `model_change_event_id`, and returns effective
active discretionary mandate bindings with source lineage, snapshot identity, supportability, and
data-quality posture. `lotus-manage` consumes that product for `CIO_MODEL_CHANGE` wave preview and
create. Callers supply `model_portfolio_id`, as-of date, optional tenant, and booking-center
filters; manage rejects caller-supplied portfolios for this trigger and builds wave items only from
lotus-core affected-mandate evidence.

Support boundary:

1. supported: `CIO_MODEL_CHANGE` backed by lotus-core `CioModelChangeAffectedCohort:v1`,
2. supported: trigger-level source refs for the cohort snapshot and model-change event,
3. supported: item-level source refs for affected mandate binding rows and existing mandate digital
   twin refs,
4. supported: unavailable, incomplete, empty, invalid-selector, and caller-supplied-portfolio
   failures return explicit dependency or validation posture,
5. supported separately: risk-event, tactical house-view, and bounded bulk-review campaign waves
   through their owning source products or manage-owned campaign envelope,
6. unsupported: global campaign discovery, permission-denied, stale-cohort, external OMS execution,
   and broader campaign workflow surfaces until owning slices implement and prove those paths.

Promotion proof:

1. source-owner route, service, repository, source-catalog, security-profile, route-registry, and
   domain-product tests pass in `lotus-core`,
2. manage source-client and wave API tests prove source-ready preview/create, invalid selector,
   unavailable/incomplete/empty dependency handling, and caller-supplied portfolio rejection,
3. source refs show the model-change event id, cohort snapshot, affected mandate binding, and
   mandate digital-twin lineage,
4. supported-features and wiki truth distinguish source-owned automatic model-change cohorts from
   the separate bounded risk-event, tactical house-view, campaign membership, and external
   execution boundaries,
5. live Gateway/Workbench product rendering remains a future downstream support claim.

#### RFC41-WTBD-003 - Tactical House-View, Risk-Event, And Implicit Campaign Cohorts

Target business outcome:

CIO, risk, or operations teams can launch governed waves for tactical house views, market/risk
events, or bulk review campaigns from source-owned campaign definitions rather than raw portfolio
lists.

Completed risk-event result:

`lotus-risk` now owns the first certified risk-event source authority for this WTBD:
`RiskEventAffectedCohort:v1` at `POST /analytics/risk/risk-event-cohorts/evaluate`. The product
was merged through `lotus-risk` PR #115 as
`bd69d1576d8c01bdcfd2309202ef37f780cc2d06`, published to `lotus-risk.wiki` commit `91f933a`,
and mirrored into platform mesh governance through `lotus-platform` PR #313
(`4218d4319d5dac82e87106429fadb14247c36515`).

`lotus-manage` now consumes that source product for bounded `RISK_EVENT` wave preview and durable
create. Callers must supply candidate portfolios and source-supplied `exposure_weights`; manage
forwards that candidate set to lotus-risk, requires `risk_event_id`, `as_of_date`, and a ready,
non-empty `RiskEventAffectedCohort:v1` response, and preserves source-owned cohort, event, affected
portfolio, candidate, and mandate-digital-twin source refs. Missing configuration, unavailable
source authority, rejected source requests, incomplete supportability, empty affected cohorts, empty
exposure weights, negative exposure weights, and invalid dates all fail closed with explicit error
codes. Manage does not discover the full book, compute risk-event impact, infer risk buckets, or
create campaign membership locally.

This slice adds the bounded manage-owned campaign result. `lotus-manage` now supports
`BULK_REVIEW_CAMPAIGN` preview/create through `BulkReviewCampaignMembership:v1`. Callers supply
source-backed candidate portfolios, source-owned `portfolio_type`, source refs, as-of date, and
eligible DPM portfolio types. Manage filters out non-eligible portfolio types, emits deterministic
membership and member source refs with a content hash, preserves source refs from underlying
facts or calculated cohorts, and fails closed for missing candidates, missing portfolio type,
missing source refs, invalid date, empty eligible portfolio-type filters, or no eligible DPM
members. Optional campaign governance evidence now preserves approval reference, approver,
approval time, expiry date, access purpose, source refs, and actor entitlement allow-list; expired
campaigns, incomplete approval evidence, invalid expiry dates, and unauthorized actors fail closed.
Manage does not discover the full book, calculate holdings/risk/performance/advisory reasons,
run a maker-checker workflow, or claim broad campaign workflow support.

This slice adds the bounded tactical house-view manage-consumer result. `lotus-advise` owns the
governed bank-wide `TacticalHouseViewAffectedCohort:v1` source product for bank-authored tactical
house-view instructions over source-backed candidate portfolios. `lotus-manage` now supports
`TACTICAL_HOUSE_VIEW` preview/create by requiring the bank-authored tactical view payload,
tactical-view source refs, source-backed candidate portfolios, source-owned portfolio type,
source-owned discretionary mandate posture, candidate source refs, eligible DPM portfolio types,
and optional minimum tactical exposure weight. Manage forwards that evidence to lotus-advise,
requires a ready non-empty source cohort, preserves Advise cohort, house-view, affected-portfolio,
candidate, and mandate refs, and fails closed for missing configuration, rejected source requests,
unavailable source authority, incomplete supportability, empty affected cohorts, invalid dates, and
missing source evidence. Manage does not compute house-view eligibility, holdings exposure,
alignment, DPM mandate posture, portfolio membership, or advisory/CIO policy locally.

The broader WTBD remains partial because broader campaign workflow surfaces and global
portfolio-universe campaign discovery remain future depth. `lotus-manage` now exposes bounded
persisted campaign discovery through `BulkReviewCampaignDiscovery:v1` at
`GET /api/v1/rebalance/waves/campaign-discovery`, summarizing campaign identity, governance
posture, expiry posture, source-ref count, source-backed candidate counts, and preview references
without discovering the global portfolio universe or recalculating membership. `lotus-gateway` PR
#212 now composes the manage-owned campaign-definition list/get/upsert APIs under
`/api/v1/dpm/command-center/waves/campaign-definitions*`, and PR #231 (`ea6c036`, Main
Releasability Gate `25989936539`) extends bounded lifecycle-events, launch-history, launch-package,
durable launch, and campaign-discovery BFF preservation without recomputing cohort facts, campaign
membership, portfolio eligibility, readiness, idempotency, order, or OMS posture. `lotus-workbench`
PR #184 renders the active campaign-definition list through Gateway/BFF, and PR #244 (`31ea877`,
Main Releasability Gate `25989936388`) validates Gateway-only READY-gated launch and paged
launch-history/empty-state/no-order/no-OMS boundary rendering without browser-side cohort,
membership, readiness, or execution calculation. Future campaign depth should expand the now-promoted
manage-owned membership and persisted-discovery envelope with broader workflow behavior only after
those controls are proven.

2026-05-16 campaign-definition supersession addendum:

`lotus-manage` now supports bounded campaign-definition supersession at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede`.
The replacement definition must already exist, use the same campaign id, and remain `ACTIVE`.
The old definition becomes `SUPERSEDED`, records the replacement campaign version and content hash,
remains visible through list/get/discovery for audit, and fails closed for new
`BULK_REVIEW_CAMPAIGN` preview/create. Supersession is implemented in the domain lifecycle module
`src/core/waves/campaign_definition_lifecycle.py`, keeping lifecycle rules out of the API router.
This is still a bounded Manage-owned lifecycle control only; it does not discover a global
portfolio universe, calculate source-owned facts, run maker-checker workflow, or claim OMS
execution.

2026-05-16 campaign-definition lifecycle-event projection addendum:

`lotus-manage` now exposes bounded campaign-definition lifecycle events at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/lifecycle-events`.
The endpoint projects `CREATED`, `RETIRED`, and `SUPERSEDED` events from the persisted
`BulkReviewCampaignDefinition:v1` record, including event actor, timestamp, business reason,
correlation id, status-after, content hash, and replacement version/hash for supersession events.
The event-builder lives in `src/core/waves/campaign_definition_events.py`, keeping read-model
projection out of the API router. This is a read-only audit surface over Manage-owned campaign
definition lifecycle truth; it does not discover campaign membership, calculate source facts,
create maker-checker workflow state, or claim OMS execution.

2026-05-17 campaign-definition preview-readiness addendum:

`lotus-manage` now exposes bounded campaign-definition preview readiness at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness`.
The endpoint evaluates whether a persisted `BulkReviewCampaignDefinition:v1` can be used for new
`BULK_REVIEW_CAMPAIGN` preview/create by checking lifecycle status, requested as-of date,
source-backed candidate eligibility, governance approval completeness, expiry posture, optional
actor entitlement, lifecycle-event count, source-ref count, and deterministic content hash. The
readiness builder lives in `src/core/waves/campaign_definition_readiness.py`, keeping business
logic out of the router. It fails closed with reason codes instead of recalculating membership,
discovering a global portfolio universe, creating maker-checker workflow, approving trades, or
claiming OMS execution.

2026-05-17 campaign-definition launch-package addendum:

`lotus-manage` now exposes bounded campaign-definition launch packages at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package`
and deterministic durable launch at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch`.
The endpoint returns `BulkReviewCampaignDefinitionLaunchPackage:v1` with nested preview-readiness,
the exact `BULK_REVIEW_CAMPAIGN` preview/create request draft, durable-create idempotency and
correlation headers, operating-boundary reason codes, and a deterministic package hash. The
builder lives in `src/core/waves/campaign_definition_launch_package.py`, keeping launch-package
assembly out of the router. It does not create a wave, recalculate campaign membership, discover a
global portfolio universe, create maker-checker workflow, approve trades, or claim OMS execution.
The launch endpoint consumes the same package, creates one durable `BULK_REVIEW_CAMPAIGN` wave
only when launch state is `READY`, replays with the deterministic launch idempotency key, and fails
closed before persistence when readiness is blocked. Successful launches append bounded launch
history to the persisted definition and project `LAUNCHED` lifecycle events with wave id, actor,
requested as-of date, correlation id, and idempotency key, without adding maker-checker,
trade-approval, order-routing, or OMS claims.

2026-05-17 campaign-definition launch-history audit-page addendum:

`lotus-manage` now exposes bounded campaign-definition launch history at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-history`.
The endpoint returns `BulkReviewCampaignDefinitionLaunchHistory:v1` with paged append-only launch
records, total count, wave id, actor, requested as-of date, correlation id, idempotency key, and
explicit no-maker-checker/no-trade-approval/no-order/no-OMS operating boundaries. The page builder
lives in `src/core/waves/campaign_definition_launch_history.py`, so downstream consumers can read
launch audit posture without fetching the full definition payload or inferring launch records from
generic lifecycle events. It does not recalculate membership, discover a global portfolio universe,
approve trades, generate orders, route orders, certify fills, settle trades, or claim OMS execution.

2026-05-19 campaign-definition workflow-overview addendum:

`lotus-manage` now exposes a bounded campaign-definition workflow overview at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview`.
The endpoint returns `BulkReviewCampaignDefinitionWorkflowOverview:v1`, composing persisted
campaign discovery posture, fail-closed preview readiness, lifecycle events, launch history, and
optional launch-package guidance for a requested as-of date and actor. The builder lives in
`src/core/waves/campaign_definition_workflow_overview.py`, keeping orchestration logic out of the
router and reusing the existing discovery, readiness, lifecycle-event, launch-history, and
launch-package domain modules. It gives Gateway/Workbench a single operator-safe read model for
campaign-definition workflow state while preserving the no-global-universe, no-source-recalculation,
no-maker-checker, no-trade-approval, no-order, and no-OMS boundaries.

2026-05-20 campaign operating-queue addendum:

`lotus-manage` now exposes a bounded campaign operating queue at
`GET /api/v1/rebalance/waves/campaign-operating-queue`. The endpoint returns
`BulkReviewCampaignOperatingQueue:v1`, classifying persisted `BulkReviewCampaignDefinition:v1`
records into `READY_TO_LAUNCH`, `ATTENTION_REQUIRED`, and `CLOSED` rows by composing existing
campaign discovery, fail-closed preview readiness, lifecycle event counts, and launch-history
posture. The builder lives in `src/core/waves/campaign_operating_queue.py`, so queue policy stays
out of the API router and reuses existing campaign read models instead of duplicating readiness or
membership logic. This is an operator read model only: it does not discover the global portfolio
universe, recalculate source facts, mutate approval state, run maker-checker workflow, approve
trades, generate orders, route orders, or claim OMS execution.

2026-05-20 campaign approval-attention inbox addendum:

`lotus-manage` now exposes a bounded read-only campaign approval-attention inbox at
`GET /api/v1/rebalance/waves/campaign-approval-inbox`. The endpoint returns
`BulkReviewCampaignApprovalInbox:v1`, classifying persisted `BulkReviewCampaignDefinition:v1`
records into `APPROVAL_COMPLETE`, `APPROVAL_REQUIRED`, `APPROVAL_INCOMPLETE`,
`EXPIRY_ATTENTION`, `ENTITLEMENT_ATTENTION`, and `CLOSED` rows by composing existing campaign
discovery and fail-closed preview readiness posture. The builder lives in
`src/core/waves/campaign_approval_inbox.py`, so approval-attention routing stays out of the API
router and reuses governed definition/readiness truth. This is an attention read model only: it
does not mutate approval state, implement maker-checker workflow, approve trades, generate orders,
route orders, or claim OMS execution.

2026-05-20 campaign approval-decision ledger addendum:

`lotus-manage` now exposes append-only campaign approval-decision evidence at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions`
and bounded approval-decision audit pages at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions`.
The endpoint records `APPROVED`, `REJECTED`, or `REQUIRES_REMEDIATION` decisions on active
`BulkReviewCampaignDefinition:v1` records, returns deterministic decision ids and content hashes,
and rejects conflicting reuse of a `decision_ref`. The page returns
`BulkReviewCampaignDefinitionApprovalDecisionPage` with latest-decision posture and pagination.
The builder lives in `src/core/waves/campaign_definition_approval_decisions.py`, so approval
posture mutation stays in domain code and repository adapters only persist an updated definition.
This is campaign approval posture evidence only: it does not implement maker-checker workflow,
approve trades, generate or route orders, contact clients, discover the global portfolio universe,
recalculate membership, or claim OMS execution.

2026-05-20 campaign workflow-board addendum:

`lotus-manage` now exposes a bounded read-only cross-actor campaign workflow board at
`GET /api/v1/rebalance/waves/campaign-workflow-board`. The endpoint returns
`BulkReviewCampaignWorkflowBoard:v1`, composing existing `BulkReviewCampaignOperatingQueue:v1` and
`BulkReviewCampaignApprovalInbox:v1` posture into actor-aware next-action rows for
`LAUNCH_CAMPAIGN`, `RECORD_APPROVAL_DECISION`, `REMEDIATE_APPROVAL_EVIDENCE`,
`REFRESH_EXPIRY_OR_AS_OF_DATE`, `REVIEW_ACTOR_ENTITLEMENT`, `REVIEW_CAMPAIGN_ATTENTION`, and
`NO_ACTION_CLOSED`. The builder lives in `src/core/waves/campaign_workflow_board.py`, so the API
router remains a thin query boundary and does not duplicate readiness, expiry, entitlement,
approval, launch, or lifecycle classification logic.

This advances the broader cross-actor campaign workflow surface by providing one operator-safe
board over the existing read models. It does not close RFC41-WTBD-003 because global
portfolio-universe discovery and richer assignment/escalation workflow beyond this read-only board
remain future depth.

2026-05-20 campaign assignment-plan addendum:

`lotus-manage` now exposes a bounded read-only campaign assignment and escalation plan at
`GET /api/v1/rebalance/waves/campaign-assignment-plan`. The endpoint returns
`BulkReviewCampaignAssignmentPlan:v1`, deriving actor routing, escalation tier, SLA posture, and
reason codes from the workflow board without mutating assignment state, creating escalation tasks,
mutating approval state, creating maker-checker workflow, approving trades, generating orders, or
claiming OMS execution. The builder lives in `src/core/waves/campaign_assignment_plan.py`, and it
reuses `BulkReviewCampaignWorkflowBoard:v1` so assignment/escalation classification stays
composed from existing read models instead of duplicating readiness, approval, queue, or lifecycle
logic.

This advances the richer assignment/escalation surface from a generic board into a dedicated
operator read model with explicit PM, operations, and governance escalation tiers. It does not
close RFC41-WTBD-003 because global portfolio-universe discovery and broader workflow automation
beyond controlled Manage-side assignment tasks remain future depth.

2026-05-20 campaign assignment-task lifecycle addendum:

`lotus-manage` now exposes controlled campaign assignment and escalation tasks at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`,
task transitions at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions`,
and bounded task pages at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks`.
The list endpoint returns `BulkReviewCampaignDefinitionAssignmentTaskPage`.
The domain records `ASSIGNMENT`, `APPROVAL_REMEDIATION`, `ENTITLEMENT_REVIEW`,
`EXPIRY_REVIEW`, and `ESCALATION` task types with controlled `OPEN`, `ACKNOWLEDGED`,
`IN_PROGRESS`, `BLOCKED`, `RESOLVED`, and `CANCELLED` statuses. Transitions preserve
deterministic task and transition ids, conflict-safe refs, actor attribution, reason,
correlation id, assignees, escalation tier, SLA posture, optional due date, source refs,
append-only transition evidence, and page-level status/escalation/SLA counts.
The builder and transition rules live in `src/core/waves/campaign_assignment_tasks.py`, keeping
task lifecycle state out of the API router and infrastructure adapters.

This advances RFC41-WTBD-003 from read-only assignment planning and append-only posture ledgers
into a bounded mutable Manage-side task lifecycle. It mutates only assignment task state and does
not mutate approval state, create maker-checker workflow, approve trades, generate or route
orders, contact clients, orchestrate external workflow systems, discover the global portfolio
universe, recalculate membership, or claim OMS execution. RFC41-WTBD-003 remains partial for
global portfolio-universe campaign discovery and broader workflow automation beyond controlled
Manage-side assignment tasks.

2026-05-20 campaign workflow-automation readiness addendum:

`lotus-manage` now exposes bounded read-only campaign workflow automation readiness at
`GET /api/v1/rebalance/waves/campaign-workflow-automation`. The endpoint returns
`BulkReviewCampaignWorkflowAutomation:v1`, composing `BulkReviewCampaignAssignmentPlan:v1` with
existing controlled assignment-task state to classify `AUTOMATION_CANDIDATE`,
`MANUAL_REVIEW_REQUIRED`, `BLOCKED`, and `CLOSED` rows. Candidate rows include a deterministic
proposed task type and task ref for idempotent downstream use of the existing assignment-task
endpoint; active rows surface non-closed task refs for monitoring; blocked rows surface blocked or
breached task refs for escalation. The builder lives in
`src/core/waves/campaign_workflow_automation.py`, keeping automation classification out of the API
router and preserving reusable domain logic.

This advances RFC41-WTBD-003 beyond controlled assignment-task mutation into a bounded
Manage-side automation-readiness projection. It does not mutate tasks, orchestrate external
workflow systems, create maker-checker workflow, contact clients, approve trades, generate or route
orders, discover the global portfolio universe, recalculate membership, or claim OMS execution.
RFC41-WTBD-003 remains partial for global portfolio-universe campaign discovery and any external
workflow orchestration beyond Manage-side task readiness and append-only evidence ledgers.

2026-05-20 campaign maker-checker control addendum:

`lotus-manage` now exposes append-only campaign maker-checker control evidence at
`POST /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls`
and bounded maker-checker control audit pages at
`GET /api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls`.
The endpoint records `SUBMITTED_FOR_REVIEW`, `REVIEWER_ASSIGNED`, `REVIEW_COMPLETED`,
`CONTROL_EXCEPTION_RAISED`, and `CONTROL_EXCEPTION_RESOLVED` actions on active
`BulkReviewCampaignDefinition:v1` records, returns deterministic control ids and content hashes,
rejects conflicting reuse of a `control_ref`, and requires distinct submitter and reviewer actors
for completed reviews. The page returns
`BulkReviewCampaignDefinitionMakerCheckerControlPage` with latest control action, control outcome,
reviewer posture, and pagination. The builder lives in
`src/core/waves/campaign_maker_checker_controls.py`, so control mutation stays in domain code and
repository adapters only persist an updated definition.

This advances the campaign maker-checker gap from unsupported approval-decision-only posture into
a bounded Manage-side control ledger. It does not approve trades, generate or route orders,
contact clients, orchestrate external workflow systems, discover the global portfolio universe,
recalculate membership, or claim OMS execution. RFC41-WTBD-003 remains partial for global
portfolio-universe campaign discovery and broader workflow automation beyond controlled
Manage-side assignment tasks.

Portfolio-memory campaign workflow event projection addendum: `GET
/api/v1/rebalance/portfolio-memory/{portfolio_id}` and the bounded search index now project
persisted `BulkReviewCampaignDefinition:v1` evidence for matching source-backed candidate
portfolios. The projection emits `BULK_REVIEW_CAMPAIGN_DEFINITION`,
`BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION`, `BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION`,
`BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK`, and `BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL`
events with stable event identity, source refs, content hashes, supportability posture, and
bounded metadata. It deliberately does not copy raw campaign payloads, discover the global
portfolio universe, recalculate membership, orchestrate an external workflow engine, contact
clients, approve trades, route orders, or claim OMS execution. This improves RFC41-WTBD-003
operating evidence and RFC40-WTBD-010 portfolio memory depth but does not close the remaining
global discovery or external workflow automation scope.

Dependencies before remaining tactical/campaign implementation:

1. owner for each cohort family is assigned,
2. cohort source APIs expose membership, rationale, source refs, freshness, permissions, and
   exclusion rules,
3. risk-event cohorts continue to come from `lotus-risk` `RiskEventAffectedCohort:v1`,
4. tactical house-view cohorts continue to come from `lotus-advise`
   `TacticalHouseViewAffectedCohort:v1`,
5. richer campaign cohorts define global portfolio-universe discovery governance,
6. Workbench active campaign-definition list, READY-gated launch, and launch-history views consume
   Gateway campaign-definition BFF routes only,
7. manage validates supportability without calculating underlying source facts locally,
8. richer workflow automation defines ownership, external orchestration boundaries, and
   downstream product evidence before any workflow claim is promoted beyond controlled
   Manage-side assignment tasks and append-only evidence ledgers.

Expected remaining implementation wave:

Treat richer campaign controls as separate RFCs or explicit slices. Campaign/bulk-review now has a
first promoted manage-owned membership envelope with optional approval, expiry, actor-entitlement
governance evidence, immutable persisted campaign definitions, bounded retirement/supersession
lifecycle controls, bounded lifecycle-event projection, bounded preview-readiness checks, bounded
launch-package request drafts, deterministic durable launch from ready definitions, first-class
append-only launch-history audit pages, bounded
persisted campaign discovery, a bounded workflow-overview read model, append-only campaign
approval-decision evidence, a bounded operating queue, a bounded approval-attention inbox, a
bounded read-only workflow board, a bounded read-only assignment/escalation plan, and Gateway BFF composition
for campaign-definition list/get/upsert plus Workbench active list rendering; future slices should
add global portfolio-universe discovery and broader workflow automation beyond controlled
Manage-side assignment tasks and append-only ledgers without moving
source-fact ownership into Manage, Gateway, or Workbench.

Promotion proof:

1. owning-service API certification for `RiskEventAffectedCohort:v1`,
2. manage trigger-specific source-client and wave API tests,
3. degraded, rejected, unavailable, invalid-selector, incomplete, and empty-cohort tests,
4. OpenAPI quality gate, no-alias guard, and API vocabulary inventory validation,
5. repo-native domain-data-product consumer declaration validation,
6. wiki and supported-feature language that names the supported trigger family precisely.

Gold-pass assessment for the 2026-05-10 risk-event consumer slice:

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | `lotus-manage` now supports `RISK_EVENT` wave preview/create by consuming `lotus-risk:RiskEventAffectedCohort:v1` over a supplied candidate portfolio set with source-supplied exposure weights. The wave preserves source-owned cohort/event/affected-portfolio refs and remains a normal RFC-0041 wave after resolution. |
| Quality improvements made | The implementation adds a typed risk-authority client method, explicit request fields and OpenAPI descriptions, fail-closed selector and dependency handling, stricter malformed-response rejection, and a machine-readable `lotus-risk` consumer declaration. |
| Debt removed | Previous RFC/wiki wording stopped at the source-owner foundation and left manage consumption as a future claim. This slice removes that drift while keeping global campaign discovery and broader campaign workflow surfaces explicitly unpromoted. |
| What was proven through testing and evidence | Focused API and client tests prove source-ready preview/create, source-ref preservation, outbound payload shape, invalid date, missing risk event id, missing candidates, empty/negative exposure weights, unavailable risk authority, rejected risk requests, degraded supportability, empty affected cohorts, and malformed source responses. Local gates passed for focused tests, mypy, ruff, OpenAPI quality, no-alias guard, API vocabulary inventory, and domain-data-product contract validation. |
| Expected-standard decision | The bounded `RISK_EVENT` manage-consumer slice reaches the expected backend standard on merged `lotus-manage` `main` truth with green GitHub checks and synchronized repo-local wiki publication. The bounded `TACTICAL_HOUSE_VIEW` manage-consumer slice reaches the expected backend standard when this branch is merged, CI-green, and wiki-published. The bounded `BULK_REVIEW_CAMPAIGN` membership slice is implementation-backed on `main`; the governance-evidence slice adds approval, expiry, and actor-entitlement controls; the approval-decision slice adds append-only campaign approval posture evidence without trade approval, order, or OMS claims; the controlled assignment-task lifecycle slice adds mutable Manage-side assignment/escalation task state without approval mutation, order, external workflow, client-contact, or OMS claims; the maker-checker control slice adds append-only actor-separation evidence without trade approval, order, client-contact, external workflow orchestration, or OMS claims. Gateway campaign-definition BFF composition is merged and wiki-published through `lotus-gateway` PR #212, and bounded lifecycle-events, launch-history, launch-package, durable launch, and campaign-discovery BFF preservation is mainline validated through PR #231. Workbench active campaign-definition list rendering is merged and wiki-published through `lotus-workbench` PR #184, and READY-gated launch plus paged launch-history boundary rendering is mainline validated through PR #244. RFC41-WTBD-003 remains partial for global portfolio-universe campaign discovery and broader workflow automation beyond controlled Manage-side assignment tasks. |

Gold-pass assessment for the 2026-05-12 bulk-review campaign membership slice:

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | `lotus-manage` now supports `BULK_REVIEW_CAMPAIGN` wave preview/create through manage-owned `BulkReviewCampaignMembership:v1` over source-backed candidate portfolios. |
| Quality improvements made | The implementation converts a previously blocked ownership decision into an explicit product boundary with deterministic membership source refs, content hash, DPM portfolio-type filtering, OpenAPI descriptions, and focused tests. |
| Debt removed | The old unsupported-trigger posture for campaign waves was replaced with a bounded first implementation that avoids duplicating source facts or claiming global campaign discovery. |
| What was proven through testing and evidence | Focused wave API tests prove successful preview/create, source-ref preservation, non-DPM portfolio exclusion, missing candidate validation, missing portfolio-type validation, missing source-ref validation, invalid date handling, empty eligible portfolio-type rejection, empty eligible membership failure, and OpenAPI documentation alignment. |
| Expected-standard decision | The slice reaches the backend standard for a first Manage-owned campaign membership envelope. The later governance-evidence slice adds optional approval, expiry, and actor-entitlement controls without claiming global portfolio discovery, broader campaign workflow surfaces, or OMS execution. |

Gold-pass assessment for the 2026-05-14 bulk-review campaign governance-evidence slice:

| Gold-pass question | Assessment |
| --- | --- |
| What was truly completed | `BULK_REVIEW_CAMPAIGN` preview/create now accepts optional governance evidence for approval reference, approver, approval time, expiry date, actor entitlement allow-list, access purpose, and source refs. |
| Quality improvements made | Campaign membership now fails closed for incomplete approval evidence, invalid or expired expiry dates, and unauthorized actors while preserving deterministic `BulkReviewCampaignGovernance` source refs and diagnostics. |
| Debt removed | The previous membership-only envelope could preserve source-backed candidates but could not carry bank governance evidence needed for controlled bulk-review use. |
| What was proven through testing and evidence | Focused wave API tests prove governance evidence preservation, source refs, diagnostics, incomplete approval rejection, invalid expiry rejection, expired campaign rejection, and actor-entitlement rejection. OpenAPI/API vocabulary gates must remain green before merge. |
| Expected-standard decision | This reaches the backend standard for bounded governance evidence on Manage-owned campaign membership. Tactical house-view is supported separately through the Advise source product, persisted campaign definitions are supported in Manage, Gateway campaign-definition BFF composition is supported through `lotus-gateway` PR #212 and PR #231, and Workbench active campaign-definition list, READY-gated launch, and launch-history boundary rendering is supported through `lotus-workbench` PR #184 and PR #244. Global campaign discovery, broader campaign workflow surfaces, and OMS execution remain outside the support claim. |

#### RFC41-WTBD-004 - Risk And Performance Aggregate Enrichment

Target business outcome:

Wave previews and simulations can show governed risk and performance impact using authoritative
analytics rather than manage-local estimates.

Completion result:

Implemented in this slice for manage backend wave aggregate authority. Wave simulation item input
can now carry source-backed `ConstructionAuthorityContext` evidence for `lotus-risk` and
`lotus-performance`; `RISK_AWARE` wave simulation can also use the existing configured
`DPM_RISK_BASE_URL` lotus-risk concentration authority path. `DpmWaveAggregateMetrics` now exposes
`source_analytics` entries for `RISK` and `PERFORMANCE` with supportability state, represented item
counts, source systems, source refs, bounded source-owner reason codes, and source-emitted scalar
values. Manage stores and aggregates those values for command-center lineage and display; it does
not recalculate risk or performance methodology.

Implemented controls:

1. `ConstructionAuthorityContext` now includes optional performance authority context alongside
   risk, liquidity, currency-overlay, and regime-stress context.
2. `AuthoritativeRiskContext` and `AuthoritativePerformanceContext` carry optional source product,
   source version, source id, and content hash fields so wave aggregates can expose lineage without
   raw upstream payloads.
3. Wave simulation accepts per-item authority context and passes it into RFC-0039 construction
   generation.
4. Wave item diagnostics store bounded `source_analytics` evidence derived from construction
   authority context and enrichment supportability.
5. Wave aggregate metrics reconcile source-owned analytics across items without summing or
   recomputing risk/performance values.
6. Wave item diagnostics also preserve bounded construction-derived `proposed_changes` rows with
   security id, action, quantity, estimated value, rationale, and constraints where available.
   These rows are PM-review evidence only and do not claim orders, executions, fills,
   venue-routing, or OMS instructions.
7. The RFC-0041 live-evidence script now requires both risk and performance source analytics in its
   aggregate reconciliation and critical-review checks.

Proof:

1. `tests/unit/dpm/api/test_waves_api.py` proves wave simulation aggregates source-owned risk and
   performance context, preserves a `READY` risk state and `DEGRADED` performance state, attaches
   source refs, carries source reason codes, exposes only source-emitted scalar values, and returns
   bounded `proposed_changes` diagnostics for PM review.
2. `tests/unit/test_rfc0041_evidence_script.py` proves the live-evidence critical review now fails
   if source-owned analytics are missing from aggregate reconciliation.
3. `scripts/generate_rfc0041_wave_evidence.py` now drives the live proof through `RISK_AWARE` and
   `MIN_TURNOVER` with source-backed risk/performance authority context and records analytics
   posture under `output/rfc0041-wave-proof/<timestamp>/`.
4. Targeted local proof for this slice:
   `python -m pytest tests/unit/test_rfc0041_evidence_script.py tests/unit/dpm/api/test_waves_api.py -q`
   passed with `45 passed`.
5. Broader targeted proof:
   `python -m pytest tests/unit/dpm/api/test_waves_api.py tests/unit/dpm/infrastructure/test_risk_authority_client.py tests/unit/dpm/construction/test_enrichment.py -q`
   passed with `74 passed`.
6. Live manage proof:
   `python scripts/generate_rfc0041_wave_evidence.py --base-url http://127.0.0.1:8001`
   passed against canonical manage runtime and wrote
   `output/rfc0041-wave-proof/20260507-224144/manifest.json`; aggregate reconciliation passed with
   `risk_source_state=READY`, `performance_source_state=DEGRADED`, and critical review
   `passed`.

Remaining downstream/product realization:

1. Gateway must compose `aggregate_metrics.source_analytics` into its wave command-center contract.
2. Workbench must render the risk/performance analytics posture and degraded states in the wave
   command center without flattening source supportability.
3. A future `lotus-performance` dedicated manage client may replace caller-supplied performance
   authority context when a wave-specific performance-impact product is promoted.

#### RFC41-WTBD-005 - Gateway Wave Composition

Target business outcome:

Workbench receives a stable command-center wave contract from Gateway, while manage remains the
wave authority.

Completion result:

Completed, merged, CI-proven, and wiki-published through `lotus-gateway` PR #196. The Gateway
merge commit is `c29d895f08b7316dd363d77559623eabfc3137e8`; the Gateway wiki publication commit is
`fc427a9`. Gateway now exposes implementation-backed `/api/v1/dpm/command-center/waves*` routes
for preview, durable create, search, detail, item list, source-check, simulation, item selection,
approval, staging, internal handoff, cancellation, proof-pack posture, and supportability.

Implemented controls:

1. Gateway RFC-0098 wave addendum was used as the execution guide.
2. Typed Gateway manage client methods cover preview, create, search, detail, items,
   source-check, simulate, select, approve, stage, handoff, cancel, proof-pack posture, and
   supportability routes.
3. Gateway preserves manage `wave_id`, lifecycle state, item states, reason codes, aggregate
   metrics, selected alternative refs, proof-pack refs, handoff refs, supportability issues, and
   `external_execution_claimed=false`.
4. Gateway does not calculate affected portfolios, classify source readiness, generate
   alternatives, select alternatives, approve items, stage items, create handoff evidence, rebuild
   proof packs, cancel external orders, or claim external execution.
5. Risk/performance/report/archive/AI posture remains composed only from owning services and is not
   claimed by this Gateway slice.

Promotion proof:

1. Local focused Gateway proof: `python -m pytest tests/unit/test_dpm_wave_service.py
   tests/integration/test_dpm_wave_router.py tests/contract/test_dpm_wave_contract.py
   tests/unit/test_upstream_clients.py tests/unit/test_rfc0098_documentation.py -q` passed with
   122 tests.
2. Local Gateway `make ci` passed with 168 integration tests, 640-test coverage gate at 88.07%,
   and `pip-audit` with no known vulnerabilities.
3. GitHub PR #196 checks passed: Feature Lane lint/typecheck/unit and workflow lint; PR Merge Gate
   lint/typecheck/unit, workflow lint, integration tests, coverage gate, Docker build, Docker
   parity, and queue auto-merge.
4. Gateway repo-local wiki source was published after merge and `Sync-RepoWikis.ps1 -CheckOnly
   -Repository lotus-gateway` reported diff count 0.

#### RFC41-WTBD-006 - Workbench Wave Command Center

Target business outcome:

Portfolio managers and operations users can review, simulate, approve, stage, hand off, and monitor
rebalance waves through a governed Workbench command-center experience.

Completion result:

Completed on 2026-05-07 and merged to `main` across the owning repositories. The implementation
keeps `lotus-manage` as the wave authority, `lotus-gateway` as the product API/BFF composition
layer, `lotus-platform` as the panel-registry and canonical-validation contract authority, and
`lotus-workbench` as the PM command-center surface.

What was delivered:

1. Manage PR #120 added source-owned wave `supportability` to preview/create/workflow responses
   and regenerated the API vocabulary inventory so downstream callers do not infer readiness.
2. Gateway PR #197 added preservation proof for Manage-provided wave supportability at the
   command-center preview boundary.
3. Platform PR #306 registered `dpm.wave_command_center` in the Workbench panel registry and
   analytics UI observability readiness contract.
4. Workbench PR #165 added the `Rebalance Wave Command Center` panel on `/workbench/{portfolioId}`
   with Gateway-backed list, preview, create, detail, items, source-check, simulate, approve, stage,
   handoff, proof-posture, and supportability actions.
5. Workbench live validation now pre-probes the Gateway wave endpoint, executes the preview action,
   records `dpm.wave_command_center`, and captures `dpm-wave-command-center-live.png` only after
   canonical validation passes.
6. Workbench wiki source now includes current feature coverage, integration posture, roadmap, and
   supported-features material for developers, operations, business users, sales/pre-sales, and
   client-demo preparation.

Promotion proof:

1. Governed canonical live proof passed through platform QA:
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-142715.json`.
2. DPM seed evidence was captured at
   `lotus-platform/output/front-office-qa/dpm-command-center-seed-20260507-143459.json`.
3. Screenshot evidence was captured at
   `lotus-workbench/output/playwright/live-canonical/dpm-wave-command-center-live.png`.
4. GitHub checks passed for Manage PR #120, Gateway PR #197, Platform PR #306, and Workbench PR
   #165, including feature lanes, PR merge gates, Docker build/parity checks, Workbench Playwright
   smoke, and Manage coverage/API-vocabulary gates.
5. Repo-local wiki source was published after merge for `lotus-manage` (`ed3569b`) and
   `lotus-workbench` (`212f486`). Gateway and Platform required no additional wiki publication for
   this closure slice.
6. Final closure keeps unsupported scope explicit: CIO cohort discovery is now implemented through
   source-owned `CioModelChangeAffectedCohort:v1`, bounded risk-event discovery now consumes
   `lotus-risk` `RiskEventAffectedCohort:v1`, and AI memo generation from wave evidence is owned
   by `lotus-ai`; downstream rendering of source-owned risk/performance analytics posture,
   tactical/campaign cohort discovery, and external OMS execution remain separate WTBDs.

#### RFC41-WTBD-007 - Full Front-Office Command-Center Product Support

Target business outcome:

The RFC-0041 wave capability is visible as an end-to-end front-office product workflow, not only as
manage backend APIs.

Completion result:

Completed for the first-wave wave command-center product path. Manage remains the wave authority,
Gateway composes manage wave truth, Workbench renders the PM command-center surface, and platform
canonical QA validates the populated path before screenshots are accepted as demo evidence.

Implemented scope:

1. RFC41-WTBD-005 Gateway wave composition is merged and wiki-published,
2. RFC41-WTBD-006 Workbench wave command center is merged, live-proven, and wiki-published,
3. canonical front-office QA passed with populated wave panel evidence,
4. supported-feature ledgers in participating apps are aligned,
5. wiki material is suitable for developers, operations, business users, sales/pre-sales, and demos.

Promotion proof:

1. canonical front-office evidence pack
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-142715.json`,
2. 2026-05-09 audit evidence pack
   `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260509-225912.json`,
3. API, BFF, and UI tests green in the owning PRs,
4. demo screenshot `lotus-workbench/output/playwright/live-canonical/dpm-wave-command-center-live.png`
   tied to validated backend evidence,
5. cross-repo supported-feature entries aligned.

Remaining boundary:

This completion does not promote global campaign discovery, broader campaign workflow surfaces, or
external OMS execution. Those remain separate source-owner, downstream-product, or
execution-product WTBDs.

#### RFC41-WTBD-008 - Report Materialization From Wave / Proof-Pack Evidence

Status: Completed on merged, validated, and wiki-published owning-repo truth.

Target business outcome:

Wave and proof-pack evidence can be materialized into governed reports and archived artifacts.

Implemented scope:

1. `lotus-manage` PR #124 added deterministic `DpmWaveReportInput` generation and
   `GET /api/v1/rebalance/waves/{wave_id}/report-input`, preserving wave identity, proof-pack
   lineage, supportability posture, selected-item evidence, hashes, actors, and handoff refs without
   generating rendered documents locally.
2. `lotus-report` PR #91 added `POST /reports/rebalance-waves`, wave snapshot lineage capture,
   report-job ledger persistence, and a render package that consumes manage wave report input rather
   than reconstructing wave state.
3. `lotus-render` PR #12 added the `rebalance-wave` v1 Typst template and manifest so generated
   wave reports use a governed template family with registry validation.
4. `lotus-archive` PR #24 added `rebalance_wave` as a governed generated-report type and validated
   archive lifecycle metadata, retention, hash, and retrieval behavior for wave reports.

Promotion proof:

1. `lotus-manage` PR #124 merged to `main` with Feature Lane and PR Merge Gate checks green; local
   `make check` passed with 931 tests passed, 13 skipped, and API vocabulary regenerated.
2. `lotus-report` PR #91 merged to `main` after coverage hardening; CI Feature Lane and PR Merge
   Gate checks passed, including coverage, Docker, unit, integration, and e2e gates.
3. `lotus-render` PR #12 merged to `main`; local `make check` passed with 82 tests and template
   registry validation, and CI passed.
4. `lotus-archive` PR #24 merged to `main`; local `make check` passed with lint, typecheck,
   OpenAPI, migration, and 74 tests, and CI passed.
5. Repo-local wiki source was published after merge for `lotus-manage`, `lotus-report`,
   `lotus-render`, and `lotus-archive`; post-publication wiki check-only drift is clean.

Remaining boundary:

This closure does not make `lotus-manage` a report renderer, archive authority, or document
retention service. It remains the source of wave evidence and deterministic report input. Gateway
and Workbench may surface report availability in a later product slice, but must consume the
owning report/archive posture rather than inferring availability in the browser or BFF.

#### RFC41-WTBD-009 - AI PM Memo Generation From Wave Evidence

Target business outcome:

PMs can request governed AI assistance over wave/proof-pack evidence without exposing forbidden
fields or allowing unsupported action recommendations.

Current implementation-backed state:

`lotus-ai` PR #63 implements the owner-side workflow pack `dpm_wave_pm_memo.pack@v1` on `main`
with CI proof and wiki publication. The pack validates Manage-owned `DpmWaveReportInput` payloads,
blocks forbidden fields, forbidden actions, autonomous requested outputs, raw payload exposure, and
external execution claims, preserves provenance and supportability posture, and returns a
review-required support-only memo payload. Manage remains evidence authority only and must not
create prompts, memos, recommendations, or AI-side workflow state locally.

`lotus-gateway` PR #201 and `lotus-workbench` PR #168 complete the product consumption path.
Gateway requests the AI workflow using Manage-owned wave report input and passes both
`blocked_actions` and `forbidden_actions` supportability controls to `lotus-ai`. Workbench exposes
the governed report-input and AI memo actions from the DPM wave command-center panel, records
observability for `dpm.waves.report-input` and `dpm.waves.ai-pm-memo`, and canonical live
validation proves the full path against the populated front-office runtime before screenshots are
accepted as demo evidence.

Implemented dependencies:

1. RFC-0043 or `lotus-ai` workflow-pack contract defines the memo workflow,
2. forbidden fields and forbidden actions are enforced,
3. provenance, model/prompt identity, input evidence hashes, and fallback states are captured,
4. Gateway/Workbench UI exposes AI posture without bypassing AI service controls,
5. AI unavailable and guardrail-blocked states are tested.

Closure posture:

This WTBD is complete for the first-wave governed product path. Manage remains wave evidence and
report-input authority; Gateway remains the BFF/product API composition layer; Workbench remains
the PM-facing product surface; and `lotus-ai` remains the only memo workflow owner. The closure does
not claim autonomous recommendations, external execution, direct browser-side prompt generation,
or future manage tactical/campaign cohort discovery.

Promotion proof:

1. `lotus-ai` PR #63 merge commit `3af5b8f8d6fee96cdc77b8c8c878b4ffdc4b01e3`,
2. `lotus-ai` wiki publication commit `6bed940`,
3. local `lotus-ai` `make check` proof and PR Merge Gate proof for PR #63,
4. AI guardrail and provenance tests,
5. prompt/input-output evidence with sensitive-field protections,
6. unavailable and blocked-state proof,
7. `lotus-gateway` PR #201 merge commit `6171df567010067edcb9fefc7acec92f68f5fde7`,
8. Gateway focused post-merge proof:
   `python -m pytest tests/unit/test_dpm_wave_service.py tests/integration/test_dpm_wave_router.py tests/contract/test_dpm_wave_contract.py -q`, 17 passed,
9. `lotus-workbench` PR #168 merge commit `ed0727a2f3571ec1dcbbab57fe79dc89b81086d9`,
10. `lotus-workbench` wiki publication commit `31ce0bd`,
11. Workbench focused post-merge proof:
    `npm test -- --run tests/unit/dpm-wave-command-center-view-model.test.ts tests/unit/live-canonical-validation-script.test.ts tests/unit/live-validation-browser-workflows.test.ts`, 16 passed,
12. Workbench RFC documentation proof:
    `python -m pytest tests/unit/test_rfc0098_documentation.py -q`, 1 passed,
13. Canonical live product proof:
    `npm run live:validate:ui`, passed with evidence under
    `lotus-workbench/output/playwright/live-canonical/` including the DPM wave command-center
    report-input and AI memo path,
14. supported-feature entries that do not imply autonomous execution authority.

#### RFC41-WTBD-010 - External Execution Integration

Target business outcome:

Approved and staged waves can hand off to a governed execution/OMS integration with auditability,
permissions, acknowledgements, and reconciliation.

Why it cannot be done now:

RFC-0041 intentionally ends at internal operations handoff evidence. No external execution owner or
OMS contract is established, and claiming execution would overstate manage's current business
capability.

2026-05-12 boundary-hardening result:

`lotus-manage` now fails closed if persisted wave handoff evidence ever contains an external
execution claim. `GET /api/v1/rebalance/waves/{wave_id}/proof-pack` can expose the contaminated
posture for operator diagnosis, but `GET /api/v1/rebalance/waves/{wave_id}/report-input` returns
`DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY` instead of propagating the claim into downstream report,
render, archive, or AI evidence paths. This does not implement OMS integration; it makes the
unsupported boundary machine-readable, API-documented, and regression-tested.

2026-05-18 boundary-evidence hardening result:

Wave proof-pack posture and `DpmWaveReportInput` now include structured
`DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY` evidence with a deterministic content hash, blocked
capabilities, required future execution/OMS owner, and required
`ExternalOrderExecutionAcknowledgement:v1` source product. Valid Manage-owned handoff evidence
continues to carry `external_execution_claimed=false`; contaminated handoff evidence remains
diagnosable through proof-pack posture but is still blocked from report-input propagation. This is
fail-closed evidence only, not execution integration.

Dependencies before implementation:

1. execution/OMS owner and contract,
2. order-generation, acknowledgement, rejection, cancellation, and reconciliation semantics,
3. maker-checker and entitlement controls,
4. failure/retry and compensation model,
5. post-trade feedback handoff into RFC-0042 scope where appropriate.

Expected implementation wave:

Do not start until the execution owner, control model, and post-trade feedback boundary are clear.
This may belong after RFC-0042 depending on whether outcome feedback requires execution status as a
source.

Promotion proof:

1. execution-owner API certification,
2. manage handoff integration tests,
3. failure and reconciliation proof,
4. operational runbook and supportability evidence,
5. explicit supported-feature promotion that names the execution boundary.

Boundary-hardening proof:

1. `python -m pytest tests/unit/dpm/api/test_waves_api.py -q`, 64 passed,
2. OpenAPI regression asserts the report-input `422` unsupported-boundary response and the
   proof-pack `external_execution_claimed` invariant wording plus structured boundary evidence,
3. report-input API regression proves an unsafe external-execution claim returns
   `DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY`.

### Suggested Sequencing

Recommended order:

1. implement Workbench wave command center,
2. prove full front-office command-center product support,
3. implement source-owned PM-book and CIO model-change cohort products,
4. promote manage automatic discovery triggers from certified source products,
5. add risk/performance aggregate enrichment from owning analytics services,
6. implement report materialization and AI memo generation in their owning apps,
7. evaluate external execution only after the execution owner and RFC-0042 post-trade feedback
   boundary are clear.

Rationale:

Gateway and Workbench can realize the already-supported explicit-list manage backend without
waiting for automatic cohort discovery. Source-owned discovery should then improve trigger quality
without blocking the product surface. Report, AI, and execution materialization should follow the
owning-service contracts because they introduce additional control, audit, and supportability
requirements.

### RFC-0041 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and API/source contract are explicit,
2. implementation is complete in the owning app,
3. `lotus-manage` consumes only certified source truth where it is not the owner,
4. Gateway and Workbench consume through the governed product path,
5. degraded, stale, missing, permission-denied, partial, and unavailable states are tested where
   applicable,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC, source-map, wiki, supported-features, and repository context are aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.
## RFC-0042 - Post-Trade Outcome Feedback Loop

Current closure status:

RFC-0042 is `DONE - MANAGE BACKEND COMPLETE; FIRST-WAVE PRODUCT REALIZATION COMPLETE; SOURCE-OWNER
ENRICHMENT REMAINS`. `lotus-manage` owns the implementation-backed outcome-review authority:
source-backed preview/create/retrieve/search, immutable persistence and append-only events,
source-refresh eventing, supportability diagnostics, deterministic report-input and AI-evidence
input handoff contracts, certified OpenAPI, and live manage proof under
`output/rfc0042-outcome-proof/20260505-024352/` plus hardening proof under
`output/rfc0042-outcome-proof/20260505-025613/`. Gateway, Workbench, report/render/archive, and
AI first-wave realization is now implemented and merged in the owning repositories. Remaining
ledger work is limited to source-owner methodology enrichment, external execution/OMS ownership,
and any future PM quality-scoring RFC.

Closure evidence:

| Evidence | Location |
| --- | --- |
| Governing RFC | `docs/rfcs/RFC-0042-post-trade-outcome-feedback-loop.md` |
| Source map | `docs/rfcs/RFC-0042-source-map-and-gap-analysis.md` |
| Slice evidence | `docs/rfcs/RFC-0042-*-slice*.md` |
| Certified API family | `wiki/Endpoint-Certification.md` post-trade outcome review API foundation |
| Supported feature claim | `wiki/Supported-Features.md` post-trade outcome feedback row |
| Live proof | `output/rfc0042-outcome-proof/20260505-024352/critical-review.json` |
| Hardening proof | `output/rfc0042-outcome-proof/20260505-025613/critical-review.json` |
| Post-merge audit rerun | `output/rfc0042-outcome-proof/20260505-040212/critical-review.json` |
| WTBD audit outcome proof | `output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/critical-review.json` |
| WTBD canonical Workbench proof | `lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/live-validation-summary.json` |

### RFC42 Gold-Pass Audit And RFC Reintegration - 2026-05-09

Gold-pass assessment:

1. Truly completed: RFC42-WTBD-001 through RFC42-WTBD-005 are completed for the bounded first-wave
   product path. Manage owns outcome-review authority; Gateway composes it; Workbench renders it;
   report/render/archive materialize governed outcome-review reports; and `lotus-ai` owns governed
   outcome-review narrative execution from bounded evidence input.
2. Quality improvements made: the owning RFC now carries the post-closure implementation truth,
   supported-feature boundaries, downstream owner boundaries, and evidence links instead of leaving
   those facts only in this WTBD ledger and wiki.
3. Debt removed: stale RFC wording that said Gateway/Workbench product proof remained unclaimed has
   been removed. The RFC now distinguishes implemented first-wave product support from unsupported
   OMS, PM-scoring, client-communication, and richer source-owner methodology work.
4. Testing and evidence proven: live manage proof, hardening proof, WTBD audit proof, canonical
   Workbench proof, and the 2026-05-09 canonical front-office QA pass are all linked from the RFC.
   Documentation regression now guards the RFC/WTBD/wiki alignment.
5. Standard reached: RFC-0042 reaches the expected standard for manage-owned backend authority and
   the bounded first-wave product path once this reintegration is merged to `main`, the repo-local
   wiki is published, and final branch hygiene confirms no stranded governance truth.

Audit refresh on 2026-05-05:

1. `lotus-manage` mainline truth was reconciled with `git fetch origin --prune` and
   `git branch -r --no-merged origin/main`; no unmerged remote branch carried RFC-0042 durable
   truth.
2. `lotus-gateway` commit `38d46f9` and `lotus-workbench` commit `3b5182f`, referenced by Slice
   10, are present on `origin/main` in their owning repositories; the realization RFC addenda are
   not stranded on side branches.
3. The RFC-0042 manage implementation evidence remains consistent with the support claim:
   backend authority is implemented and proven; downstream product, report, AI narrative,
   execution/OMS, PM scoring, and richer source-owner methodology work remains unpromoted.
4. RFC42-WTBD-002 and RFC42-WTBD-003 were completed after the audit through the downstream owning
   repositories: `lotus-workbench` PR #146, `lotus-gateway` PR #187, `lotus-platform` PR #300, and
   `lotus-core` PR #336 are merged, Workbench wiki publication completed, and canonical
   front-office evidence is captured under
   `lotus-workbench/output/playwright/live-canonical-rfc42-outcome-review/`.

WTBD audit refresh on 2026-05-06:

1. Rebuilt stale local `lotus-gateway`, `lotus-manage`, and `lotus-workbench` Docker images before
   accepting live evidence; stale images initially hid merged route/UI truth and caused false live
   failures.
2. Generated a durable live manage-backed outcome review with
   `python scripts/generate_rfc0042_outcome_evidence.py --base-url http://127.0.0.1:8001
   --output-root C:\Users\Sandeep\projects\lotus-manage\output\rfc0042-wtbd-audit-outcome-proof`.
   The accepted critical review is
   `output/rfc0042-wtbd-audit-outcome-proof/20260505-211611/critical-review.json` and it passed
   review creation, idempotency replay/conflict, source lineage, supportability, report input, AI
   guardrails, degraded-source posture, refresh eventing, OpenAPI certification, and variance
   worked-example checks.
3. Fixed the `lotus-workbench` outcome-review view model after screenshot review found manage-owned
   `source_system`, `source_id`, and `content_hash` lineage rendered as `N/A`. The corrected panel
   now shows `lotus-manage` and `lotus-core` source refs and hashes from the Gateway contract.
4. Fixed the manage RFC-0042 evidence generator so relative `--output-root` paths resolve under the
   repository root instead of failing before manifest publication.
5. Reran canonical front-office validation after the fixes. Accepted evidence is
   `lotus-workbench/output/playwright/rfc42-wtbd-audit-20260506-fixed/live-validation-summary.json`,
   `SHOT-INDEX.md`, and `dpm-outcome-review-live.png`; the DPM outcome-review panel is
   `demo_ready`, contains one manage-backed review, one dimension row, and two source-lineage rows.
6. Residual non-RFC42 findings remain bounded: the Workbench page still includes separate
   non-outcome sections showing unavailable reporting/analytics placeholders and existing build
   warnings for CSS autoprefixer/dependency audit posture. These are not outcome-review contract
   failures and should be handled by their owning Workbench/platform hygiene items rather than
   weakening RFC42-WTBD closure.

### Remaining Work Summary

These items are outside the RFC-0042 manage closure because outcome review backend authority is
necessary but not sufficient for the full front-office learning loop. Source calculations belong
to source-owning services, product composition belongs to Gateway and Workbench, generated
artifacts belong to report/render/archive services, and AI narrative execution belongs to
`lotus-ai`.

| ID | Work item | Owner | Current status | Why it was not done in RFC-0042 |
| --- | --- | --- | --- | --- |
| RFC42-WTBD-001 | Gateway outcome-review composition and BFF contract | `lotus-gateway` | Implemented, merged, CI-proven, and wiki-published through `lotus-gateway` PR #186; live canonical product proof remains part of RFC42-WTBD-003 | Manage APIs were stabilized first. Gateway now composes the BFF route family without recomputing outcome truth. Product support still requires Workbench implementation and canonical front-office proof. |
| RFC42-WTBD-002 | Workbench post-trade outcome review UX | `lotus-workbench` through Gateway/BFF | Implemented, merged, CI-proven, live-proven, and wiki-published through `lotus-workbench` PR #146 | Workbench now consumes Gateway/BFF outcome-review contracts only, presents manage-owned outcome truth without recomputation, and is proven by canonical Workbench validation. |
| RFC42-WTBD-003 | Full front-office post-trade outcome feedback product support | `lotus-gateway`, `lotus-workbench`, `lotus-manage` | Implemented and canonically proven for current Gateway/Workbench outcome-review product scope through `lotus-gateway` PR #186, `lotus-gateway` PR #187, `lotus-workbench` PR #146, `lotus-platform` PR #300, and `lotus-core` PR #336 | The full first-wave product path is now implementation-backed: manage owns authority, Gateway composes it, Workbench renders it, panel governance certifies it, and live canonical evidence proves it. Reporting, AI, OMS, source-owner methodology, and PM-scoring scope remain separate ledger items. |
| RFC42-WTBD-004 | Rendered outcome reports and archive lifecycle | `lotus-report`, `lotus-render`, `lotus-archive`, `lotus-gateway`, `lotus-workbench` | Implemented, merged, CI-proven, and wiki-published through `lotus-render` PR #9, `lotus-archive` PR #21, `lotus-report` PR #88, `lotus-gateway` PR #188, and `lotus-workbench` PR #147 | Manage emits bounded report input only; downstream services now consume it to create deterministic outcome-review report artifacts, preserve archive posture, expose Gateway submission, and add the Workbench report request action without recomputing outcome truth. |
| RFC42-WTBD-005 | Governed AI narrative/copilot over outcome evidence | `lotus-ai`, Gateway, Workbench, with manage as evidence authority | Implemented, merged, CI-proven, and wiki-published through `lotus-ai` PR #59/#60, `lotus-gateway` PR #189, and `lotus-workbench` PR #148 | Manage emits AI evidence input only; `lotus-ai` now owns guarded workflow-pack narrative execution, Gateway composes the evidence/narrative BFF, and Workbench exposes only a governed request action without prompt construction or autonomous decisioning. |
| RFC42-WTBD-006 | Source-owned realized risk/performance/tax/FX/cash/liquidity outcome methodologies | `lotus-risk`, `lotus-performance`, `lotus-core`, future source owners | In progress source-family by source-family | RiskMetricsReport, drawdown analytics maximum drawdown, average drawdown, ulcer index, and time under water, concentration response position HHI, top-position weight, top-N cumulative weight, issuer HHI, top issuer weight, and selected measures, rolling metric summaries, historical attribution selected measures, performance RFC-046 TWR daily evidence/supportability/benchmark posture, workspace-summary TWR, active return, stateful MWR, contribution selected measures, attribution selected measures, source-owned portfolio-level `currency_attribution_totals`, core HoldingsAsOf cash totals, core TransactionLedgerWindow explicit transaction-row measures and field-aware book/trade reporting-currency restatement, core PortfolioCashflowProjection total/booked/projected-settlement cashflow, core PortfolioLiquidityLadder operational bucket measures, core `ClientTaxProfile:v1` / `ClientTaxRuleSet:v1` profile/rule evidence, core `ClientIncomeNeedsSchedule:v1` / `LiquidityReserveRequirement:v1` / optional `PlannedWithdrawalSchedule:v1` bounded reference evidence, core `PortfolioRealizedTaxSummary:v1` portfolio-level explicit realized tax evidence, and core `PortfolioCashMovementSummary:v1` signed cash movement bucket evidence now have source-owned implementation truth. Broader FX methodology beyond performance-owned Karnosky-Singer attribution totals, predictive execution, and OMS acknowledgements stay source-owner follow-on work; tax advice, tax-loss harvesting suitability, after-tax optimization, jurisdiction-specific recommendation, client-tax approval, tax-reporting certification, income-needs planning, cashflow forecasting, funding recommendation, treasury instruction, and OMS acknowledgement remain unsupported. |
| RFC42-WTBD-007 | External execution/OMS integration and acknowledgements | Execution/OMS owner, `lotus-core` source-boundary posture, `lotus-manage` consumer | Lotus-side fail-closed source contract and Manage consumer implemented; bank-owned OMS ingestion not established | `lotus-core` `ExternalOrderExecutionAcknowledgement:v1` now exposes a fail-closed `UNAVAILABLE` source-product posture and Manage preserves it as construction authority diagnostics and RFC-0042 realized outcome execution-quality evidence with acknowledgement counts, empty acknowledgement rows, missing data families, blocked capabilities, lineage, and source hashes. Outcome-review supportability, report input, and AI evidence input now expose structured `DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY` evidence with blocked capabilities, required future execution/OMS owner, required `ExternalOrderExecutionAcknowledgement:v1` source product, execution-quality dimension posture, acknowledgement-count posture, and deterministic content hash. RFC-0042 can compare expected and realized non-execution evidence while marking execution-quality evidence blocked, but production OMS integration still needs a bank-owned execution/OMS owner, ingestion controls, acknowledgements, fills, settlement, and reconciliation contract before support can be promoted. |
| RFC42-WTBD-008 | PM operating quality framework / configurable scoring | `lotus-manage` with source evidence from `lotus-core`, `lotus-risk`, and `lotus-performance`; Gateway composition; `lotus-ai` narrative only; Workbench through Gateway only | Completed for the bounded Manage backend and first-wave product support claim: policy administration, score-run preview, immutable create/read/list score-run lifecycle, optional source-owned PM-book materialization, bank approval evidence, fairness-review evidence, expiry controls, actor entitlement checks, bank-defined peer-group/lookback-window scope materialization, bounded source-segment fairness-analysis preview/create/read/list, bounded immutable review-action preview/create/read/list, bounded portfolio-memory score-run and review-action lineage projection, Gateway policy/score-run/fairness-analysis/support-summary BFF composition, AI-owned support-only PM quality summary, and Gateway-only Workbench policy/score-run/fairness-analysis/support-summary UI are implemented, merged, validated, and wiki-published where changed. Gateway/Workbench review-action BFF and UI realization remains downstream work and is not claimed here. | `lotus-manage` now owns configurable, evidence-first, default-disabled PM operating quality policies at `PUT /api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}`, `GET /api/v1/rebalance/pm-operating-quality/policies`, and `GET /api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}`; score-run preview at `POST /api/v1/rebalance/pm-operating-quality/score-runs/preview`; persisted score-run lifecycle at `POST /api/v1/rebalance/pm-operating-quality/score-runs`, `GET /api/v1/rebalance/pm-operating-quality/score-runs`, and `GET /api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}`; source-segment fairness-analysis preview/create/list/get at `/api/v1/rebalance/pm-operating-quality/fairness-analyses*`; review-action preview/create/list/get at `/api/v1/rebalance/pm-operating-quality/review-actions*`; portfolio-memory `PM_QUALITY_SCORE_RUN` lineage events for persisted score runs whose source-owned Core PM-book membership evidence includes the requested portfolio; and portfolio-memory `PM_QUALITY_REVIEW_ACTION` supervisory events for review actions over those score runs without raw rationale, score values, PM ranking, client-contact, trade, order, OMS, or execution claims. `lotus-gateway` PR #213 (`62ce4c4`, wiki `a4c9db9`) exposes bounded policy, score-run, fairness-analysis, and score-run AI-summary handoff routes, preserving Manage policy, score-run, fairness-analysis, and summary truth without calculating scores, ranking PMs, administering policy locally, or creating HR, compensation, conduct, approval, client-contact, execution, or OMS decisions; it does not yet expose the Manage review-action route family. `lotus-workbench` PR #245 (`2af063b`, wiki `2ba368d`, Main Releasability Gate `25991445845`) completes the Gateway-only PM operating quality product surface for policy and score-run evidence, fairness-analysis preview/create/list/detail, persisted-analysis readback, supportability/reason/source-ref/forbidden-use rendering, and review-gated PM-quality support-summary invocation without browser-side score, segment-average, fairness-spread, protected-class, ranking, HR, conduct, client-contact, trade, order, OMS, or execution logic; it does not yet render a PM-quality review-action ledger/detail/preview/create UX. `lotus-ai` PR #70 (`1951f62`, wiki `038a1a1`) adds `pm_quality_summary.pack@v1` for review-gated support-only summaries over Manage-owned `PmOperatingQualityScoreRun` evidence; it validates score-run identity, source refs, supportability posture, optional bounded portfolio-memory context, and forbidden-use controls without calculating scores, ranking PMs, generating HR/compensation/conduct decisions, contacting clients, approving trades, routing orders, claiming execution, or inventing missing facts. Optional `pm_book_scope` resolves lotus-core `PortfolioManagerBookMembership:v1`, records explicit `book_scope_evidence`, and fails closed for unavailable, incomplete, degraded, or empty membership. Enabled policies require bank-defined dimensions, weights, thresholds, peer groups, governance approval, fairness-review evidence, source refs, and non-use posture; `peer_group_policy` and `lookback_window_policy` materialize into score-run `scope_evidence`, preserve peer-group/lookback source refs in the content hash, and fail closed for dated evidence outside the approved lookback window without Manage discovering peers, ranking PMs, or owning source methodology. Missing evidence, expired governance, unauthorized actors, and prohibited HR, compensation, conduct-enforcement, autonomous-ranking, and AI-generated scoring use are rejected. Fairness analysis consumes persisted score-run ids and source-defined operating segments, validates common policy/as-of scope, minimum scorable segment counts, and governed average-score spread, and does not infer protected classes or create PM rankings. Persisted summary history, Gateway/Workbench review-action realization, approval workflow beyond immutable review actions, and external OMS/execution remain future product depth rather than part of this support claim. |

### Detailed Follow-Up Items

2026-05-16 fairness-analysis lifecycle addendum:

`lotus-manage` now persists immutable `PmOperatingQualityFairnessAnalysis:v1` evidence at
`POST /api/v1/rebalance/pm-operating-quality/fairness-analyses`, lists bounded pages at
`GET /api/v1/rebalance/pm-operating-quality/fairness-analyses`, and retrieves one analysis at
`GET /api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}`. The create
route uses the same source-segment contract as preview, persists content-addressed evidence, and
stored reads do not recompute score runs, infer protected classes, rank PMs, or create HR,
compensation, conduct, approval, client-contact, execution, or OMS decisions.

2026-05-20 PM-quality review-action ledger addendum:

`lotus-manage` now emits and persists immutable `PmOperatingQualityReviewAction:v1` evidence at
`POST /api/v1/rebalance/pm-operating-quality/review-actions/preview`,
`POST /api/v1/rebalance/pm-operating-quality/review-actions`, lists bounded pages at
`GET /api/v1/rebalance/pm-operating-quality/review-actions`, and retrieves one ledger row at
`GET /api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}`. The implementation
uses `src/core/pm_quality/review_actions.py` plus the
`0013_pm_quality_review_actions.sql` migration to preserve the reviewed score-run or
fairness-analysis content hash, bounded bank review reference, rationale, actor, reason codes, and
source refs. Stored reads do not recalculate scores, recompute fairness, rank PMs, create HR,
compensation, conduct, client-contact, trade, order, OMS, or execution decisions, or claim a broader
approval workflow beyond immutable review evidence.

2026-05-20 PM-quality portfolio-memory review-action projection addendum:

Portfolio memory now projects bounded `PM_QUALITY_REVIEW_ACTION` events for immutable PM operating
quality review actions whose reviewed score-run has source-owned Core PM-book membership evidence
for the requested portfolio. The projection preserves review-action identity, target identity,
target content hash, policy/as-of scope, action state, source refs, content hash, and operating
boundaries while deliberately omitting raw review rationale and score values. It does not
recalculate scores, recompute fairness, rank PMs, create HR/compensation/conduct outcomes, contact
clients, approve trades, generate orders, route execution, claim OMS acknowledgement, or discover
the global portfolio universe.

#### RFC42-WTBD-001 - Gateway Outcome-Review Composition And BFF Contract

Target business outcome:

Gateway exposes a product-facing outcome-review contract for command-center and portfolio workspace
consumers while preserving manage-owned source lineage, state, reason codes, supportability,
report-input refs, and AI-evidence refs.

Current implementation-backed result:

`lotus-gateway` branch `feat/rfc42-outcome-review-gateway` implements the first RFC-0042
realization slice. Gateway now has typed manage client methods, DPM command-center outcome-review
BFF contracts, a service layer, and route handlers for preview, create, search, detail,
source-refresh, supportability, report-input, AI-evidence input, run lookup, and wave lookup.
Gateway preserves manage-owned payloads and supportability and does not recompute expected values,
realized values, variance, tolerance, hashes, lineage, freshness, or review state. Gateway PR #186
merged to `main` as `a71275d` after local `make ci` and GitHub PR Merge Gate passed. Gateway wiki
publication completed with zero drift. End-to-end product proof remains under RFC42-WTBD-003
because it requires Workbench UX implementation and canonical front-office validation.

Why it was not done in RFC-0042:

RFC-0042 intentionally stabilized the manage API surface first. Gateway composition had to consume
the certified surface after manage closure and remain in the Gateway owning repository.

Dependencies before implementation:

1. typed Gateway manage client for all RFC-0042 outcome-review endpoints,
2. Gateway route design aligned with RFC-0098,
3. no direct Workbench-to-manage calls,
4. no recomputation of outcome dimensions in Gateway,
5. unavailable/degraded source posture preserved for UI consumers.

Expected implementation wave:

This item is complete enough to unblock Workbench outcome-review UX work. The next implementation
wave is RFC42-WTBD-002 in `lotus-workbench`, followed by RFC42-WTBD-003 for full canonical
front-office product proof.

Promotion proof:

1. Gateway unit and contract tests: focused tests added in
   `tests/unit/test_dpm_command_center_service.py`,
   `tests/unit/test_upstream_clients.py`,
   `tests/integration/test_dpm_command_center_router.py`, and
   `tests/contract/test_dpm_command_center_contract.py`,
2. Gateway OpenAPI/Swagger certification: route family registered with What/When/How descriptions
   and response schema descriptions; local `make check` and `make ci` passed,
3. live canonical front-office proof remains required before full product-support promotion under
   RFC42-WTBD-003,
4. degraded, blocked, unsupported, unavailable, and upstream-error coverage has been added at the
   Gateway service/router layer; live degraded proof remains required,
5. Gateway README/wiki/context updates are merged and wiki source was published.

#### RFC42-WTBD-002 - Workbench Post-Trade Outcome Review UX

Target business outcome:

PMs, CIO, compliance, and operations can review expected-versus-realized outcomes in Workbench with
clear state, variance, source lineage, supportability, report/AI handoff posture, and next-action
guidance.

Current implementation-backed result:

`lotus-workbench` PR #146 implements the RFC-0042 post-trade outcome-review UX on
`/workbench/{portfolioId}`. The panel consumes Gateway/BFF contracts only through the shared
Workbench API layer, normalizes manage-owned outcome-review payloads in a deterministic view-model,
and renders review state, expected-versus-realized dimensions, variance/tolerance posture, source
lineage, hashes, supportability, report-input refs, AI-evidence refs, and next-action posture
without client-side outcome calculation. Server-side Workbench Gateway reads now share governed
caller-context propagation with the BFF route. The canonical live validator certifies
`dpm.outcome_review` as a governed panel and captures machine-readable API/panel proof plus the
`dpm-outcome-review-live.png` screenshot.

Cross-repo hardening completed during live proof:

1. `lotus-gateway` PR #187 fixed platform-capabilities live fanout and the manage capability
   contract route so Workbench no longer sees false platform degradation.
2. `lotus-platform` PR #300 registered `dpm.outcome_review` in the governed Workbench panel
   registry and analytics UI observability readiness contracts.
3. `lotus-core` PR #336 passed governed caller-context headers during canonical front-office seed
   validation and added unit coverage for that contract.

Why it was not done in RFC-0042:

Workbench had to wait until manage and Gateway contracts stabilized. Implementing earlier would
have forced direct manage calls, duplicated outcome logic, or speculative UI behavior.

Dependencies before implementation:

1. RFC42-WTBD-001 complete,
2. Workbench must consume Gateway/BFF only,
3. Workbench BFF/client modules consume Gateway only,
4. outcome-review list and detail information architecture,
5. UI states for ready, degraded, blocked, unsupported, stale, malformed, conflicting, and empty,
6. canonical browser validation with populated and degraded evidence cases.

Expected implementation wave:

Complete. This item merged through `lotus-workbench` PR #146 after Gateway, platform governance,
and core caller-context dependencies were raised, fixed, green, and merged.

Promotion proof:

1. Workbench unit/component/BFF/browser tests:
   `tests/unit/outcome-review-view-model.test.ts`, `tests/unit/outcome-review-panel.test.tsx`,
   `tests/unit/workbench-api.test.ts`, `tests/unit/live-validation-probes.test.ts`,
   `tests/unit/live-validation-browser-workflows.test.ts`, and
   `tests/integration/workbench-page.test.tsx`,
2. local gates: `npm run typecheck`, `npm run lint`, `npm run build`, `make check`, and
   `git diff --check`,
3. GitHub checks: `lotus-workbench` PR #146 Feature Lane and PR Merge Gate green,
4. canonical proof:
   `lotus-workbench/output/playwright/live-canonical-rfc42-outcome-review/live-validation-summary.json`
   shows `DPM outcome reviews` API status 200 and `dpm.outcome_review` panel state `ready`,
5. screenshot index:
   `lotus-workbench/output/playwright/live-canonical-rfc42-outcome-review/SHOT-INDEX.md` lists
   `dpm-outcome-review-live.png` as `demo_ready`,
6. Workbench README/wiki/context updates merged, and Workbench wiki source was published with
   commit `650f698` to `lotus-workbench.wiki`.

#### RFC42-WTBD-003 - Full Front-Office Post-Trade Outcome Feedback Product Support

Target business outcome:

The RFC-0042 capability becomes an end-to-end product workflow: manage creates durable outcome
reviews, Gateway composes them, Workbench presents them, and documentation supports business,
operations, sales/pre-sales, client demos, and engineering.

Current implementation-backed result:

The first-wave front-office product path is complete for RFC-0042 outcome review. Manage remains
the backend authority, Gateway composes the outcome-review contract, Workbench presents the
post-trade outcome-review panel through Gateway/BFF only, platform governance registers the panel,
and canonical Workbench validation proves the populated panel on `PB_SG_GLOBAL_BAL_001` with
machine-readable API, panel, and screenshot evidence.

Why it was not done in RFC-0042:

The original RFC-0042 closure was intentionally limited to manage backend authority. Gateway,
Workbench, platform panel governance, and core seed-validation hardening had to be implemented in
their owning repositories after manage contracts and live proof stabilized.

Dependencies before implementation:

1. RFC42-WTBD-001 complete,
2. RFC42-WTBD-002 complete,
3. canonical front-office QA passes with populated outcome-review panels,
4. supported-feature ledgers align across participating apps,
5. unresolved downstream issues are closed or explicitly bounded.

Expected implementation wave:

Complete for current Gateway/Workbench product realization. Remaining OMS, source-owner
methodology, persisted PM-quality summary history, approval workflow beyond immutable review actions, and any future
employment-decision or execution-related PM-quality depth stay in explicitly bounded follow-on
RFCs rather than the current support claim.

Promotion proof:

1. manage backend authority: RFC-0042 proof under
   `lotus-manage/output/rfc0042-outcome-proof/20260505-024352/`,
   `20260505-025613/`, and post-merge audit `20260505-040212/`,
2. Gateway composition: `lotus-gateway` PR #186 merged as `a71275d`; Gateway wiki publication was
   completed with zero drift,
3. Gateway live-proof hardening: `lotus-gateway` PR #187 merged and all GitHub Feature Lane /
   PR Merge Gate checks passed,
4. platform panel governance: `lotus-platform` PR #300 merged and all platform contract/vocabulary
   checks passed,
5. core caller-context validation: `lotus-core` PR #336 merged after local targeted proof,
   `make warning-gate`, and full GitHub Feature Lane / PR Merge Gate including Docker, E2E,
   latency, fast load, and coverage gates,
6. Workbench UX: `lotus-workbench` PR #146 merged after Feature Lane and PR Merge Gate passed,
7. canonical evidence:
   `lotus-workbench/output/playwright/live-canonical-rfc42-outcome-review/live-validation-summary.json`,
   `SHOT-INDEX.md`, and `dpm-outcome-review-live.png`,
8. Workbench wiki was published from repo source after merge.

#### RFC42-WTBD-004 - Rendered Outcome Reports And Archive Lifecycle

Target business outcome:

Outcome reviews can be turned into governed report artifacts with deterministic rendering,
retention, archive retrieval, legal hold posture, and access audit.

Current implementation-backed result:

Complete for the first-wave generated outcome-review report artifact path. `lotus-report` now
accepts manage-owned `DpmOutcomeReportInput` through `POST /reports/outcome-reviews`, persists the
handoff as the immutable report snapshot, records lineage back to `lotus-manage`, builds the
`dpm_outcome_report_input.v1` render package, submits the `outcome-review` template to
`lotus-render` when PDF is requested, and hands rendered artifacts to the existing
`lotus-archive` generated-document lifecycle. `lotus-render` now owns the deterministic
`outcome-review/v1` Typst template and registry manifest. `lotus-archive` documentation confirms
that outcome-review generated documents inherit the existing archive, retrieval, retention,
legal-hold, access-audit, purge, and lifecycle posture when supplied by `lotus-report`.

Gateway and Workbench realization is complete for report-request submission: `lotus-gateway`
exposes `POST /api/v1/reports/outcome-reviews` as a pass-through Experience API route to
`lotus-report`, preserving caller context and idempotency without recomputing outcome truth.
`lotus-workbench` adds a governed outcome-review report request action in the DPM outcome panel,
calling Gateway/BFF only and recording the `dpm.outcome-review.report-job.submit` observability
surface.

Why it was not done in the original RFC-0042 manage closure:

`lotus-manage` correctly emits bounded `DpmOutcomeReportInput`; report generation, rendering,
archive persistence, retrieval, and retention lifecycle are owned by downstream reporting services.
The work had to land in the owning repositories after manage report-input contracts stabilized.

Dependencies before implementation:

1. `lotus-report` contract for consuming outcome-review report input - complete in PR #88,
2. `lotus-render` deterministic rendering contract - complete in PR #9,
3. `lotus-archive` retention, legal hold, access-audit, and retrieval posture - documented and
   merged in PR #21,
4. Gateway/Workbench posture for report availability and submission - complete in Gateway PR #188
   and Workbench PR #147,
5. reconciliation from generated artifact back to manage evidence hashes - complete through
   `lotus-report` snapshot lineage, render package hashes, and archive metadata handoff.

Expected implementation wave:

Complete for first-wave outcome-review generated reports. A future enhancement may add direct
Workbench retrieval/download affordances once the broader generated-document discovery UX is
standardized, but report request, render, archive handoff, and lifecycle posture are now
implementation-backed and must not remain listed as deferred.

Promotion proof:

1. `lotus-render` PR #9 merged after Feature Lane and PR Merge Gate passed, including lint,
   unit/integration/e2e tests, coverage, Docker build validation, and template-registry gate;
   wiki published from repo source as `lotus-render.wiki` commit `e09f36e`,
2. `lotus-archive` PR #21 merged after Feature Lane and PR Merge Gate passed, including lint,
   unit/integration/e2e tests, coverage, Docker build validation, and documentation posture tests;
   wiki published from repo source as `lotus-archive.wiki` commit `47b59e0`,
3. `lotus-report` PR #88 merged after Feature Lane and PR Merge Gate passed, including lint,
   unit/integration/e2e tests, 99 percent coverage gate, Docker build validation, OpenAPI wording
   guardrails, immutable snapshot capture, report render package tests, idempotency guardrails,
   degraded validation coverage, and supported-features/wiki updates; wiki published from repo
   source as `lotus-report.wiki` commit `aa6d487`,
4. `lotus-gateway` PR #188 merged after Feature Lane and PR Merge Gate passed, including lint,
   typecheck, unit/contract/integration tests, coverage, Docker parity, Docker build validation,
   caller-context/idempotency forwarding tests, OpenAPI route registration, README, and wiki
   updates; wiki published from repo source as `lotus-gateway.wiki` commit `483f627`,
5. `lotus-workbench` PR #147 merged after Feature Lane and PR Merge Gate passed, including lint,
   typecheck, focused unit/component tests, coverage/build, Docker parity, Playwright smoke,
   Docker build validation, BFF/API tests, component action tests, observability registry tests,
   and wiki updates; wiki published from repo source as `lotus-workbench.wiki` commit `6db1daa`.

#### RFC42-WTBD-005 - Governed AI Narrative/Copilot Over Outcome Evidence

Target business outcome:

PMs and CIO users can request governed AI support over outcome-review evidence without inventing
missing facts, scoring PMs, contacting clients, approving trades, or bypassing controls.

Current implementation-backed result:

Complete for first-wave governed outcome-review narrative support. `lotus-ai` now owns
`outcome_review_narrative.pack@v1`, including supported caller governance, narrative guardrails,
stub-provider execution, workflow-pack registry exposure, queue policy, and supportability
metadata. `lotus-gateway` composes the product route
`POST /api/v1/dpm/command-center/outcome-reviews/{outcome_review_id}/ai-narrative` by fetching
manage-owned `DpmOutcomeAiEvidenceInput`, forwarding a bounded request to `lotus-ai`, preserving
manage as evidence/workflow authority, and returning explicit manage/AI upstream posture.
`lotus-workbench` exposes the governed action on the RFC-0042 outcome-review panel through the
Gateway BFF only, records bounded observability for `dpm.outcome-review.ai-narrative`, and displays
workflow-pack run posture without constructing prompts, scoring PMs, approving trades, or calling
raw manage/AI services.

Why it was not done in the original RFC-0042 manage closure:

`lotus-manage` correctly emitted bounded AI evidence input but was not the AI workflow owner.
Prompt execution, model posture, guardrails, narrative execution, and unavailable/blocked AI states
belong in `lotus-ai`; product composition belongs in Gateway; user realization belongs in
Workbench. The item could only close after all three owning repositories implemented and proved
their contracts.

Dependencies satisfied:

1. `lotus-ai` workflow-pack contract and registry entry for `outcome_review_narrative.pack@v1`,
2. guardrails that block forbidden actions, forbidden fields, unsupported/degraded evidence,
   empty review evidence, and missing required evidence hashes,
3. caller governance for both `lotus-manage` and `lotus-gateway`,
4. Gateway route and service composition that calls manage and AI through typed owning-service
   contracts without recomputing outcome truth,
5. Workbench BFF/API/component realization through Gateway only, with bounded metric labels that
   exclude outcome review ids, workflow-pack run ids, request bodies, response bodies, hashes, and
   lineage references.

Expected implementation wave:

Complete for first-wave governed AI narrative support over RFC-0042 outcome evidence. Future
enhancements, such as non-stub model providers, richer narrative templates, or additional PM/CIO
workflow outputs, must remain in `lotus-ai` and preserve the same evidence, guardrail, provenance,
Gateway-only, and Workbench-no-autonomy boundaries.

Promotion proof:

1. `lotus-ai` PR #59 merged as `6e547866e0e7254a4d03bc8cf94101d70eaef221` after Feature Lane and
   PR Merge Gate passed; post-merge validation
   `python -m pytest tests/unit/test_outcome_review_narrative_guardrails.py tests/unit/test_workflow_pack_execution.py tests/integration/test_workflow_pack_run_api_contract.py -q`
   passed `49` tests; wiki published from repo source as `lotus-ai.wiki` commit `89b873b`,
2. `lotus-ai` PR #60 merged as `d1df451` after Feature Lane and PR Merge Gate passed, adding
   `lotus-gateway` as an explicit supported caller and proving Gateway caller execution through
   targeted integration/registry tests,
3. `lotus-gateway` PR #189 merged as `9d1d04794ea7ee0a733a76e671fd927a3a2d862c` after Feature
   Lane and PR Merge Gate passed, including service/router/contract tests, OpenAPI route
   registration, local `make ci`, and post-merge targeted validation
   `python -m pytest tests/unit/test_dpm_command_center_service.py tests/integration/test_dpm_command_center_router.py tests/contract/test_dpm_command_center_contract.py -q`
   with `17` passing tests; wiki published from repo source as `lotus-gateway.wiki` commit
   `e4dbdd0`,
4. `lotus-workbench` PR #148 merged as `46fe13ad3dd43f3a3150f6c2966c59e88a8a3e95` after Feature
   Lane and PR Merge Gate passed, including lint, typecheck, coverage/build, Playwright smoke,
   Docker build, Docker parity, focused API/component/observability tests, and local
   `make test-coverage` with `695` passing tests and `91.06%` statement coverage; post-merge
   targeted validation
   `npm test -- --run tests/unit/outcome-review-panel.test.tsx tests/unit/workbench-api.test.ts tests/unit/analytics-observability-metrics.test.ts`
   passed `58` tests,
5. `lotus-workbench` wiki was published from repo source as `lotus-workbench.wiki` commit
   `e223851` and `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-workbench` returned clean
   synchronization.

#### RFC42-WTBD-006 - Source-Owned Realized Outcome Methodologies

Target business outcome:

Outcome reviews can compare richer realized evidence across risk, performance, tax, FX, cash,
liquidity, and execution dimensions using source-owner methodologies and certified contracts.

Implementation-backed progress:

1. `src/core/outcomes/performance_sources.py` adds WTBD-006 source-family adapters for
   `lotus-performance` workspace-summary TWR return, active return, MWR return, contribution
   selected-measure evidence, and attribution reconciliation/level/currency selected-measure
   evidence,
2. `src/core/outcomes/risk_sources.py` adds WTBD-006 source-family adapters for
   `lotus-risk` `RiskMetricsReport:v1`, drawdown response evidence, concentration response
   selected-measure evidence, rolling metrics selected metric/statistic/window evidence, and
   historical attribution selected set/contributor evidence,
3. `src/core/outcomes/core_sources.py` adds WTBD-006 `lotus-core` source-family adapters for
   `HoldingsAsOf:v1` cash-total evidence, `TransactionLedgerWindow:v1` explicit transaction-row
   scalar evidence, and `PortfolioCashflowProjection:v1` total, booked, and projected-settlement
   cashflow evidence,
4. the performance adapters consume source-owned `WORKSPACE_SUMMARY_TWR_RETURN`,
   `WORKSPACE_SUMMARY_ACTIVE_RETURN`, `WORKSPACE_SUMMARY_MWR_RETURN`, and
   `PERFORMANCE_CONTRIBUTION`, and `PERFORMANCE_ATTRIBUTION` output and convert percentage-point
   source units to RFC-0042 ratio units without calculating performance, contribution, or
   attribution locally,
5. the risk adapters consume source-owned `RISK_METRICS_REPORT`, `DRAWDOWN_RESPONSE`,
   `CONCENTRATION_RESPONSE`, `ROLLING_RISK_METRICS_REPORT`, and
   `HISTORICAL_RISK_ATTRIBUTION` output and preserve selected source metric, absolute
   max-drawdown, benchmark-relative max-drawdown, HHI, single-position concentration, issuer
   concentration, issuer-coverage, rolling metric, rolling statistic, rolling window, attribution
   type, attribution metric, grouping dimension, set-level measure, and explicit contributor values
   without calculating risk locally,
6. the core adapters consume source-owned `HOLDINGS_AS_OF_CASH_BALANCE` totals,
   `TRANSACTION_LEDGER_WINDOW` explicit transaction-row trade-fee, withholding-tax, realized-FX-P&L,
   linked-cashflow measures, and `PORTFOLIO_CASHFLOW_PROJECTION` total net cashflow without
   aggregating cash accounts, aggregating transaction rows, projecting/forecasting cashflows,
   deriving tax, calculating FX, inferring execution quality, or converting currency locally,
7. performance source lineage is preserved through calculation id, calculation hash, selected
   period, selected basis or MWR method where applicable, selected return, contribution, or
   attribution measure, attribution model, linking method, benchmark context where available,
   source supportability where applicable, source owner, source type, and reason codes,
8. risk source lineage is preserved through request fingerprint, selected period where applicable,
   selected risk metric, drawdown measure, concentration measure, rolling metric, rolling
   statistic, rolling window length, attribution type, attribution metric, grouping dimension,
   attribution measure, contributor group key where applicable, source supportability state,
   source supportability reason, issuer coverage posture where applicable, benchmark/risk-free
   context where applicable, attribution quality flags and stateful active-risk support metadata,
   latest observation date, period end date, as-of date, source owner, source type, and reason codes,
9. core source lineage is preserved through product identity, portfolio id, as-of date,
   generated/evidence timestamp, data-quality posture, source fingerprint, source owner, source type,
   transaction id/type, selected transaction measure where applicable, selected source field,
   projection range/include-projected posture where applicable, source units, and reason codes,
10. focused tests prove ready, missing, degraded/unavailable, permission-blocked, explicit metric,
   source supportability, source-owned active return, source-owned MWR return, source-owned
   absolute and relative max drawdown, relative-drawdown unavailable posture, rolling metric
   summaries, benchmark/risk-free rolling degraded posture, historical attribution set and
   contributor measures, historical attribution quality-flag and period-error posture, contribution
   selected measures, attribution reconciliation/level/currency selected measures, stale
   contribution and attribution posture, errored contribution and attribution blocking posture, core
   cash totals, explicit transaction-row trade-fee, withholding-tax, realized-FX-P&L,
   linked-cashflow measures, core cashflow projection total/booked/projected-settlement cashflow,
   projection
   degraded/unavailable posture, required currency/total/projection guardrails, and malformed
   payload behavior,
11. no broader methodology is claimed yet: portfolio-level FX attribution, aggregated
   transaction-cost beyond source-owned observed curves, execution, client income-needs planning,
   tax advice or after-tax optimization,
   risk attribution outside
   source-emitted historical attribution scalars,
   broader benchmark-relative performance analysis outside source-emitted attribution scalars, and
   full review-window source contracts remain source-owner follow-on scope.

Why it cannot be done now:

RFC-0042 intentionally avoided local calculation clones. The first risk, performance, and core cash
adapters are possible because `lotus-risk` publishes `RiskMetricsReport:v1`, drawdown response
output, concentration response output, rolling metrics response output, and historical attribution
response output, `lotus-performance` publishes workspace-summary TWR, active return, MWR output,
contribution output, and attribution output, and `lotus-core` publishes `HoldingsAsOf:v1` cash
totals, `TransactionLedgerWindow:v1` explicit transaction-row scalar evidence, and
`PortfolioCashflowProjection:v1` total, booked, and projected-settlement cashflow with explicit
portfolio currency.
Remaining source-owner methods are surfaced as degraded, unsupported, unavailable, malformed,
conflicting, or blocked states until their owning applications publish certified contracts.

Dependencies before implementation:

1. source-owner methodology and API contract,
2. source lineage, freshness, and content hashes,
3. validation of missing, partial, stale, conflicting, and permission-denied behavior,
4. manage adapter consumes source truth without becoming the source owner,
5. OpenAPI and evidence documentation in source-owning apps.

Expected implementation wave:

Implement source family by source family as source owners publish certified contracts.

Promotion proof:

1. source-owner unit/integration/live tests,
2. manage adapter tests,
3. live evidence with ready and degraded examples,
4. README/wiki/context updates in both source and manage repositories.

Latest WTBD-006 tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-source-methodology-proof/20260506-060312/critical-review.json`,
2. repo-native `make check` passed with `874` unit tests, lint, typecheck, OpenAPI quality,
   API vocabulary, no-alias, mesh contracts, and monetary-float guard,
3. focused source-adapter/doc proof passed with `52` tests across documentation current-state,
   performance, risk, core cash, and realized-source assembly behavior.

Latest WTBD-006 risk-drawdown tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-risk-drawdown-proof/20260506-061850/critical-review.json`,
2. `tests/unit/core/test_risk_realized_outcome_sources.py` passed with `16` tests,
3. tests cover source-owned absolute max drawdown, benchmark-relative max drawdown, ready snapshot
   assembly, stale source posture, unavailable benchmark-relative posture, missing fingerprint, and
   missing ready-value guardrails,
4. repo-native `make check` passed with `881` unit tests, lint, typecheck, OpenAPI quality,
   API vocabulary, no-alias, mesh contracts, and monetary-float guard,
5. manage preserves `lotus-risk` request fingerprint and supportability truth and performs no
   drawdown path, episode, or benchmark-relative calculation locally.

Latest WTBD-006 risk-concentration tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-risk-concentration-proof/20260506-064212/critical-review.json`,
2. `tests/unit/core/test_risk_realized_outcome_sources.py` passed with `24` tests,
3. tests cover source-owned HHI, top-position weight, issuer HHI, issuer partial-coverage degraded
   posture, issuer missing-coverage degraded posture, ready snapshot assembly, missing fingerprint,
   and missing ready-value guardrails,
4. repo-native `make check` passed with `889` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, no-alias, domain-data-product, trust telemetry, observability, and
   monetary-float guardrails before PR #96 merge,
5. manage preserves `lotus-risk` request fingerprint, supportability truth, issuer coverage
   posture, and concentration source units, and performs no HHI, top-position, issuer, or coverage
   calculation locally.

Latest WTBD-006 risk-rolling tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-risk-rolling-proof/20260506-081336/critical-review.json`,
2. `tests/unit/core/test_risk_realized_outcome_sources.py` passed with `33` tests,
3. tests cover source-owned latest rolling volatility, beta percentile, ready snapshot assembly,
   benchmark-unavailable degraded posture, risk-free-unavailable degraded posture, stale source
   posture, permission-blocked posture, missing fingerprint, and missing ready-value guardrails,
4. repo-native `make check` passed with `912` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, domain-data-product, trust telemetry, and observability contract gates,
5. manage preserves `lotus-risk` request fingerprint, supportability truth, selected period,
   selected metric, selected statistic, selected window length, benchmark/risk-free context,
   latest observation date, and source units, and performs no rolling-window, volatility, Sharpe,
   beta, tracking-error, information-ratio, drawdown, percentile, benchmark-alignment, or
   risk-free-alignment calculation locally.

Latest WTBD-006 risk rolling-tracking-error methodology proof:

1. `lotus-risk` PR #113 was merged to `main` as
   `e00ece9279082a96071bd9e745b7211232b82db6` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `d1330ee`,
2. `docs/methodologies/metrics/rolling-tracking-error.md` now records the implemented
   `ROLLING_TRACKING_ERROR` source-owner methodology for `RollingRiskMetricsReport:v1`, including
   percentage-point input conventions, decimal conversion, inner date alignment, `ddof=1` sample
   standard deviation, annualization, strict versus partial minimum observations, warm-up nulls,
   no-aligned-benchmark posture, and decimal-ratio output mapping,
3. `wiki/Mesh-Data-Products.md` now gives business, developer, operations, and sales/pre-sales
   guidance plus a Mermaid flow from `lotus-performance` return series through `lotus-risk`
   rolling tracking-error ownership into Gateway, Workbench, and manage realized-outcome
   consumption,
4. source-owner proof passed locally with `305` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation, and
   the focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_rolling_engine.py`
   methodology regressions,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: aggregated tax, aggregated FX, cash movement
   methodology beyond source-emitted totals, liquidity ladders, execution methodology, broader
   aggregate risk/performance products, and any client tax or OMS acknowledgement claims remain
   future source-owner work.

Latest WTBD-006 risk rolling-information-ratio methodology proof:

1. `lotus-risk` PR #114 was merged to `main` as
   `ffa881e3266c09a4d48044b50df5bb2db43bd489` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `105b716`,
2. `docs/methodologies/metrics/rolling-information-ratio.md` now records the implemented
   `ROLLING_INFORMATION_RATIO` source-owner methodology for `RollingRiskMetricsReport:v1`,
   including percentage-point input conventions, decimal conversion, inner date alignment,
   `ddof=1` sample standard deviation, annualization, strict versus partial minimum observations,
   warm-up nulls, no-aligned-benchmark posture, zero-tracking-error flagging, and dimensionless
   output mapping,
3. `wiki/Mesh-Data-Products.md` now describes rolling tracking error and rolling information ratio
   as implementation-backed active-risk metrics, with business, operations, developer, and
   sales/pre-sales guidance and explicit zero-tracking-error handling,
4. source-owner proof passed locally with `307` unit tests through `make check`, plus a focused e2e
   rolling active-risk contract test and local test-pyramid proof showing `307` unit, `94`
   integration, and `22` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates after the e2e test was added to preserve the
   governed test pyramid,
6. this advances RFC42-WTBD-006 but does not close it: aggregated tax, aggregated FX, cash movement
   methodology beyond source-emitted totals, liquidity ladders, execution methodology, broader
   aggregate risk/performance products, and any client tax or OMS acknowledgement claims remain
   future source-owner work.

Latest WTBD-006 risk rolling-volatility methodology proof:

1. `lotus-risk` PR #117 was merged to `main` as
   `8f04b24276bd73dd34ef5ce3edf59e81453858ae` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `c6eef3c`,
2. `docs/methodologies/metrics/rolling-volatility.md` now records the implemented
   `ROLLING_VOLATILITY` source-owner methodology for `RollingRiskMetricsReport:v1`, including
   percentage-point input conventions, decimal conversion, `ddof=1` sample standard deviation,
   annualization, strict versus partial minimum observations, warm-up nulls, no benchmark or
   risk-free dependency, constant-return zero-volatility behavior, and annualized decimal-ratio
   output mapping,
3. `wiki/Mesh-Data-Products.md` now describes rolling volatility alongside rolling tracking error
   and rolling information ratio as implementation-backed rolling-risk metrics with business,
   operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `318` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation, and
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_rolling_engine.py`
   methodology regressions,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: aggregated tax, aggregated FX, cash movement
   methodology beyond source-emitted totals, liquidity ladders, execution methodology, broader
   aggregate risk/performance products, and any client tax or OMS acknowledgement claims remain
   future source-owner work.

Latest WTBD-006 risk rolling-Sharpe methodology proof:

1. `lotus-risk` PR #118 was merged to `main` as
   `3f4bbfe6d536a1f3d68b773f917a3f059987db51` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `0b96201`,
2. `docs/methodologies/metrics/rolling-sharpe.md` now records the implemented
   `ROLLING_SHARPE` source-owner methodology for `RollingRiskMetricsReport:v1`, including
   percentage-point input conventions, decimal conversion, risk-free inner date alignment,
   `ddof=1` sample standard deviation, annualization, strict versus partial minimum observations,
   warm-up nulls, no-aligned-risk-free dependency posture, zero-excess-volatility flagging, and
   dimensionless annualized ratio output mapping,
3. `wiki/Mesh-Data-Products.md` now describes rolling Sharpe alongside rolling volatility, rolling
   tracking error, and rolling information ratio as implementation-backed rolling-risk metrics
   with business, operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `320` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation, and
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_rolling_engine.py`
   methodology regressions,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals, liquidity
   ladders, execution methodology, and any client tax or OMS acknowledgement claims remain future
   source-owner work.

Latest WTBD-006 risk rolling-beta methodology proof:

1. `lotus-risk` PR #119 was merged to `main` as
   `ffcfddbc24484811152c85582398528c0c879d98` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `bcccb0c`,
2. `docs/methodologies/metrics/rolling-beta.md` now records the implemented
   `ROLLING_BETA` source-owner methodology for `RollingRiskMetricsReport:v1`, including
   percentage-point input conventions, decimal conversion, benchmark inner date alignment, sample
   rolling covariance over benchmark sample variance with `ddof=1`, strict versus partial minimum
   observations, warm-up nulls, no-aligned-benchmark dependency posture,
   zero-benchmark-variance flagging, annualization-basis non-use, and dimensionless ratio output
   mapping,
3. `wiki/Mesh-Data-Products.md` now describes rolling beta alongside rolling volatility, rolling
   Sharpe, rolling tracking error, and rolling information ratio as implementation-backed
   rolling-risk metrics with business, operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `322` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation, and
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_rolling_engine.py`
   methodology regressions,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and any client tax or OMS acknowledgement claims
   remain future source-owner work.

Latest WTBD-006 risk rolling-maximum-drawdown methodology proof:

1. `lotus-risk` PR #120 was merged to `main` as
   `2c205372a5ac3bfc024a7eb61c0bd44383895078` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `429e284`,
2. `docs/methodologies/metrics/rolling-max-drawdown.md` now records the implemented
   `ROLLING_MAX_DRAWDOWN` source-owner methodology for `RollingRiskMetricsReport:v1`, including
   percentage-point input conventions, decimal conversion, annualization-basis non-use,
   cumulative-wealth and running-peak drawdown path construction, strict versus partial minimum
   observations, warm-up nulls, no benchmark or risk-free dependency posture, no-denominator
   posture, and decimal drawdown-ratio output mapping,
3. `wiki/Mesh-Data-Products.md` now describes rolling maximum drawdown alongside rolling
   volatility, rolling Sharpe, rolling beta, rolling tracking error, and rolling information ratio
   as implementation-backed rolling-risk metrics with business, operations, developer, and
   sales/pre-sales guidance,
4. source-owner proof passed locally with `324` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation, and
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_rolling_engine.py`
   methodology regressions,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and any client tax or OMS acknowledgement claims
   remain future source-owner work.

Latest WTBD-006 risk drawdown analytics maximum-drawdown methodology proof:

1. `lotus-risk` PR #129 was merged to `main` as
   `6ac31ac860275561cb5770a49f1c2d7aeb7440e6` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `3f2e37a`,
2. `docs/methodologies/metrics/drawdown-max-drawdown.md` now records the implemented
   source-owner methodology for `DrawdownAnalyticsReport:v1`; the `MAX_DRAWDOWN` source-owner
   methodology includes percentage-point input conventions, decimal cumulative-wealth and
   running-peak drawdown behavior, decimal `summary.max_drawdown` output, episode
   peak/trough/recovery semantics, empty-period insufficient-data posture, never-underwater
   zero-drawdown posture, duration-unit day-counter behavior, and episode-list filter isolation
   from the summary maximum-drawdown value,
3. `wiki/Mesh-Data-Products.md` now describes `DrawdownAnalyticsReport:v1` maximum drawdown
   alongside `RiskMetricsReport:v1` and `RollingRiskMetricsReport:v1` metrics as
   implementation-backed source-owner risk analytics with business, operations, developer, and
   sales/pre-sales guidance,
4. source-owner proof passed locally with `342` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_drawdown_engine.py`
   methodology regressions, and test-pyramid proof with `23` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and any client tax or OMS acknowledgement claims
   remain future source-owner work.

Latest WTBD-006 risk drawdown analytics average-drawdown methodology proof:

1. `lotus-risk` PR #130 was merged to `main` as
   `d96651d0c34e2414f61fb70c2e1a3106134c3632` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `01d181b`,
2. `docs/methodologies/metrics/drawdown-average-drawdown.md` now records the implemented
   source-owner methodology for `DrawdownAnalyticsReport:v1`; the `AVERAGE_DRAWDOWN`
   source-owner methodology includes percentage-point input conventions, decimal
   cumulative-wealth and running-peak drawdown behavior, decimal
   `summary.average_drawdown` output, strictly-underwater observation inclusion,
   empty-period insufficient-data posture, never-underwater zero-drawdown posture,
   duration-unit day-counter isolation, and episode-list filter isolation from the summary
   average-drawdown value,
3. `wiki/Mesh-Data-Products.md` now describes `DrawdownAnalyticsReport:v1` average drawdown
   alongside maximum drawdown as implementation-backed source-owner risk analytics with business,
   operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `344` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_drawdown_engine.py`
   methodology regressions, full `tests/e2e` proof with `24` tests, and test-pyramid proof with
   `24` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and any client tax or OMS acknowledgement claims
   remain future source-owner work.

Latest WTBD-006 risk drawdown analytics ulcer-index methodology proof:

1. `lotus-risk` PR #131 was merged to `main` as
   `ce129e4ba52ff20f6e620df837238a852d7a522c` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `6f244d1`,
2. `docs/methodologies/metrics/drawdown-ulcer-index.md` now records the implemented
   source-owner methodology for `DrawdownAnalyticsReport:v1`; the `ULCER_INDEX`
   source-owner methodology includes percentage-point input conventions, decimal
   cumulative-wealth and running-peak drawdown behavior, non-negative decimal
   `summary.ulcer_index` output, full-path squared drawdown inclusion including zero peak
   observations, empty-period insufficient-data posture, never-underwater zero-drawdown posture,
   duration-unit day-counter isolation, and episode-list filter isolation from the summary
   ulcer-index value,
3. `wiki/Mesh-Data-Products.md` now describes `DrawdownAnalyticsReport:v1` ulcer index alongside
   maximum drawdown and average drawdown as implementation-backed source-owner risk analytics with
   business, operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `346` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_drawdown_engine.py`
   methodology regressions, and test-pyramid proof with `24` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and any client tax or OMS acknowledgement claims
   remain future source-owner work.

Latest WTBD-006 risk drawdown analytics time-under-water methodology proof:

1. `lotus-risk` PR #132 was merged to `main` as
   `d44aae1ec899c59565169b5fd4434cdedb00f76d` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `8a7e507`,
2. `docs/methodologies/metrics/drawdown-time-under-water.md` now records the implemented
   source-owner methodology for `DrawdownAnalyticsReport:v1`; `TIME_UNDER_WATER_DAYS` includes
   percentage-point input conventions, decimal cumulative-wealth and running-peak drawdown
   behavior, observation-count `summary.time_under_water_days` output, strictly-underwater
   observation counting, explicit non-duration posture for calendar/business-day settings,
   empty-period insufficient-data posture, never-underwater zero posture, duration-unit
   day-counter isolation, and episode-list filter isolation,
3. `wiki/Mesh-Data-Products.md` describes time under water alongside maximum drawdown, average
   drawdown, and ulcer index as implementation-backed source-owner risk analytics with audience
   guidance,
4. source-owner proof passed locally with `348` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_drawdown_engine.py`, and
   test-pyramid proof with `24` e2e tests,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and client tax/OMS claims remain future source-owner
   work.

Latest WTBD-006 manage drawdown analytics consumer-preservation proof:

1. `lotus-manage` now preserves source-emitted `DrawdownAnalyticsReport:v1` average drawdown,
   ulcer index, and time-under-water values in RFC-0042 realized outcome snapshots through
   `realized_drawdown_source_from_drawdown_response`,
2. the adapter maps only `summary.average_drawdown`, `summary.ulcer_index`, and
   `summary.time_under_water_days` values supplied by `lotus-risk`; it does not calculate cumulative wealth, running peaks, underwater paths,
   squared drawdowns, observation counts,
   episode lists, relative benchmark behavior, or any drawdown methodology locally,
3. source references, request fingerprints, as-of date, supportability state, quality, and reason
   codes remain source-owned and hash-backed so report, AI, portfolio-memory, Gateway, and
   Workbench consumers can preserve the source-owner posture without reconstructing risk facts,
4. focused Manage proof covers maximum drawdown, relative maximum drawdown, average drawdown,
   ulcer index, time-under-water, degraded relative benchmark posture, and realized-snapshot
   supportability through `tests/unit/core/test_risk_realized_outcome_sources.py`,
5. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, broader FX methodology beyond performance-owned Karnosky-Singer attribution totals,
   predictive execution, OMS acknowledgement, client tax advice, after-tax optimization, and
   financial-planning claims remain unsupported source-owner work.

Latest WTBD-006 risk concentration position-HHI methodology proof:

1. `lotus-risk` PR #133 was merged to `main` as
   `dea20b5a6f99403a9b8e974ac9da823c691c5465` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `1e2f926`,
2. `docs/methodologies/metrics/concentration-hhi.md` now records the implemented source-owner
   methodology for `ConcentrationRiskReport:v1`; `POSITION_HHI` includes stateless, stateful, and
   simulation source paths, positive numeric position-value extraction, market-value versus
   quantity fallback precedence, decimal position-weight construction, conventional `0..10000` Herfindahl-Hirschman
   scaling, six-decimal response rounding, proposed-state fallback to
   current HHI when projected values are unavailable, input-universe option boundaries, and
   issuer-enrichment isolation from `risk_proxy.hhi_*` outputs,
3. `wiki/Mesh-Data-Products.md` describes position HHI as implementation-backed source-owner
   concentration analytics and directs downstream services to preserve `ConcentrationRiskReport:v1`
   concentration outputs rather than recomputing concentration locally,
4. source-owner proof passed locally with `350` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_concentration_engine.py`,
   and test-pyramid proof with `24` e2e tests,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and client tax/OMS claims remain future source-owner
   work.

Latest WTBD-006 risk concentration top-position methodology proof:

1. `lotus-risk` PR #134 was merged to `main` as
   `21ef697a1c308a3d8ea7c8e40e06019544be7e93` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `dd25844`,
2. `docs/methodologies/metrics/concentration-top-position-weight.md` now records the implemented
   source-owner methodology for `ConcentrationRiskReport:v1`; `TOP_POSITION_WEIGHT` includes
   stateless, stateful, and simulation source paths, positive numeric position-value extraction,
   market-value versus quantity fallback precedence, decimal `0..1` top-position weight output,
   six-decimal response rounding, proposed-state fallback to current top-position weight when
   projected values are unavailable, deterministic top-position driver selection, input-universe
   option boundaries, and issuer-enrichment isolation from
   `single_position_concentration.top_position_*` outputs,
3. `wiki/Mesh-Data-Products.md` describes top-position weight as implementation-backed
   source-owner concentration analytics and directs downstream services to preserve
   `ConcentrationRiskReport:v1` concentration outputs rather than recomputing concentration
   locally,
4. source-owner proof passed locally with `352` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_concentration_engine.py`,
   and test-pyramid proof with `24` e2e tests,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and client tax/OMS claims remain future source-owner
   work.

Latest WTBD-006 risk concentration top-N cumulative methodology proof:

1. `lotus-risk` PR #135 was merged to `main` as
   `02352279c4a990f386ec582e8f839fc3c359437f` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `59277e5`,
2. `docs/methodologies/metrics/concentration-top-n-cumulative-weight.md` now records the
   implemented source-owner methodology for `ConcentrationRiskReport:v1`;
   `TOP_N_CUMULATIVE_WEIGHT` includes stateless, stateful, and simulation source paths, positive
   numeric position-value extraction, market-value versus quantity fallback precedence, decimal
   `0..1` top-N cumulative weight output, six-decimal response rounding, request-contract
   `top_n` bounds, proposed-state fallback to current top-N cumulative weight when projected
   values are unavailable, top-N sorted-weight summation, input-universe option boundaries, and
   issuer-enrichment isolation from
   `single_position_concentration.top_n_cumulative_weight_*` outputs,
3. `wiki/Mesh-Data-Products.md` describes top-N cumulative weight as implementation-backed
   source-owner concentration analytics and directs downstream services to preserve
   `ConcentrationRiskReport:v1` concentration outputs rather than recomputing concentration
   locally,
4. source-owner proof passed locally with `354` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_concentration_engine.py`,
   and test-pyramid proof with `24` e2e tests,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and client tax/OMS claims remain future source-owner
   work.

Latest WTBD-006 risk concentration issuer-HHI methodology proof:

1. `lotus-risk` PR #136 was merged to `main` as
   `ed9dba4663b718ae86c326f7d1f7ae591177e322` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `3dc7293`,
2. `docs/methodologies/metrics/concentration-issuer-hhi.md` now records the implemented
   source-owner methodology for `ConcentrationRiskReport:v1`; `ISSUER_HHI` includes stateless,
   stateful, and simulation source paths, positive numeric position-value extraction,
   market-value versus quantity fallback precedence, conventional `0..10000` issuer-HHI output,
   six-decimal response rounding, proposed-state fallback to current issuer HHI when projected
   issuer buckets are unavailable, covered-subset issuer aggregation, legal versus
   ultimate-parent issuer grouping, issuer-enrichment precedence, issuer coverage/supportability
   posture, and isolation from `risk_proxy.hhi_*` and `single_position_concentration.*` outputs,
3. `wiki/Mesh-Data-Products.md` describes issuer HHI as implementation-backed source-owner
   concentration analytics and directs downstream services to preserve
   `ConcentrationRiskReport:v1` concentration outputs rather than recomputing concentration
   locally,
4. source-owner proof passed locally with `356` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_concentration_engine.py`,
   and test-pyramid proof with `24` e2e tests,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and client tax/OMS claims remain future source-owner
   work.

Latest WTBD-006 risk concentration top-issuer methodology proof:

1. `lotus-risk` PR #137 was merged to `main` as
   `2da6e3a8346d5a188484750436a0258776918620` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `1e1eb14`,
2. `docs/methodologies/metrics/concentration-top-issuer-weight.md` now records the implemented
   source-owner methodology for `ConcentrationRiskReport:v1`; `TOP_ISSUER_WEIGHT` includes
   stateless, stateful, and simulation source paths, positive numeric position-value extraction,
   market-value versus quantity fallback precedence, decimal `0..1` top-issuer weight output,
   six-decimal response rounding, proposed-state fallback to current top issuer when projected
   issuer buckets are unavailable, covered-subset issuer aggregation, legal versus
   ultimate-parent issuer grouping, issuer-enrichment precedence, deterministic top-issuer driver
   selection, issuer coverage/supportability posture, and isolation from `risk_proxy.hhi_*` and
   `single_position_concentration.*` outputs,
3. `wiki/Mesh-Data-Products.md` describes top issuer weight as implementation-backed
   source-owner concentration analytics and directs downstream services to preserve
   `ConcentrationRiskReport:v1` concentration outputs rather than recomputing concentration
   locally,
4. source-owner proof passed locally with `358` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_concentration_engine.py`,
   and test-pyramid proof with `24` e2e tests,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance products,
   aggregated tax, aggregated FX, cash movement methodology beyond source-emitted totals,
   liquidity ladders, execution methodology, and client tax/OMS claims remain future source-owner
   work.

Latest WTBD-006 risk volatility methodology proof:

1. `lotus-risk` PR #121 was merged to `main` as
   `457f28dedea2a9db386192f5d00a6905e2f1c49a` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `2c09ab2`,
2. `docs/methodologies/metrics/risk-volatility.md` now records the implemented
   source-owner methodology for `RiskMetricsReport:v1`; the `VOLATILITY` source-owner methodology
   includes percentage-point input conventions, optional log-return transform, frequency
   compounding before volatility, `ddof=1` sample standard deviation, decimal
   `details.standard_deviation`, annualized percentage-point `metrics.VOLATILITY.value`, default
   and override annualization-factor resolution, no benchmark or risk-free dependency posture,
   no-denominator posture, and insufficient-data failure behavior,
3. `wiki/Mesh-Data-Products.md` now describes `RiskMetricsReport:v1` volatility alongside
   `RollingRiskMetricsReport:v1` metrics as implementation-backed source-owner risk metrics
   with business, operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `326` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_risk_engine.py`
   methodology regressions, and an e2e public-contract test for `/analytics/risk/calculate`,
5. local test-pyramid gate passed with `23` e2e tests within policy, and GitHub PR Merge Gate
   passed workflow lint, lint/typecheck/security, unit, integration, e2e, test-pyramid,
   coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, aggregated tax, aggregated FX, cash movement methodology beyond source-emitted
   totals, liquidity ladders, execution methodology, and any client tax or OMS acknowledgement
   claims remain future source-owner work.

Latest WTBD-006 risk Sharpe methodology proof:

1. `lotus-risk` PR #122 was merged to `main` as
   `932600162df7482a6d9c01a7470760238cab57ce` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `cdb25df`,
2. `docs/methodologies/metrics/risk-sharpe.md` now records the implemented source-owner
   methodology for `RiskMetricsReport:v1`; the `SHARPE` source-owner methodology includes
   percentage-point input conventions, optional log-return transform, frequency compounding before
   Sharpe, `ddof=1` sample standard deviation, decimal `details.mean_return`,
   `details.volatility`, and `details.periodic_risk_free_rate`, dimensionless annualized
   `metrics.SHARPE.value`; the dimensionless annualized `metrics.SHARPE.value` uses default and
   override annualization-factor resolution, no benchmark dependency posture,
   zero-volatility fail-closed posture, and insufficient-data failure behavior,
3. `wiki/Mesh-Data-Products.md` now describes `RiskMetricsReport:v1` Sharpe alongside
   volatility and `RollingRiskMetricsReport:v1` metrics as implementation-backed source-owner risk
   metrics with business, operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `328` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_risk_engine.py`
   methodology regressions, and test-pyramid proof with `23` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, aggregated tax, aggregated FX, cash movement methodology beyond source-emitted
   totals, liquidity ladders, execution methodology, and any client tax or OMS acknowledgement
   claims remain future source-owner work.

Latest WTBD-006 risk Sortino methodology proof:

1. `lotus-risk` PR #126 was merged to `main` as
   `dbe16b647f972ff626a8b6eb11e06041b6e0f46a` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `81f787e`,
2. `docs/methodologies/metrics/risk-sortino.md` now records the implemented source-owner
   methodology for `RiskMetricsReport:v1`; `SORTINO` source-owner methodology includes
   percentage-point input conventions, optional log-return transform, frequency compounding before
   Sortino, annual-to-periodic MAR conversion, full-sample mean excess return, downside-only
   root-mean-square denominator, decimal `details.periodic_mar`, `details.mean_return`,
   `details.excess_return`, `details.annualized_excess_return`, and
   `details.downside_deviation`, dimensionless annualized `metrics.SORTINO.value`, no benchmark
   dependency posture, no risk-free dependency posture, no-downside-observation fail-closed
   posture, and insufficient-data failure behavior,
3. `wiki/Mesh-Data-Products.md` now describes `RiskMetricsReport:v1` Sortino alongside
   volatility, Sharpe, beta, tracking error, information ratio, and `RollingRiskMetricsReport:v1`
   metrics as implementation-backed source-owner risk metrics with business, operations,
   developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `336` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_risk_engine.py`
   methodology regressions, and test-pyramid proof with `23` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, aggregated tax, aggregated FX, cash movement methodology beyond source-emitted
   totals, liquidity ladders, execution methodology, and any client tax or OMS acknowledgement
   claims remain future source-owner work.

Latest WTBD-006 risk VaR methodology proof:

1. `lotus-risk` PR #127 was merged to `main` as
   `957d1a4d37e75e70a9915e65584fc41e7328f082` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `85116ab`,
2. `docs/methodologies/metrics/risk-var.md` now records the implemented source-owner methodology
   for `RiskMetricsReport:v1`; the `VAR` source-owner methodology includes percentage-point input
   conventions, optional log-return transform, frequency compounding before VaR, historical,
   Gaussian, and Cornish-Fisher method behavior, signed return-threshold output in percentage
   points, square-root-of-time horizon scaling, optional expected-shortfall calculation, signed
   `details.base_var`, `details.base_expected_shortfall`, and `details.expected_shortfall`, no
   benchmark dependency posture, no risk-free dependency posture, no annualization-factor posture,
   and insufficient-data failure behavior,
3. `wiki/Mesh-Data-Products.md` now describes `RiskMetricsReport:v1` VaR alongside volatility,
   Sharpe, Sortino, beta, tracking error, information ratio, and `RollingRiskMetricsReport:v1`
   metrics as implementation-backed source-owner risk metrics with business, operations,
   developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `338` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_risk_engine.py`
   methodology regressions, and test-pyramid proof with `23` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, aggregated tax, aggregated FX, cash movement methodology beyond source-emitted
   totals, liquidity ladders, execution methodology, and any client tax or OMS acknowledgement
   claims remain future source-owner work.

Latest WTBD-006 risk drawdown methodology proof:

1. `lotus-risk` PR #128 was merged to `main` as
   `4784839067027d991500ff2d19c728122e227466` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `edde5df`,
2. `docs/methodologies/metrics/risk-drawdown.md` now records the implemented source-owner
   methodology for `RiskMetricsReport:v1`; the `DRAWDOWN` source-owner methodology includes
   percentage-point input conventions, frequency compounding before drawdown, explicit
   no-log-return posture, cumulative-wealth and running-peak behavior, signed percentage-point
   `metrics.DRAWDOWN.value`, signed `details.max_drawdown`, peak/trough/recovery episode timing
   details, no benchmark dependency posture, no risk-free dependency posture, no
   annualization-factor posture, no-denominator posture beyond the running peak wealth path, and
   insufficient-data failure behavior,
3. `wiki/Mesh-Data-Products.md` now describes `RiskMetricsReport:v1` drawdown alongside
   volatility, Sharpe, Sortino, VaR, beta, tracking error, information ratio, and
   `RollingRiskMetricsReport:v1` metrics as implementation-backed source-owner risk metrics with
   business, operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `340` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_risk_engine.py`
   methodology regressions, and test-pyramid proof with `23` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, aggregated tax, aggregated FX, cash movement methodology beyond source-emitted
   totals, liquidity ladders, execution methodology, and any client tax or OMS acknowledgement
   claims remain future source-owner work.

Latest WTBD-006 risk beta methodology proof:

1. `lotus-risk` PR #123 was merged to `main` as
   `d6c50e126fa81250ab16f0299380fb0ad9022619` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `7738cac`,
2. `docs/methodologies/metrics/risk-beta.md` now records the implemented source-owner
   methodology for `RiskMetricsReport:v1`; the `BETA` source-owner methodology includes
   percentage-point input conventions, optional log-return transform, frequency compounding before
   beta, strict inner date alignment, `ddof=1` sample covariance and benchmark variance,
   percentage-point-squared `details.covariance` and `details.benchmark_variance`,
   dimensionless slope `metrics.BETA.value`, no risk-free dependency posture, zero-benchmark-variance
   fail-closed posture, and insufficient-aligned-observation failure behavior,
3. `wiki/Mesh-Data-Products.md` now describes `RiskMetricsReport:v1` beta alongside volatility,
   Sharpe, and `RollingRiskMetricsReport:v1` metrics as implementation-backed source-owner risk
   metrics with business, operations, developer, and sales/pre-sales guidance,
4. source-owner proof passed locally with `330` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_risk_engine.py`
   methodology regressions, and test-pyramid proof with `23` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, aggregated tax, aggregated FX, cash movement methodology beyond source-emitted
   totals, liquidity ladders, execution methodology, and any client tax or OMS acknowledgement
   claims remain future source-owner work.

Latest WTBD-006 risk tracking-error methodology proof:

1. `lotus-risk` PR #124 was merged to `main` as
   `46eddb4dc332bb1e4a79c22b1bd557f2b2db2cb9` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `a1d8898`,
2. `docs/methodologies/metrics/risk-tracking-error.md` now records the implemented source-owner
   methodology for `RiskMetricsReport:v1`; the `TRACKING_ERROR` source-owner methodology includes
   percentage-point input conventions, optional log-return transform, frequency compounding before
   tracking error, strict inner date alignment, `ddof=1` sample active-return standard deviation,
   decimal `details.active_volatility` and `details.annualized_tracking_error`,
   annualized percentage-point `metrics.TRACKING_ERROR.value`, no risk-free dependency posture, no-denominator
   posture, constant-active-return zero tracking-error posture, and insufficient-aligned-observation
   failure behavior,
3. `wiki/Mesh-Data-Products.md` now describes `RiskMetricsReport:v1` tracking error alongside
   volatility, Sharpe, beta, and `RollingRiskMetricsReport:v1` metrics as
   implementation-backed source-owner risk metrics with business, operations, developer, and
   sales/pre-sales guidance,
4. source-owner proof passed locally with `332` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_risk_engine.py`
   methodology regressions, and test-pyramid proof with `23` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, aggregated tax, aggregated FX, cash movement methodology beyond source-emitted
   totals, liquidity ladders, execution methodology, and any client tax or OMS acknowledgement
   claims remain future source-owner work.

Latest WTBD-006 risk information-ratio methodology proof:

1. `lotus-risk` PR #125 was merged to `main` as
   `7ccf5667e6676b8f1865ebd9768b8913262d3d3b` and the repo-local wiki was published to
   `lotus-risk.wiki` commit `7a0aa9e`,
2. `docs/methodologies/metrics/risk-information-ratio.md` now records the implemented
   source-owner methodology for `RiskMetricsReport:v1`; `INFORMATION_RATIO` source-owner methodology
   includes percentage-point input conventions, optional log-return transform,
   frequency compounding before information ratio, strict inner date alignment, active-return
   construction, `ddof=1` sample active-return standard deviation, decimal
   `details.portfolio_mean_return`, `details.benchmark_mean_return`,
   `details.active_mean_return`, `details.tracking_error`,
   `details.annualized_active_return`, and `details.annualized_tracking_error`,
   dimensionless annualized `metrics.INFORMATION_RATIO.value`, no risk-free dependency posture,
   zero-tracking-error fail-closed denominator posture, and insufficient-aligned-observation
   failure behavior,
3. `wiki/Mesh-Data-Products.md` now describes `RiskMetricsReport:v1` information ratio alongside
   volatility, Sharpe, beta, tracking error, and `RollingRiskMetricsReport:v1` metrics as
   implementation-backed source-owner risk metrics with business, operations, developer, and
   sales/pre-sales guidance,
4. source-owner proof passed locally with `334` unit tests through `make check`, including Ruff,
   format, no-alias, mypy, OpenAPI quality, API vocabulary, domain-data-product validation,
   focused `tests/unit/test_methodology_docs.py` and `tests/unit/test_risk_engine.py`
   methodology regressions, and test-pyramid proof with `23` e2e tests within policy,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. this advances RFC42-WTBD-006 but does not close it: broader aggregate risk/performance
   products, aggregated tax, aggregated FX, cash movement methodology beyond source-emitted
   totals, liquidity ladders, execution methodology, and any client tax or OMS acknowledgement
   claims remain future source-owner work.

Latest WTBD-006 risk-attribution tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-risk-attribution-proof/20260506-083000/critical-review.json`,
2. `tests/unit/core/test_risk_realized_outcome_sources.py` passed with `41` tests,
3. tests cover source-owned historical attribution total value, explicit contributor component
   contribution, ready snapshot assembly, source quality-flag degraded posture, period-error
   blocked posture, missing fingerprint, missing ready-value guardrails, and contributor-group-key
   guardrails,
4. repo-native `make check` passed with `920` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, domain-data-product, trust telemetry, and observability contract gates,
5. manage preserves `lotus-risk` request fingerprint, supportability truth, selected period,
   attribution type, metric, grouping dimension, selected measure, contributor group key where
   applicable, stateful active-risk support metadata, quality-flag posture, period-error posture,
   period end date, as-of date, and source units, and performs no covariance, contribution,
   residual, grouping, top-contributor, or support-matrix calculation locally.

Latest WTBD-006 risk historical-attribution supportability proof:

1. `lotus-risk` PR #139 was merged to `main` as `40ac7a5` and the repo-local wiki was published
   to `lotus-risk.wiki` commit `421ae79`,
2. `HistoricalRiskAttributionReport:v1` now degrades response-level
   `metadata.calculation_supportability` whenever any attribution set emits source-owned quality
   flags, including missing grouping data, empty active-risk alignment, and unsupported
   attribution combinations,
3. `docs/methodologies/metrics/attribution-volatility.md`,
   `docs/methodologies/metrics/attribution-tracking-error.md`,
   `docs/standards/risk-analytics-contract.md`, repo context, and wiki source record the
   downstream preservation rule,
4. source-owner proof passed locally with `make ci`, including Ruff, mypy, OpenAPI quality, API
   vocabulary, domain-product validation, migration smoke, test-pyramid gate, dependency audit
   with zero known vulnerabilities, `360` unit tests, `80` integration tests, `24` e2e tests,
   `98%` coverage, and Docker build,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/security, unit, integration, e2e,
   test-pyramid, coverage, and Docker build gates,
6. Manage consumes this as source-owner supportability truth only and performs no covariance,
   contribution, residual, grouping, supportability, or active-risk methodology calculation
   locally.

Latest WTBD-006 core-transaction-ledger tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-core-transaction-ledger-proof/20260506-085229/critical-review.json`,
2. `tests/unit/core/test_core_realized_outcome_sources.py` passed with `15` tests,
3. tests cover source-owned trade fee, withholding tax, realized FX P&L, linked cashflow amount,
   ready tax-dimension snapshot assembly, degraded source-owner posture, missing transaction-row
   guardrails, and missing selected source-value guardrails,
4. repo-native `make check` passed with `928` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, no-alias, domain-data-product, trust-telemetry, observability, and
   monetary-float guardrails,
5. manage preserves `lotus-core` product identity, portfolio id, as-of date, generated/evidence
   timestamp, data-quality posture, source fingerprint, transaction id/type, selected measure,
   selected source field, and source units, and performs no transaction aggregation, tax
   calculation, FX calculation, cash movement aggregation, currency conversion, or
   execution-quality inference locally.

Latest WTBD-006 core-cashflow-projection tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-core-cashflow-projection-proof/20260506-101500/critical-review.json`,
2. source-owner hardening was completed, merged, CI-proven, and wiki-published in `lotus-core`
   PR #338 as merge commit `1ab53453198bede79b1d8ec7326120f27adc9ba5`; the core source product
   now exposes `PortfolioCashflowProjection:v1` product metadata, latest evidence timestamp,
   deterministic source fingerprint, and explicit `portfolio_currency`,
3. local manage adapter proof passed with `33` focused core/realized-source tests,
4. tests cover source-owned total net cashflow, ready cash-dimension snapshot assembly, degraded
   source-owner posture, unavailable source-owner posture, missing portfolio currency, missing
   total net cashflow, and missing include-projected posture,
5. manage preserves `lotus-core` product identity, portfolio id, as-of date, generated/evidence
   timestamp, data-quality posture, source fingerprint, projection range, include-projected
   posture, selected measure, and portfolio currency, and performs no cashflow forecasting,
   cashflow aggregation, liquidity-ladder calculation, currency conversion, or execution-quality
   inference locally.

Latest WTBD-006 core realized-outcome source-boundary proof:

1. `lotus-core` PR #343 was merged to `main` as
   `25cbff191d681a6518dfc7072dc2a8c9cf2fd7f0` and the repo-local wiki was published to
   `lotus-core.wiki` commit `a9d1f68`,
2. `docs/architecture/RFC-0083-source-data-product-catalog.md` now records the source/non-source
   boundary for `HoldingsAsOf:v1`, `TransactionLedgerWindow:v1`,
   `PortfolioCashflowProjection:v1`, `PortfolioTaxLotWindow:v1`, and
   `TransactionCostCurve:v1`,
3. `wiki/Mesh-Data-Products.md` now gives business, developer, operations, and sales/client-demo
   guidance plus a Mermaid source-boundary diagram for core realized outcome evidence,
4. local source-owner proof passed with `8` focused tests:
   `python -m pytest tests/unit/docs/test_source_data_product_boundaries.py tests/unit/test_domain_data_product_contracts.py -q`,
5. GitHub PR Merge Gate passed workflow lint, lint/typecheck/contracts/security, unit,
   unit-db, integration-lite, transaction contract tests, coverage, docker build, docker smoke,
   E2E smoke, latency, and fast load gates,
6. this does not close RFC42-WTBD-006: aggregated tax, aggregated FX, cash movement methodology
   beyond source-emitted totals, liquidity ladders, execution methodology, and any client tax or
   OMS acknowledgement claims remain future source-owner work.

Latest WTBD-006 core cashflow-projection methodology proof:

1. `lotus-core` PR #344 was merged to `main` as
   `3a29c3ea92fce92d39fbc91f325bd04cb1157d20` and the repo-local wiki was published to
   `lotus-core.wiki` commit `231bd75`,
2. `docs/methodologies/source-data-products/portfolio-cashflow-projection.md` now records the
   implemented `PortfolioCashflowProjection:v1` methodology with endpoint modes, inputs,
   upstream source tables, unit conventions, variable dictionary, formulas, deterministic steps,
   validation/failure behavior, configuration options, outputs, and a worked example,
3. the methodology pins booked-only versus projected mode behavior, latest-cashflow-row selection,
   settlement-dated external `DEPOSIT`/`WITHDRAWAL` inclusion, same-day booked/projected
   additivity, empty-day cumulative carry-forward, portfolio-base-currency output, and explicit
   boundaries from liquidity ladders, tax methodology, performance returns, market impact, and OMS
   execution forecasting,
4. `wiki/Cashflow-Calculator.md` and `wiki/Mesh-Data-Products.md` now carry implementation-backed
   business, operations, developer, and sales/client-demo truth for the cashflow projection source
   product,
5. local source-owner proof passed with `8` focused service/doc tests plus the OpenAPI cashflow
   projection example test, and local contract gates passed for OpenAPI quality, API vocabulary,
   and source-data-product contracts,
6. GitHub PR Merge Gate passed workflow lint, lint/typecheck/contracts/security, unit,
   unit-db, integration-lite, ops-contract, transaction contract tests, coverage, docker build,
   docker smoke, E2E smoke, latency, and fast performance gates,
7. this advances RFC42-WTBD-006 but does not close it: aggregated tax, aggregated FX, liquidity
   ladders, execution methodology, broader aggregate risk/performance products, and any client tax
   or OMS acknowledgement claims remain future source-owner work.

Latest WTBD-006 core cashflow-component evidence proof:

1. `lotus-core` `PortfolioCashflowProjection:v1` now emits daily
   `booked_net_cashflow`, `projected_settlement_cashflow`, `net_cashflow`, and cumulative
   cashflow points plus window-level `booked_total_net_cashflow`,
   `projected_settlement_total_cashflow`, and `total_net_cashflow`,
2. the source-owner methodology records `N_d = B_d + S_d`, `BT`, `ST`, and `T = BT + ST = C_E`,
   preserving booked and projected-settlement components without turning the product into a
   liquidity ladder, client income-needs plan, funding recommendation, or OMS forecast,
3. `lotus-manage` can now adapt the source-emitted booked and projected-settlement totals as
   selected `CASH_RESIDUAL` evidence through `src/core/outcomes/core_sources.py` without
   aggregating cashflows locally,
4. focused source-owner proof passed locally in `lotus-core` with `14` tests across the cashflow
   projection service/router, OpenAPI contract, and methodology guard,
5. focused manage adapter proof passed locally with `31` core realized-outcome source tests,
6. this advances RFC42-WTBD-006 but does not close it: the components are operational cash-movement
   evidence only; client income planning, MWR flow context, client tax,
   execution methodology, and OMS acknowledgement remain future source-owner work.

Latest WTBD-006 core liquidity-ladder methodology proof:

1. `lotus-core` PR #356 was merged to `main` as
   `d47eb716e2992ea0988ddbb92e402594d4193dec` and the repo-local wiki was published to
   `lotus-core.wiki` commit `28c4ae2`,
2. `docs/methodologies/source-data-products/portfolio-liquidity-ladder.md` now records the
   implemented `PortfolioLiquidityLadder:v1` methodology with endpoint input semantics,
   upstream source tables, variable dictionary, deterministic formulas, validation/failure
   behavior, output contract semantics, and worked examples,
3. the methodology pins opening cash balance, fixed `T0`, `T_PLUS_1`, `T_PLUS_2_TO_7`,
   `T_PLUS_8_TO_30`, and `T_PLUS_31_TO_HORIZON` buckets, booked and optionally projected
   settlement cashflows, net bucket cashflow, cumulative cash, shortfall, and asset exposure by
   instrument liquidity tier,
4. `contracts/domain-data-products/lotus-core-products.v1.json`,
   `docs/standards/route-contract-family-registry.json`,
   `docs/architecture/RFC-0083-source-data-product-catalog.md`, and
   `wiki/Mesh-Data-Products.md` now carry implementation-backed source-product, route-family,
   source-boundary, and business/demo documentation for the liquidity ladder,
5. source-owner proof passed locally with focused service/router/catalog/security/docs tests,
   `make source-data-product-contract-guard`, `make domain-product-validate`,
   `make openapi-gate`, `make api-vocabulary-gate`, `make test-integration-lite`, and
   `make coverage-gate`,
6. GitHub Feature Lane and PR Merge Gate passed workflow lint, lint/typecheck/contracts/security,
   unit, unit-db, integration-lite, ops-contract, transaction contract tests, coverage, docker
   build, docker smoke, E2E smoke, latency, and fast performance gates,
7. wiki publication was completed from repo-local source with `Sync-RepoWikis.ps1 -Publish
   -Repository lotus-core` and post-publish check-only returned `DiffCount 0`,
8. this advances RFC42-WTBD-006 but does not close it: source-owned liquidity ladders are
   operational cash and liquidity-readiness evidence only, not client advice, funding
   recommendation, income-needs planning, tax methodology, FX attribution, market-impact model,
   best-execution certification, venue routing, or OMS acknowledgement.

Latest WTBD-006 core transaction-ledger-window methodology proof:

1. `lotus-core` PR #347 was merged to `main` as
   `7aef82bc8f9232c62333b8386001527b19829f86` and the repo-local wiki was published to
   `lotus-core.wiki` commit `6bb1041`,
2. `docs/methodologies/source-data-products/transaction-ledger-window.md` now records the
   implemented `TransactionLedgerWindow:v1` methodology with endpoint mode coverage, inputs,
   upstream source tables, unit conventions, variable dictionary, formulas, deterministic steps,
   validation/failure behavior, configuration options, outputs, and a worked example,
3. the methodology pins booked and projected-inclusive ledger modes, effective as-of date
   resolution, portfolio/instrument/security/transaction type/FX-event/date-window filters,
   joined row-level transaction-cost and cashflow evidence preservation, field-aware
   reporting-currency restatement from latest FX rates, and empty/complete/paged data-quality
   posture,
4. `docs/architecture/RFC-0083-source-data-product-catalog.md` and `wiki/Mesh-Data-Products.md`
   now carry implementation-backed business, operations, developer, and sales/client-demo truth
   for the transaction-ledger source product,
5. source-owner proof passed locally with focused transaction-ledger service tests, documentation
   guards, `make source-data-product-contract-guard`, `make openapi-gate`, and `git diff --check`,
6. GitHub PR Merge Gate passed workflow lint, lint/typecheck/contracts/security, unit, unit-db,
   integration-lite, ops-contract, transaction contract tests, coverage, docker build,
   docker smoke, E2E smoke, latency, and fast performance gates,
7. this advances RFC42-WTBD-006 but does not close it: row-level ledger evidence is not aggregated
   tax methodology, FX attribution, cash movement aggregation, transaction-cost methodology,
   execution-quality assessment, OMS acknowledgement, or client advice.

Latest WTBD-006 core realized-FX reporting-currency evidence proof:

1. `lotus-core` now restates explicit row-level `realized_capital_pnl_local`,
   `realized_fx_pnl_local`, and `realized_total_pnl_local` values into reporting-currency fields
   when `reporting_currency` is supplied on `TransactionLedgerWindow:v1`,
2. the API contract documents `realized_fx_pnl_local_reporting_currency` as row-level source
   evidence rather than portfolio-level FX attribution,
3. `docs/methodologies/source-data-products/transaction-ledger-window.md` now records the
   `FX_report = FX_local * X_trade` methodology, supported field set, validation behavior, and
   worked example for explicit realized FX P&L local evidence,
4. `docs/architecture/RFC-0083-source-data-product-catalog.md` and
   `wiki/Mesh-Data-Products.md` now carry the source-boundary update for business, operations,
   developer, and sales/client-demo audiences,
5. focused proof passed locally in `lotus-core` with `20` tests:
   `python -m pytest tests/unit/services/query_service/services/test_transaction_service.py tests/integration/services/query_service/test_main_app.py::test_openapi_describes_transaction_filters_and_not_found_examples tests/unit/docs/test_source_data_product_boundaries.py -q`,
6. `python -m ruff check` and `python -m ruff format --check` passed for the touched service,
   DTO, API-doc, methodology, and source-boundary files,
7. this advances RFC42-WTBD-006 but does not close it: realized FX P&L remains row-level
   source-owned evidence; aggregated FX attribution, cash movement methodology, client tax,
   execution methodology, and OMS acknowledgement remain future owner work. A later
   `PortfolioLiquidityLadder:v1` source-owner slice now covers operational liquidity buckets.

Latest WTBD-006 core field-aware transaction-ledger restatement proof:

1. `lotus-core` PR #359 (`ab1fea9e`) corrects `TransactionLedgerWindow:v1`
   reporting-currency restatement so book-currency fields use `record.currency` while trade/local
   fields use `record.trade_currency` when present, falling back to book currency only when trade
   currency is absent,
2. canonical front-office seeding now publishes USD/SGD, SGD/USD, EUR/SGD, and SGD/EUR FX rates
   alongside EUR/USD pairs so SGD reporting-currency evidence is executable for
   `PB_SG_GLOBAL_BAL_001`,
3. the source-data methodology, OpenAPI descriptions, source-data product catalog, README,
   repository context, docs guards, and `wiki/Mesh-Data-Products.md` were updated so this behavior
   is durable product truth and not only implementation behavior,
4. focused local proof in `lotus-core` passed with `92` tests across transaction service,
   OpenAPI-description, source-data-boundary, and front-office seed coverage; `ruff`, format check,
   `make openapi-gate`, `make api-vocabulary-gate`, `make source-data-product-contract-guard`, and
   `git diff --check` also passed,
5. live proof passed after targeted `query_service` refresh and canonical reseed:
   `TransactionLedgerWindow:v1` returned `29` rows, `dataQuality=COMPLETE`, and EUR trade-fee rows
   restated through EUR/SGD; `npm run live:validate` in `lotus-workbench` passed with `31` API
   checks, `12` screenshots, `19` UI checks, `0` console errors, and `17/17` panels ready,
6. log review after the passing run found no Gateway or core query `ERROR`, `CRITICAL`, traceback,
   or `5xx` entries in the final validation window,
7. this advances RFC42-WTBD-006 but does not close it: the fixed behavior is source-owned
   row-level transaction-ledger evidence, not aggregated portfolio FX attribution, client-tax
   advice, execution-quality assessment, OMS acknowledgement, or PM scoring.

Latest WTBD-006 canonical current-horizon cashflow and liquidity proof:

1. `lotus-core` PR #360 was merged to `main` as
   `e83f0c85ac0bdaa738af831a8224709e1b29a7fd` and the repo-local wiki was published to
   `lotus-core.wiki` commit `3956cb6`,
2. canonical front-office seeding now includes deterministic current-horizon projected withdrawal
   `TXN-WITHDRAWAL-CURRENT-HORIZON-001` for `PB_SG_GLOBAL_BAL_001`, with transaction date
   `2026-04-30`, settlement date `2026-05-16`, and USD `12,000` withdrawal evidence so the current
   Workbench liquidity horizon exercises non-zero projected settlement cashflow,
3. focused local source-owner proof in `lotus-core` passed with
   `python -m pytest tests/unit/tools/test_front_office_portfolio_seed.py tests/unit/services/query_service/services/test_liquidity_ladder_service.py -q`
   returning `51 passed`, and `git diff --check` passed,
4. GitHub Feature Lane and PR Merge Gate passed workflow lint, lint/typecheck/contracts/security,
   unit, unit-db, integration-lite, ops-contract, transaction contract tests, coverage, docker
   build, docker smoke, E2E smoke, latency, and fast performance gates,
5. live Core proof after canonical reseed showed
   `PortfolioCashflowProjection:v1` returning `projected_settlement_total_cashflow=-12000` and
   `total_net_cashflow=-12000` for `as_of_date=2026-05-08`, `horizon_days=30`,
   `include_projected=true`,
6. live Gateway proof showed
   `/api/v1/portfolio/portfolios/PB_SG_GLOBAL_BAL_001/liquidity` returning
   `cashflow_outlook.total_net_cashflow_base=-12000.0`, no warnings, and no partial failures, and
   `npm run live:validate` in `lotus-workbench` passed against the canonical stack,
7. log review found successful Gateway/Core query responses and no sampled `ERROR`, `CRITICAL`,
   traceback, or `5xx` entries in the final validation window; the Core aggregation backlog stayed
   visible as `AGGREGATION_BACKLOG_OPEN` and was not hidden or weakened,
8. this advances RFC42-WTBD-006 but does not close it: the seeded current-horizon event proves
   operational projected cashflow and liquidity-ladder behavior for the canonical front-office
   portfolio; it is not client income-needs planning, funding advice, execution forecasting,
   OMS acknowledgement, or PM scoring.

Latest WTBD-006 core portfolio-tax-lot methodology proof:

1. `lotus-core` PR #346 was merged to `main` as
   `e48d85a98ae3f53199bdccbe2e83f6304c9e050c` and the repo-local wiki was published to
   `lotus-core.wiki` commit `f37af67`,
2. `docs/methodologies/source-data-products/portfolio-tax-lot-window.md` now records the
   implemented `PortfolioTaxLotWindow:v1` methodology with endpoint mode coverage, inputs,
   upstream source tables, unit conventions, variable dictionary, formulas, deterministic steps,
   validation/failure behavior, configuration options, outputs, and a worked example,
3. the methodology pins `acquisition_date <= as_of_date` lot selection, optional `security_ids`
   filtering, open/closed lot filtering, default open-lot behavior, deterministic
   `(acquisition_date, lot_id)` paging, `OPEN` versus `CLOSED` status derivation from open
   quantity, cost-basis field preservation without reallocation, and empty full-portfolio
   source-evidence supportability as `UNAVAILABLE` / `TAX_LOTS_EMPTY` / `MISSING`,
4. `docs/architecture/RFC-0083-source-data-product-catalog.md` and `wiki/Mesh-Data-Products.md`
   now carry implementation-backed business, operations, developer, and sales/client-demo truth
   for the tax-lot window source product,
5. source-owner proof passed locally with focused tax-lot service tests, documentation guards,
   `make source-data-product-contract-guard`, `make openapi-gate`, and `git diff --check`,
6. GitHub PR Merge Gate passed workflow lint, lint/typecheck/contracts/security, unit, unit-db,
   integration-lite, ops-contract, transaction contract tests, coverage, docker build,
   docker smoke, E2E smoke, latency, and fast performance gates,
7. this advances RFC42-WTBD-006 but does not close it: source-owned tax lots preserve lot and
   cost-basis evidence for downstream consumption, but they are not jurisdiction-specific tax
   advice, realized-tax optimization, wash-sale treatment, client-tax approval, tax-reporting
   certification, predictive execution methodology, or OMS acknowledgement.

Latest WTBD-006 client tax-profile and tax-rule source-product proof:

1. `lotus-core` PR #361 was merged to `main` as
   `ec75ddfcd77dd38629d06d2e2ce53d5830023f73` and the repo-local wiki was published to
   `lotus-core.wiki` commit `2f47f65`,
2. `lotus-core` is the Lotus-side owner for `ClientTaxProfile:v1` and `ClientTaxRuleSet:v1`
   products because client/portfolio reference data, booking jurisdiction, tax lots, transaction
   evidence, and source-readiness composition already belong in Core,
3. deployed banks may map external tax/reference systems into those Core products; Lotus does not
   need a separate tax application for the current WTBD decision,
4. `lotus-manage` may consume these products for bounded tax-aware construction, proof-pack, and
   outcome-review supportability, but must not claim tax advice, after-tax optimization, legal
   interpretation, tax-loss harvesting suitability, client-tax approval, or jurisdiction-specific
   recommendation,
5. Core publishes contracts, supportability states, examples, tests, source-owner methodology docs,
   OpenAPI route-family governance, source-product catalog/security profiles, and explicit
   non-claims for profile/rule evidence.

Latest WTBD-006 core portfolio-realized-tax-summary methodology proof:

1. `lotus-core` PR #363 was merged to `main` as
   `a349dc0cefc2d254c539d240073f5a5aa44a0a00` and the repo-local wiki was published to
   `lotus-core.wiki` commit `1170afd`,
2. `lotus-platform` PR #331 was merged to `main` as
   `500a1b83dddb85842b79e6218595bd13f237d949`, mirroring
   `PortfolioRealizedTaxSummary:v1` into platform domain-product discovery, certification,
   dependency-graph, and enterprise-mesh maturity artifacts,
3. `docs/methodologies/source-data-products/portfolio-realized-tax-summary.md` now records the
   implemented `PortfolioRealizedTaxSummary:v1` methodology for explicit realized tax evidence,
   including upstream transaction fields, withholding-tax and other-interest-deduction aggregation
   by ledger currency, optional reporting-currency restatement through Core FX rates, validation
   behavior, supportability posture, outputs, and a worked example,
4. `GET /portfolios/{portfolio_id}/realized-tax-summary` is the source-owned Core API for
   portfolio-level realized tax evidence. Manage and other consumers may reference it as bounded
   evidence without calculating tax methodology locally,
5. local source-owner proof passed with `2033` unit tests plus focused router, service,
   repository, DTO, source-data product, security, OpenAPI, vocabulary, contract, and wiki drift
   checks; GitHub Feature Lane and PR Merge Gate passed for the Core PR,
6. this advances RFC42-WTBD-006 by closing the Lotus-side portfolio-level realized-tax aggregation
   source-product gap, but it does not create tax advice, after-tax optimization, tax-loss
   harvesting suitability, jurisdiction-specific recommendation, client-tax approval,
   tax-reporting certification, portfolio-level FX attribution, predictive execution, or OMS
   acknowledgement support.

Latest WTBD-006 core portfolio-cash-movement-summary methodology proof:

1. `lotus-core` PR #364 was merged to `main` as
   `486136affef18d7c9d51886be1d52a804cfd2867` and the repo-local wiki was published to
   `lotus-core.wiki` commit `ad67cf6`,
2. `docs/methodologies/source-data-products/portfolio-cash-movement-summary.md` now records the
   implemented `PortfolioCashMovementSummary:v1` methodology for source-owned signed cash
   movement bucket evidence, including latest-cashflow-row selection per transaction, grouping by
   classification, timing, currency, position-flow, and portfolio-flow posture, signed totals,
   movement direction, data-quality posture, evidence timestamp, and source fingerprint,
3. `GET /portfolios/{portfolio_id}/cash-movement-summary` is the source-owned Core API for
   portfolio-level operational cash movement evidence. Manage and other consumers may reference
   it as bounded evidence without aggregating cashflows locally,
4. local source-owner proof passed with `2043` tests plus focused service, repository, router,
   DTO, source-data product, security, OpenAPI, vocabulary, contract, source-boundary, and wiki
   drift checks; GitHub Feature Lane and PR Merge Gate passed for the Core PR,
5. this advances RFC42-WTBD-006 by closing the Lotus-side signed cash movement aggregation source
   product gap, but it does not create cashflow forecasting, liquidity advice, income-needs
   planning, funding recommendation, treasury instruction, tax methodology, predictive execution,
   execution-quality assessment, or OMS acknowledgement support.

Latest WTBD-006 core transaction-cost-curve methodology proof:

1. `lotus-core` PR #345 was merged to `main` as
   `83d791d0e599f06a2c0caab6eaba647f717d4658` and the repo-local wiki was published to
   `lotus-core.wiki` commit `154ae27`,
2. `docs/methodologies/source-data-products/transaction-cost-curve.md` now records the implemented
   `TransactionCostCurve:v1` methodology with endpoint mode, upstream source tables, unit
   conventions, variable dictionary, formulas, deterministic steps, validation/failure behavior,
   configuration options, outputs, and a worked example,
3. the methodology pins observed booked-fee aggregation by
   `(security_id, transaction_type, currency)`, `transaction_costs` precedence over `trade_fee`,
   zero-fee and zero-notional exclusion, notional-weighted average bps, min/max bps, deterministic
   paging, and supportability states,
4. `docs/architecture/RFC-0083-source-data-product-catalog.md` and `wiki/Mesh-Data-Products.md`
   now carry implementation-backed business, operations, developer, and sales/client-demo truth
   for the observed transaction-cost curve source product,
5. source-owner proof passed locally with focused transaction-cost curve service tests, docs tests,
   integration/router tests, `make source-data-product-contract-guard`, `make openapi-gate`, and
   `git diff --check`,
6. GitHub PR Merge Gate passed workflow lint, lint/typecheck/contracts/security, unit, unit-db,
   integration-lite, ops-contract, transaction contract tests, coverage, docker build,
   docker smoke, E2E smoke, latency, and fast performance gates,
7. this advances RFC42-WTBD-006 but does not close it: observed booked-fee evidence is not a
   predictive execution quote, market-impact model, venue-routing model, best-execution
   certification, OMS acknowledgement, or true min-cost execution methodology.

Latest WTBD-006 core holdings-as-of methodology proof:

1. `lotus-core` PR #348 was merged to `main` as
   `0a8785e0a4be7ea737b40eded07bd9c7f8002f25` and the repo-local wiki was published to
   `lotus-core.wiki` commit `2a428eb`,
2. `docs/methodologies/source-data-products/holdings-as-of.md` now records the implemented
   `HoldingsAsOf:v1` methodology with endpoint modes, upstream source tables, variable
   dictionary, formulas, deterministic steps, validation/failure behavior, output contract
   semantics, worked examples, and downstream no-reconstruction posture,
3. the methodology covers `GET /portfolios/{portfolio_id}/positions` and
   `GET /portfolios/{portfolio_id}/cash-balances`, including booked holdings, explicit as-of
   holdings, projected-inclusive holdings, cash-balance reads, explicit as-of cash balances,
   reporting-currency cash balances, snapshot-versus-history fallback, position weights, and cash
   reporting-currency conversion,
4. it records supportability for missing portfolio, missing business date, missing FX, empty
   holdings, missing state, stale state, stale market price, history supplement fallback, complete
   snapshot-backed holdings, and cash-balance evidence,
5. `docs/architecture/RFC-0083-source-data-product-catalog.md` and `wiki/Mesh-Data-Products.md`
   now carry implementation-backed business, operations, developer, and sales/client-demo truth
   for the holdings-as-of source product,
6. merged-main source-owner proof passed with focused docs guards, position-service tests,
   cash-balance service tests, `make source-data-product-contract-guard`, and wiki check-only
   diff count `0`,
7. this advances RFC42-WTBD-006 but does not close it: source-owned holdings and cash-balance
   methodology does not claim liquidity ladders, income-needs planning, performance returns, risk
   exposure methodology, tax advice, execution quality, or OMS acknowledgement.

Latest WTBD-006 core market-data coverage methodology proof:

1. `lotus-core` PR #349 was merged to `main` as
   `4101f1ba321b8464093c12358e57f5c448440413` and the repo-local wiki was published to
   `lotus-core.wiki` commit `9be04cc`,
2. `docs/methodologies/source-data-products/market-data-coverage-window.md` now records the
   implemented `MarketDataCoverageWindow:v1` methodology with endpoint inputs, upstream source
   tables, variable dictionary, formulas, deterministic steps, validation/failure behavior, output
   contract semantics, worked examples, and downstream no-reconstruction posture,
3. the methodology covers `POST /integration/market-data/coverage`, including price coverage by
   `instrument_ids`, FX coverage by `currency_pairs`, combined DPM universe readiness, configurable
   `max_staleness_days`, latest observation selection at or before `as_of_date`, and
   valuation-currency context,
4. it records supportability for missing price rows, missing FX rows, stale price rows, stale FX
   rows, complete fresh coverage, partial coverage, and empty request universes,
5. `docs/architecture/RFC-0083-source-data-product-catalog.md` and `wiki/Mesh-Data-Products.md`
   now carry implementation-backed business, operations, developer, and sales/client-demo truth
   for the market-data coverage source product,
6. merged-main source-owner proof passed with focused docs guards, market-data coverage service
   tests, `make source-data-product-contract-guard`, `make openapi-gate`, and wiki check-only
   diff count `0`,
7. this advances RFC42-WTBD-006 but does not close it: source-owned market-data coverage confirms
   price and FX freshness posture but does not claim valuation methodology, FX attribution,
   liquidity ladders, cash forecasts, market impact, execution quality, best execution, venue
   routing, or OMS acknowledgement.

Latest WTBD-006 core DPM source-readiness methodology proof:

1. `lotus-core` PR #350 was merged to `main` as
   `c17bfa3298470375faa0b5e15bf369fa88a70597` and the repo-local wiki was published to
   `lotus-core.wiki` commit `e3fd859`,
2. `docs/methodologies/source-data-products/dpm-source-readiness.md` now records the implemented
   `DpmSourceReadiness:v1` methodology with endpoint inputs, source-product dependencies,
   variable dictionary, deterministic formulas, validation/failure behavior, output contract
   semantics, worked examples, and downstream no-reconstruction posture,
3. the methodology covers `POST /integration/portfolios/{portfolio_id}/dpm-source-readiness`,
   including mandate binding, model portfolio target selection, eligibility profile checks,
   tax-lot coverage, market-data coverage, deterministic instrument universe assembly, and
   fail-closed source-family precedence,
4. it records supportability for unavailable, incomplete, degraded, and ready source-family
   combinations, plus the precise `data_quality_status` mapping used by downstream DPM consumers,
5. `docs/architecture/RFC-0083-source-data-product-catalog.md` and `wiki/Mesh-Data-Products.md`
   now carry implementation-backed business, operations, developer, and sales/client-demo truth
   for the DPM source-readiness source product,
6. merged-main source-owner proof passed with focused docs guards, DPM source-readiness service
   tests, `make source-data-product-contract-guard`, `make openapi-gate`, and wiki check-only
   diff count `0`,
7. this advances RFC42-WTBD-006 but does not close it: source-owned DPM readiness confirms whether
   a populated DPM run has the required source families, but does not claim mandate approval,
   client suitability, tax advice, portfolio valuation, FX attribution, liquidity ladders,
   execution quality, best execution, venue routing, or OMS acknowledgement.

Latest WTBD-006 performance-contribution tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-performance-contribution-proof/20260506-074309/critical-review.json`,
2. `tests/unit/core/test_performance_realized_outcome_sources.py` passed with `19` tests,
3. tests cover source-owned total contribution, total portfolio return, summary FX contribution,
   ready snapshot assembly, stale/degraded source-owner posture, errored source blocking posture,
   and missing ready-value guardrails,
4. repo-native `make check` passed with `896` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, no-alias, domain-data-product, trust telemetry, observability, and
   monetary-float guardrails before PR #97 merge,
5. manage preserves `lotus-performance` calculation id, calculation hash, supportability truth,
   input mode, selected contribution measure, and percentage-point to ratio unit conversion, and
   performs no position, daily, hierarchy, local/FX, benchmark-relative, or attribution calculation
   locally.

Latest WTBD-006 performance-attribution tightening proof:

1. local critical review evidence:
   `output/rfc0042-wtbd006-performance-attribution-proof/20260506-075838/critical-review.json`,
2. `tests/unit/core/test_performance_realized_outcome_sources.py` passed with `26` tests,
3. tests cover source-owned active-return reconciliation, level total effect, currency total
   effect, ready snapshot assembly, stale/degraded source-owner posture, errored source blocking
   posture, and missing ready-value guardrails,
4. repo-native `make check` passed with `903` unit tests, lint, format, mypy, OpenAPI quality,
   API vocabulary, no-alias, domain-data-product, trust-telemetry, observability, and
   monetary-float guardrails,
5. manage preserves `lotus-performance` calculation id, calculation hash, supportability truth,
   input mode, attribution model, linking method, benchmark context, selected attribution measure,
   and percentage-point to ratio unit conversion, and performs no group-row summing, active-return,
   allocation, selection, interaction, residual, currency-effect, benchmark-selection, or
   attribution calculation locally.

Latest WTBD-006 performance MWR source-truth proof:

1. `lotus-performance` PR #144 was merged to `main` as
   `37e125b6525e87a31a84b46e68f8c2939855edcd`; the merged source-owner slice tightens
   `docs/methodologies/metrics/metric-mwr-xirr.md`,
   `docs/methodologies/metrics/metric-mwr-dietz.md`, and
   `docs/methodologies/metrics/master-index.md` so MWR methodology truth covers both stateless
   caller-owned inputs and stateful lotus-core source resolution,
2. the source-owner methodology docs now describe `stateful_input.window_start_date`,
   `CORE_CONTROL_PLANE_BASE_URL`, cross-observation carry-forward capital adjustments, fee-row
   exclusion from investor cash flows, resolved start-date behavior, `cashflows_used`,
   `calculation_supportability`, and downstream no-reconstruction posture,
3. `lotus-performance` wiki source `wiki/Integrations.md` now includes a Mermaid source-flow
   diagram from lotus-core timeseries through performance MWR normalization, engine execution,
   Gateway contract consumption, and Workbench investor capital-timing display,
4. focused documentation proof passed with `43` tests:
   `python -m pytest tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py -q`,
5. implementation-backed proof passed with `41` MWR engine/service/integration tests:
   `python -m pytest tests/unit/engine/test_mwr.py tests/unit/services/test_mwr_mode_service.py tests/unit/services/test_workspace_summary_service.py tests/integration/test_mwr_api.py tests/integration/test_response_attribute_certification.py -q`,
6. `python -m ruff check tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py`
   and `git diff --check` passed before merge; repo-local wiki source was published after merge
   through the governed wiki-publication flow.

Latest WTBD-006 performance contribution source-truth proof:

1. `lotus-performance` PR #145 was merged to `main` as
   `7aa83fe5eda49916d5a2afa59151bb49dc056652`; the merged source-owner slice tightens
   `docs/methodologies/metrics/metric-contribution-total.md`,
   `metric-contribution-local.md`, `metric-contribution-fx.md`, and
   `docs/methodologies/metrics/master-index.md` so contribution methodology truth covers stateless
   caller-owned inputs and stateful lotus-core portfolio/position timeseries normalization,
2. the source-owner methodology docs now describe `stateful_input.metric_basis`,
   `stateful_input.dimensions`, `stateful_input.include_cash_flows`, source filters,
   portfolio/position retrieval, source currency metadata, FX requirements for mixed-currency
   stateful contribution, `calculation_supportability`, and downstream no-reconstruction posture,
3. `lotus-performance` wiki source `wiki/Integrations.md` now includes a Mermaid source-flow
   diagram from lotus-core portfolio and position timeseries through performance contribution
   normalization, total/local/FX contribution execution, and downstream Gateway, Workbench, risk,
   and reporting consumption,
4. focused documentation proof passed with `44` tests:
   `python -m pytest tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py -q`,
5. implementation-backed proof passed with `48` contribution stateful/service/integration tests:
   `python -m pytest tests/unit/services/test_stateful_contribution_input_service.py tests/integration/test_contribution_api.py -q`,
6. `git diff --check` passed before merge; repo-local wiki source was published after merge
   through the governed wiki-publication flow.

Latest WTBD-006 performance attribution source-truth proof:

1. `lotus-performance` PR #146 was merged to `main` as
   `817c5bbc6c2b0ca03b6de5eaafa8ace81def81b2`; the merged source-owner slice tightens
   `docs/methodologies/metrics/metric-attribution-active-return.md`,
   `metric-attribution-allocation.md`, `metric-attribution-selection.md`,
   `metric-attribution-interaction.md`, and the four `metric-currency-*.md` methodology docs so
   attribution methodology truth covers stateless caller-owned inputs and stateful lotus-core
   portfolio/position, benchmark, and source-currency normalization,
2. the source-owner methodology docs now describe stateful portfolio/position retrieval,
   benchmark assignment or explicit benchmark override, benchmark component sourcing through the
   shared benchmark engine path, source currency and FX evidence, supportability metadata, and
   downstream no-reconstruction posture for allocation, selection, interaction, active return, and
   Karnosky-Singer currency effects,
3. `lotus-performance` wiki source `wiki/Integrations.md` now includes a Mermaid source-flow
   diagram from lotus-core portfolio, position, benchmark, and FX evidence through performance
   attribution normalization, Brinson/Karnosky-Singer execution, and downstream Gateway,
   Workbench, risk, and reporting consumption,
4. focused documentation proof passed with `45` tests:
   `python -m pytest tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py -q`,
5. implementation-backed proof passed with `46` attribution stateful/service/integration tests:
   `python -m pytest tests/unit/services/test_stateful_attribution_input_service.py tests/unit/services/test_attribution_mode_service.py tests/integration/test_attribution_api.py -q`,
6. `python -m ruff check tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py`,
   `python -m ruff format --check tests/unit/docs/test_metric_methodology_docs.py tests/unit/docs/test_public_docs_contract.py`,
   and `git diff --check` passed before merge; repo-local wiki source was published after merge
   through the governed wiki-publication flow.

Latest WTBD-006 performance RFC-046 TWR live-audit proof:

1. `lotus-performance` PR #156 was merged to `main` as `bf173b4`; RFC-046 TWR daily calculation
   evidence, denominator/linkability/episode semantics, source-quality supportability,
   benchmark FX/calendar evidence, Gateway/Workbench consumer realization, wiki productization,
   and supported-feature boundaries are implementation-backed on merged mainline truth,
2. focused local proof on 2026-05-10 passed with `48` tests:
   `python -m pytest tests/unit/app/test_twr_openapi_contract.py tests/unit/models/test_responses_models.py tests/unit/docs/test_public_docs_contract.py -q`,
3. live canonical TWR inspection passed through
   `python scripts/validate_canonical_twr_inspection.py --performance-base-url http://127.0.0.1:8002 --core-control-plane-base-url http://127.0.0.1:8202`;
   it returned `supportable_with_warnings` with only the allowed canonical warning codes
   `WEEKEND_OBSERVATIONS_PRESENT` and `MONTHLY_RETURN_DAY_DOMINANCE_DETECTED`,
4. direct live `POST /performance/twr` / result polling for `PB_SG_GLOBAL_BAL_001`, `YTD`,
   `NET`, `include_benchmark=true`, and as-of `2026-04-10` returned calculation
   `9c448568-f2a7-4a3f-8570-f7189d3390b0`, supportability `ready` /
   `calculation_complete`, net TWR `-0.6917915976265676%`, benchmark
   `5.095680231948784%`, active return `-5.7874718295753524%`, `100` daily rows,
   `4` monthly rows, and benchmark calendar posture `partial_overlap` /
   `BENCHMARK_CALENDAR_GAP`,
5. Gateway performance summary/details returned current canonical workspace evidence with
   `2026-05-08` latest performance evidence, supported evidence view, `-0.691792%` net TWR,
   `-0.671493%` gross TWR, `6.997327%` benchmark return, `-7.689119%` active return,
   `-1.926818%` MWR, contribution total `-0.691791%`, attribution active return
   `-7.016227%`, explicit `performance=stale` and `benchmark=stale` input freshness for the
   `2026-05-10` Workbench as-of date, and complete execution/artifact lineage,
6. performance and gateway log review over the live-audit window found no `ERROR`, `CRITICAL`,
   traceback, or `5xx` entries,
7. this advances RFC42-WTBD-006 but does not close it: the source-owned performance evidence is
   production-grade for the implemented TWR/MWR/contribution/attribution source families, while
   client tax, broader FX methodology outside performance-owned Karnosky-Singer attribution totals,
   income-needs planning, predictive execution, OMS acknowledgements, and PM scoring remain
   future source-owner work. `lotus-performance` PR #164 (`cbda83f`, wiki `f76a954`) adds
   source-owned portfolio-level `currency_attribution_totals` for the implemented performance
   attribution path.

Latest WTBD-006 risk/performance issuer active-risk proof:

1. `lotus-performance` PR #165 was merged to `main` as `191a405` and published wiki commit
   `46a9124`; it ungates `ISSUER` for `POST /integration/benchmarks/exposure-context`, maps
   issuer rows from lotus-core index-catalog `classification_labels.issuer_id` and `issuer_name`,
   updates integration capability copy and API vocabulary, and keeps lotus-core as the benchmark
   composition/classification system of record,
2. performance local proof passed `make lint`, `make typecheck`, `make openapi-gate`,
   `make api-vocabulary-gate`, `make domain-product-validate`, `make no-alias-gate`, focused
   endpoint/doc tests with `88` passed, and `make test-unit` with `1270` passed; GitHub Feature
   Lane and PR Merge Gate were green before merge,
3. `lotus-risk` PR #138 was merged to `main` as `8ae3e4a` and published wiki commit `616a10c`;
   it enables stateful `ACTIVE_RISK + ISSUER` historical attribution by consuming
   lotus-performance benchmark exposure context issuer rows and publishes an empty
   `stateful_active_risk_gated_grouping_dimensions` list,
4. risk local proof passed `make lint`, `make no-alias-gate`, `make typecheck`,
   `make openapi-gate`, `make api-vocabulary-gate`, `make domain-data-product-gate`,
   `make test-unit` with `358` passed, `make test-integration` with `80` passed and `14`
   skipped, `make test-e2e` with `24` passed, `make test-pyramid-gate`, and the final GitHub
   Feature Lane and PR Merge Gate were green before merge,
5. manage consumes this as source-owner truth for outcome-review and proof-pack posture only: no
   benchmark issuer exposure, active-risk decomposition, covariance, tracking-error,
   issuer-enrichment, or benchmark classification logic is implemented or duplicated in manage,
6. this advances RFC42-WTBD-006 but does not close it: broader FX methodology beyond
   performance-owned Karnosky-Singer totals, predictive execution, OMS acknowledgements,
   income-needs planning, financial-planning advice, tax advice, tax optimization, and broader
   live portfolio-archetype validation remain source-owner or future-RFC work.

Latest WTBD-006 performance currency-attribution fail-closed proof:

1. `lotus-performance` PR #166 was merged to `main` as `643226d` and published wiki commit
   `a48035b`; it tightens source-owned Karnosky-Singer currency-attribution evidence so
   `currency_attribution_status` is `complete` only when `currency_mode=BOTH`, required local/FX
   columns are present, and the request includes the `currency` grouping key,
2. the same prerequisite check now gates both supportability status and emitted
   `currency_attribution` / `currency_attribution_totals`, so downstream consumers receive
   `currency_attribution_unavailable` instead of a false complete posture when no currency bucket
   can be emitted,
3. performance local proof passed focused attribution/docs tests, `make lint`, `make typecheck`,
   `make openapi-gate`, `make api-vocabulary-gate`, `make no-alias-gate`,
   `make domain-product-validate`, `make test-unit`, `make test-integration`, `make test-e2e`,
   platform context validators, migration smoke, security audit, coverage gate, Docker build, and
   the final GitHub Feature Lane and PR Merge Gate before merge,
4. manage consumes this as source-owner supportability truth only: no Karnosky-Singer, FX
   attribution, local/FX return, benchmark-currency, or portfolio-level currency-effect
   calculation is implemented or duplicated in manage,
5. this advances RFC42-WTBD-006 but does not close it: broader FX methodology beyond the
   implemented performance attribution path, predictive execution, OMS acknowledgements,
   income-needs planning, tax advice, tax optimization, and broader live portfolio-archetype
   validation remain source-owner or future-RFC work.

Latest WTBD-006 performance currency-attribution totals aggregation proof:

1. `lotus-performance` PR #167 was merged to `main` as `16261c9` and published wiki commit
   `41bdaa3`; it tightens source-owned portfolio-level `currency_attribution_totals` so grouped
   attribution requests that include `currency` plus another dimension recompute a date/currency
   panel from summed weights and weight-averaged local/FX returns before applying Karnosky-Singer
   formulas,
2. the regression proves totals are invariant when a caller requests `group_by=["currency",
   "sector"]` rather than only `currency`, preventing visible-row granularity from distorting
   portfolio-level FX attribution evidence,
3. performance local proof passed focused attribution/docs tests, `make lint`, `make typecheck`,
   `make openapi-gate`, `make api-vocabulary-gate`, `make domain-product-validate`,
   `make no-alias-gate`, `make test-unit`, and full `make ci` including migration smoke,
   dependency/security audit with zero known vulnerabilities, unit/integration/e2e, coverage, and
   Docker; GitHub Feature Lane and PR Merge Gate were green before merge,
4. manage consumes this as source-owner methodology truth only: no Karnosky-Singer, FX
   attribution, local/FX return, benchmark-currency, or portfolio-level currency-effect
   calculation is implemented or duplicated in manage,
5. this advances RFC42-WTBD-006 but does not close it: broader FX methodology beyond the
   implemented performance attribution path, predictive execution, OMS acknowledgements,
   tax advice, tax optimization, and broader live portfolio-archetype validation remain
   source-owner or future-RFC work.

Latest WTBD-006 performance MWR source-preconverted FX-evidence proof:

1. `lotus-performance` PR #168 was merged to `main` as
   `781415f9b5a442a9afbb0b7034e8bd28cc76343c` and published wiki commit `6fb7209`;
   it adds stateless `source_preconverted_fx_evidence` to MWR requests and preserves
   per-market-value and per-cashflow source amount/currency, reporting amount/currency, FX rate,
   FX pair, rate date, source, version, conversion policy, timestamp, and fingerprint evidence,
2. the source-owner MWR service validates that source-preconverted evidence is complete and
   internally consistent, failing closed for missing beginning/ending market-value evidence,
   mismatched cashflow counts or dates, reporting amount or currency mismatches, same-currency
   non-1 FX rates, and blank source/policy/version/fingerprint fields,
3. stateless MWR responses now emit `currency_mode="SOURCE_PRECONVERTED_WITH_FX_EVIDENCE"` and
   `conversion_evidence_status="complete_source_preconverted_fx_metadata"` when caller-supplied
   preconverted inputs include complete FX metadata,
4. stateful MWR remains single-reporting-currency with
   `upstream_preconverted_missing_per_input_fx_metadata`; `lotus-performance` still does not
   convert FX inside the MWR engine and computes over one reporting-currency schedule only,
5. performance proof passed focused MWR integration/OpenAPI/docs tests, unit/integration/e2e
   suites, lint, typecheck, OpenAPI gate, API vocabulary gate, no-alias gate, domain-product
   validation, platform context validators, wiki drift check/publish, Feature Lane, PR Merge Gate,
   Docker validation, and Main Releasability Gate
   `https://github.com/sgajbi/lotus-performance/actions/runs/26135968611`,
6. manage consumes this as source-owner evidence truth only: no MWR FX conversion,
   FX-rate sourcing, FX attribution, reporting-currency restatement, or mixed-currency capital
   timing methodology is implemented or duplicated in Manage,
7. this advances RFC42-WTBD-006 but does not close it: stateful upstream per-input FX conversion
   evidence, broader FX methodology outside implemented performance-owned paths, predictive
   execution, OMS acknowledgements, tax advice, tax optimization, and broader live
   portfolio-archetype validation remain source-owner or future-RFC work.

#### RFC42-WTBD-007 - External Execution / OMS Integration And Acknowledgements

Target business outcome:

Outcome reviews can include governed execution status, acknowledgement, rejection, cancellation,
settlement, and reconciliation facts from an execution/OMS owner.

Why it cannot be done now:

Bank-owned execution/OMS ingestion is not established. RFC-0041 deliberately stopped at internal
operations handoff evidence, and RFC-0042 must not invent execution truth. The current Lotus-side
contract is intentionally fail-closed: `lotus-core` owns the
`ExternalOrderExecutionAcknowledgement:v1` source-product posture and Manage consumes it only as
blocked evidence.

2026-05-12 boundary-hardening result:

The upstream RFC-0041 wave report-input seam now refuses to emit report input when persisted wave
handoff evidence contains an external execution claim. Outcome review can continue to consume
manage-owned internal handoff and expected-snapshot evidence, but OMS acknowledgement remains an
explicit future owner contract. This prevents downstream outcome, report, archive, and AI flows
from treating contaminated manage handoff evidence as execution truth.

2026-05-17 fail-closed source-consumer result:

`lotus-core` `ExternalOrderExecutionAcknowledgement:v1` exposes external OMS acknowledgement
posture as `UNAVAILABLE` until bank-owned OMS ingestion is certified. Manage consumes that posture
through stateful core sourcing and preserves it in construction authority diagnostics with
acknowledgement count, empty acknowledgement rows, missing data families, blocked capabilities,
lineage, and source hash. This remains evidence only: it is not order generation, venue routing,
best-execution certification, OMS acknowledgement ingestion, fills, settlement, execution-status
certification, or autonomous execution truth.

2026-05-18 realized outcome source-consumer result:

Manage now also preserves the same `ExternalOrderExecutionAcknowledgement:v1` fail-closed posture
as RFC-0042 realized outcome source evidence through
`realized_execution_acknowledgement_source_from_response`. The adapter emits a blocked `EXECUTION_QUALITY` source snapshot with acknowledgement count, missing external OMS data families,
blocked capabilities, source fingerprint, supportability reason, and Core product/version evidence.
The assembled realized snapshot keeps the execution-quality value null and reason-coded
`EXECUTION_EVIDENCE_BLOCKED`, so outcome review evidence can record the source-owned boundary
without promoting OMS acknowledgement, fill, settlement, execution-status, best-execution, venue
routing, or autonomous execution support. Focused proof lives in
`tests/unit/core/test_core_realized_outcome_sources.py`.

2026-05-18 outcome supportability and handoff boundary result:

`GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability` now emits structured
and the `DpmOutcomeReportInput` / `DpmOutcomeAiEvidenceInput` handoff contracts now carry
`DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY` evidence. The boundary is derived from persisted
outcome-review source refs, realized `EXECUTION_QUALITY` supportability reason codes, and dimension
state; it names blocked capabilities, the required future execution/OMS owner, the required
`ExternalOrderExecutionAcknowledgement:v1` source product, acknowledgement-count posture, and a
deterministic content hash. This gives Gateway, Workbench, report, AI, support, and operations
consumers a machine-readable no-OMS boundary without promoting order generation, venue routing,
best-execution certification, OMS acknowledgement ingestion, fill confirmation, settlement, or
execution-status reconciliation. Focused API and handoff proof lives in
`tests/unit/api/test_outcome_reviews_api.py`.

2026-05-18 outcome client-communication boundary result:

`GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability` now emits structured
and the `DpmOutcomeReportInput` / `DpmOutcomeAiEvidenceInput` handoff contracts now carry
`DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY` evidence. The boundary is derived from persisted
outcome-review truth, always projects `client_communication_projected=false` and
`client_approval_projected=false`, names blocked client-contact, client-message-generation,
client-approval, delivery-confirmation, and communication-audit capabilities, identifies the
required future client-communication owner and `ClientCommunicationRecord:v1` source product, and
carries a deterministic content hash. This gives Gateway, Workbench, report, AI, support, and
operations consumers a machine-readable no-client-communication boundary without promoting client contact, client-ready message generation,
client approval, delivery confirmation, or communication audit truth.
Focused API and handoff proof lives in `tests/unit/api/test_outcome_reviews_api.py`
and `tests/unit/core/test_outcome_handoffs.py`.

Dependencies before implementation:

1. execution/OMS owner and API contract,
2. order, acknowledgement, rejection, cancellation, settlement, and reconciliation semantics,
3. maker-checker and entitlement controls,
4. failure/retry/compensation model,
5. manage outcome-review adapter that treats execution as source truth.

Expected implementation wave:

Do not promote beyond fail-closed evidence until the execution owner and control model are
explicit.

Promotion proof:

1. execution-owner API certification,
2. manage integration tests,
3. failure, rejection, cancellation, and reconciliation proof,
4. operational runbook and supportability evidence,
5. supported-feature promotion that names the execution boundary.

#### RFC42-WTBD-008 - PM Operating Quality Framework / Configurable Scoring

Target business outcome:

If a buying bank enables it, outcome evidence could support a governed PM operating quality
framework over process quality without becoming opaque, punitive, or biased. The product may expose
scores, but only through explicit bank configuration, access controls, explainability,
supportability, and non-use posture.

Implementation decision:

PM operating quality policy, configuration, score runs, reason decomposition, access mode,
non-use posture, audit trail, and supportability should be owned by `lotus-manage`. This is a DPM
management workflow product because Manage owns waves, proof packs, construction alternatives,
overrides, handoffs, outcome reviews, and PM activity evidence. `lotus-core` provides PM book,
mandate, portfolio, client/portfolio constraint, region, and source-context evidence.
`lotus-risk` provides risk-breach and risk-response evidence. `lotus-performance` provides
outcome and benchmark-relative evidence. `lotus-ai` may summarize evidence but must not calculate
or own the score.

The default shipped posture should remain scoring disabled, with evidence timeline and quality
indicators available only as non-ranking signals until a bank configures and approves the policy.

2026-05-12 implementation result:

`lotus-manage` now implements the first bounded Manage-owned PM operating quality product through
immutable policy administration at
`PUT /api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}`,
`GET /api/v1/rebalance/pm-operating-quality/policies`, and
`GET /api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}`,
plus score-run preview at `POST /api/v1/rebalance/pm-operating-quality/score-runs/preview`. The
preview route emits `PmOperatingQualityScoreRun:v1` from an explicit inline or persisted bank-owned
`PmOperatingQualityPolicy`, optional persisted outcome-review ids, and source-owned evidence
signals. Scoring remains disabled by default: a disabled policy returns `DISABLED` with no score,
enabled policies fail closed for missing required evidence, and every score returns decomposed
indicator results, bounded reason codes, source refs, content hash, forbidden-use posture, and
correlation evidence. The route family does not create HR, compensation, conduct-enforcement,
autonomous-ranking, AI-generated, risk, performance, execution, tax, or source-owner methodology
claims.

2026-05-14 PM-book materialization result:

`POST /api/v1/rebalance/pm-operating-quality/score-runs/preview` and
`POST /api/v1/rebalance/pm-operating-quality/score-runs` now accept optional `pm_book_scope`.
When supplied, `lotus-manage` resolves the PM scope from lotus-core
`PortfolioManagerBookMembership:v1`, attaches explicit `book_scope_evidence` with source id,
product version, returned portfolio count, source-applied filters, reason codes, and source refs,
and contributes the source-owned book posture as score-run source-quality evidence. The route fails
closed for unavailable, incomplete, degraded, or empty PM-book membership. Manage does not infer PM
book membership, calculate source-owner methodology, or project PM-scoring events into portfolio
memory.

2026-05-14 governance-control result:

Enabled `PmOperatingQualityPolicy` versions now require `governance_approval` evidence covering
bank approval, fairness-review reference, approver/reviewer identifiers, approval/review
timestamps, optional expiry, optional actor entitlement allow-list, and supporting source refs.
Score-run preview/create emits `governance_evidence`, includes governance refs in score-run source
refs and content hash, and fails closed for missing approval, invalid expiry date, expired
approval, or unauthorized actor. This implements first-wave fairness/access governance controls
without calculating protected-class fairness analytics or turning PM quality into HR,
compensation, conduct-enforcement, autonomous-ranking, or AI-generated scoring.

Portfolio memory now publishes `pm_scoring` as `SUPPORTED` with route
`/api/v1/rebalance/pm-operating-quality/score-runs`: PM quality score-run lifecycle is supported
separately, and persisted score runs with source-owned Core PM-book member evidence project
bounded `PM_QUALITY_SCORE_RUN` lineage events for matching portfolios. The projection does not
copy raw score payloads, create portfolio-level rankings, or calculate PM scores locally.

2026-05-14 persisted lifecycle result:

`lotus-manage` now persists immutable PM operating quality score runs through
`POST /api/v1/rebalance/pm-operating-quality/score-runs`, retrieves them through
`GET /api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}`, and lists bounded pages
through `GET /api/v1/rebalance/pm-operating-quality/score-runs`. The score-run body remains the
same content-addressed `PmOperatingQualityScoreRun:v1` emitted by preview; storage is immutable,
Postgres migration-backed, and queryable by PM, book, policy, as-of date, and state. Portfolio
memory now publishes `pm_scoring` as a governed source-event family for bounded score-run lineage
projection. Only persisted score runs with source-owned Core PM-book member evidence are projected
into portfolio memory, and the event metadata deliberately omits numeric scores.

2026-05-16 peer-group and lookback-window scope result:

`PmOperatingQualityPolicy` now supports optional `peer_group_policy` and
`lookback_window_policy` configuration with required source refs. Score-run preview/create
materializes those policies into `scope_evidence`, includes the peer-group and lookback-window refs
in source refs and content hash, and fails closed when dated evidence falls outside the approved
lookback window. This closes the first Manage-owned peer-group/lookback materialization gap without
discovering peers locally, computing source-owner methodology, ranking PMs, or creating HR,
compensation, conduct, approval, client-contact, execution, or OMS decisions.

2026-05-16 AI PM-quality summary result:

`lotus-ai` PR #70 (`1951f62`, wiki `038a1a1`) implements the owner-side
`pm_quality_summary.pack@v1` workflow pack over Manage-owned `PmOperatingQualityScoreRun`
evidence. The pack requires score-run identity, policy/version, PM identity, as-of date, reason
codes, indicator results, source refs, content hash, supportability posture, forbidden-action
guardrails, and optional bounded `portfolio_memory_context`. It returns review-required
support-only summary posture and blocks PM ranking, HR, compensation, conduct, client-contact,
trade approval, execution, OMS, raw payload, sensitive field, and invented-source-fact outputs.
Gateway/Workbench product invocation is implemented for the bounded support-summary surface through
Gateway PR #213 and Workbench PR #245, preserving Manage score-run truth without local scoring or
browser prompt construction.

Implemented first-wave dependency posture:

1. Manage-owned `PmOperatingQualityPolicy` and `PmOperatingQualityScoreRun:v1` models are
   implementation-backed for policy versioning, enablement, weights, thresholds, evidence
   minimums, access purpose, governance approval, fairness-review evidence, actor entitlement,
   non-use posture, score decomposition, source refs, and content hash.
2. The first-wave implementation supports immutable persisted policy versions, explicit
   policy-supplied PM/book scope, optional source-owned PM-book materialization from
   `PortfolioManagerBookMembership:v1`, and bank-defined peer-group/lookback-window scope evidence
   materialized into score-run `scope_evidence`.
3. Bias/fairness controls are enforced first as required bank approval, fairness-review evidence,
   optional expiry, optional actor entitlement, no-hidden-use controls, and no-prohibited-use
   controls: compensation, HR, conduct enforcement, and autonomous decisioning are rejected or
   listed as forbidden. Manage now supports bounded source-segment fairness-analysis preview and
   immutable create/read/list lifecycle across caller-supplied mandate type, region, book profile,
   client constraint profile, market regime, or custom source segments, using persisted score-run
   ids and source refs only. Persisted fairness analyses are content-addressed and returned without
   recomputing score runs or segment posture.
4. Manage now supports immutable review-action preview/create/read/list over existing score-run or
   fairness-analysis evidence, preserving reviewed content hashes, review references, actors,
   source refs, and bounded bank rationale without recalculating scores or recomputing fairness.
5. Explainability, missing-evidence posture, supportability state, reason decomposition, source
   refs, and deterministic content hash are implementation-backed for every indicator.
6. AI remains narrative-only and is not involved in score calculation; `pm_quality_summary.pack@v1`
   is implemented in `lotus-ai` for bounded support-only score-run summaries.

Remaining expansion wave:

1. persisted PM-quality summary history and approval workflow beyond immutable review actions,
2. richer portfolio-memory analytics beyond bounded score-run lineage events,
3. any approval workflow beyond evidence validation, HR/compensation/conduct integration,
   protected-class inference, PM ranking, client-contact, order, OMS, or execution product must
   be owned by explicit future RFCs and remains outside the current support claim.

2026-05-14 Gateway composition result:

`lotus-gateway` PR #213 (`62ce4c4`) implements the PM operating quality BFF route family at
`/api/v1/dpm/command-center/pm-operating-quality/*` for policy list/get/upsert and score-run
preview/create/list/get. Gateway forwards to the Manage
`/api/v1/rebalance/pm-operating-quality/*` source routes, preserves Manage-owned policy
configuration, score-run lifecycle, supportability, governance evidence, source refs, reason
codes, content hashes, and forbidden-use posture, and does not calculate scores, rank PMs,
administer bank policy locally, approve trades, contact clients, route orders, claim execution, or
create HR, compensation, conduct, or autonomous-ranking decisions. Gateway local gates and PR Merge
Gate passed, and Gateway wiki source was published at `a4c9db9` with zero drift.

2026-05-17 Workbench PM-quality product realization result:

`lotus-workbench` PR #245 (`2af063b`, wiki `2ba368d`, Main Releasability Gate `25991445845`)
implements the Gateway-only PM operating quality product surface for policy and score-run evidence,
fairness-analysis preview/create/list/detail, saved-analysis readback, supportability/reason/source
refs/forbidden-use rendering, and review-gated PM-quality support-summary invocation. Workbench does
not calculate PM scores, segment averages, fairness spread, protected-class posture, rankings, HR,
conduct, client-contact, trade approval, order routing, OMS, execution, or browser prompts.

Promotion proof:

1. `tests/unit/dpm/pm_quality/test_pm_operating_quality.py`,
2. `tests/unit/dpm/pm_quality/test_pm_quality_repository.py`,
3. `tests/unit/api/test_pm_operating_quality_api.py`,
4. `tests/unit/dpm/api/test_portfolio_memory_api.py`,
5. `tests/unit/test_domain_data_product_contracts.py`,
6. OpenAPI, vocabulary, no-alias, migration-smoke, typecheck, lint, and domain-product contract gates before PR.

Boundary-hardening proof:

1. `python -m pytest tests/unit/dpm/api/test_portfolio_memory_api.py -q`,
2. portfolio-memory API regression proves `pm_scoring` projects only bounded
   `PM_QUALITY_SCORE_RUN` lineage events for source-backed PM-book members and omits raw score
   payloads,
3. OpenAPI regression proves the explicit PM operating quality score-run preview route is
   documented and that hidden-truth prevention and non-use posture remain visible.

### Suggested Sequencing

Recommended order:

1. maintain the implemented Gateway/Workbench outcome-review composition as contracts evolve,
2. maintain generated report/render/archive materialization and retrieval posture,
3. maintain governed AI narrative support only through `lotus-ai`, Gateway, and Workbench,
4. add source-owned risk/performance/tax/FX/cash/execution methodologies as source owners publish
   certified contracts,
5. expand PM operating quality beyond the current policy, governance controls, score-run lifecycle,
   optional source-backed PM-book materialization, source-segment fairness-analysis preview, and
   immutable review-action ledger only through governed downstream UX and source-owner contracts.

Rationale:

Gateway, Workbench, report/render/archive, and governed AI narrative now realize the supported
manage backend for the first-wave RFC-0042 product path without waiting for every future source
methodology. Execution/OMS integration and richer source-owned outcome methodologies still
introduce separate ownership, control, audit, and regulatory considerations. PM operating quality
now has a bounded Manage-owned policy administration, score-run preview, persisted score-run
lifecycle, source-segment fairness-analysis preview product, and immutable review-action ledger with scoring disabled by default,
strict non-use posture, required bank approval and fairness-review evidence, immutable policy
versions, immutable score-run storage, optional source-owned PM-book materialization, and bounded
portfolio-memory score-run/review-action lineage projection. Gateway BFF composition is implemented through
`lotus-gateway` PR #213 for policy, score-run, fairness-analysis, and score-run summary handoff
without local score calculation or prohibited-use claims; Gateway review-action BFF routes remain
downstream work. `lotus-ai` PR #70
implements `pm_quality_summary.pack@v1` as support-only narrative over score-run evidence without
score ownership. Gateway/Workbench fairness-analysis product realization and PM-quality summary
invocation are now complete for the bounded current support claim through Gateway PR #213 and
Workbench PR #245. Workbench review-action ledger/detail/preview/create UX, persisted summary
history, approval workflow beyond immutable review actions, evidence validation,
HR/compensation/conduct integration, protected-class inference, PM ranking, client-contact, order,
OMS, and execution remain future product depth outside this support claim.

### RFC-0042 Promotion Checklist For Any Future Item

Before any item above moves from this ledger into a supported-feature claim:

1. owning repository and API/source contract are explicit,
2. implementation is complete in the owning app,
3. `lotus-manage` consumes only certified source truth where it is not the owner,
4. Gateway and Workbench consume through the governed product path,
5. degraded, stale, missing, permission-denied, partial, unsupported, malformed, conflicting, and
   unavailable states are tested where applicable,
6. OpenAPI/Swagger quality is certified for every API added or changed,
7. live or canonical front-office evidence is captured and critically reviewed,
8. README, RFC, source-map, wiki, supported-features, and repository context are aligned,
9. PR checks are green, PRs are merged, wiki is published, and branches are cleaned.
