# Repository Engineering Context

This file provides repository-local engineering context for `lotus-manage`.

For platform-wide truth, read:

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`

## Repository Role

`lotus-manage` is the discretionary mandate portfolio-management execution and operational
supportability service.

It owns management-side rebalance execution, what-if orchestration, run supportability, policy-pack
controls, and mandate workflow review for discretionary portfolio management.

## Business And Domain Responsibility

This repository owns:

1. discretionary mandate rebalance simulation and what-if workflow APIs,
2. management-side lifecycle, workflow review, and execution support,
3. operational supportability, deterministic artifacts, lineage, idempotency, and policy-pack
   contracts.

Advisor-led proposal simulation, artifacts, consent, and lifecycle workflows are intentionally
owned by `lotus-advise`.

## Current-State Summary

Current repository posture:

1. `lotus-manage` is the management-side service after the split from `lotus-advise`,
2. canonical local host runtime uses port `8001` so it can coexist with `lotus-advise`,
3. local CI and Docker parity are already standardized under the RFC-0072 lane model,
4. upstream and source-data authority posture is classified under RFC-0082 in `docs/standards/RFC-0082-upstream-contract-family-map.md`,
5. it carries repo-native RFC-0084 consumer declarations for the governed core portfolio-state
   product used by management execution request contracts,
6. it carries the RFC-0091 repo-native producer declaration and telemetry fixture for
   `PortfolioActionRegister`,
7. the service remains part of the canonical front-office validation path through `lotus-gateway`,
8. current execution APIs support explicit `input_mode=stateless` caller-supplied portfolio,
   market-data, model, shelf, and option bundles,
9. stateful `portfolio_id` execution has typed selector/context models, a bounded `lotus-core`
   resolver client, transformation helpers, and lineage fields; it is disabled by default but
   live-proven when explicit stateful gates and `DPM_CORE_BASE_URL` are configured,
10. RFC-087 composed source-product integrations are implemented and live-proven for
    `DpmModelPortfolioTarget:v1` through
    `/integration/model-portfolios/{model_portfolio_id}/targets` and
    `DiscretionaryMandateBinding:v1` through
    `/integration/portfolios/{portfolio_id}/mandate-binding`, and
    `InstrumentEligibilityProfile:v1` through `/integration/instruments/eligibility-bulk`, and
    `PortfolioTaxLotWindow:v1` through `/integration/portfolios/{portfolio_id}/tax-lots`,
    `MarketDataCoverageWindow:v1` through `/integration/market-data/coverage`, and
    `DpmSourceReadiness:v1` through `/integration/portfolios/{portfolio_id}/dpm-source-readiness`,
    and `TransactionCostCurve:v1` through
    `/integration/portfolios/{portfolio_id}/transaction-cost-curve`.
11. RFC-0037 through RFC-0043 define the strategic revamp into a DPM operating system.
    RFC-0038, RFC-0039, RFC-0040, the manage-owned explicit portfolio-list wave scope of
    RFC-0041, Gateway RFC-0098 wave composition, and the first-wave Workbench wave command center
    are now implementation-backed, CI-proven, live-proven, and wiki-published in their owning
    repositories. Remaining roadmap scope stays target-state planning material until
    implementation-backed support, live proof, and supported-feature promotion are completed.
    RFC37-WTBD-006 is complete on merged, validated, and wiki-published platform truth through
    `lotus-platform` PR #310. The governed canonical DPM demo story now lives in
    `lotus-platform/docs/demo/canonical-dpm-demo-story.md` and
    `lotus-platform/wiki/Canonical-DPM-Demo-Story.md`, tied to `PB_SG_GLOBAL_BAL_001`, canonical
    demo-data contracts, Workbench panel registry, platform QA, audience-specific demo guidance,
    diagrams, and unsupported-claim boundaries.
12. RFC-0038 has delivered the first implementation-backed DPM operating-system foundation with a
    source-mapped `DpmMandateDigitalTwin`, deterministic ten-dimension mandate health engine,
    derived monitoring-exception taxonomy, repository contract, in-memory and PostgreSQL
    persistence, mandate migrations, certified mandate refresh/read/version/diff APIs, standalone
    health APIs, bounded monitoring/exception APIs, and a bounded command-center summary API.
    Local manage proof, local canonical manage plus live `lotus-core` proof, supported-feature
    promotion, and wiki publication have passed. Gateway composition, Workbench cockpit panels, and
    populated platform canonical seed automation are now implementation-backed and live-proven in
    their owning repositories. PM-book wave discovery and command-center monitoring cohorts now
    consume lotus-core `PortfolioManagerBookMembership:v1`; Workbench triggers the PM-book-backed
    command-center monitoring path through Gateway without inferring membership locally. The
    command-center supportability contract now publishes a bounded `state` over ready, partial,
    empty, degraded, and blocked source-readiness posture so Gateway, Workbench, and platform seed
    automation can distinguish completeness from source health without local inference.
13. RFC-0039 has delivered the implementation-backed construction-alternative backend foundation:
    bounded construction vocabulary, pure alternative models, method registry, enrichment posture,
    risk/performance seams, repository contract, in-memory and PostgreSQL persistence foundation,
    migration `0005_construction_alternatives.sql`, and certified APIs for generating, retrieving,
    and selecting persisted alternative sets. First-wave and mandatory authority-backed methods are
    supported as manage backend capabilities: solver-constrained, risk-aware through `lotus-risk`
    concentration authority, liquidity-aware with optional `lotus-core`
    `PortfolioCashflowProjection:v1` projected cash-pressure evidence, optional source-owned
    `ClientIncomeNeedsSchedule:v1`, `LiquidityReserveRequirement:v1`, and
    `PlannedWithdrawalSchedule:v1` supportability evidence, currency-overlay, and regime-stress-aware
    through `lotus-risk` `RegimeScenarioPackEvaluation:v1` when `DPM_RISK_BASE_URL` is configured.
    Manage preserves these client-liquidity source products as evidence only and does not claim
    financial-planning advice, funding recommendation, client liability planning, OMS instruction,
    or treasury action.
    RFC-0038 mandate-health refresh also consumes core `ClientRestrictionProfile:v1`,
    `SustainabilityPreferenceProfile:v1`, `PortfolioCashflowProjection:v1`,
    `ClientIncomeNeedsSchedule:v1`, `LiquidityReserveRequirement:v1`, and
    `PlannedWithdrawalSchedule:v1` when available: source lineage is preserved, field-gap codes
    remain only for unavailable optional products, restricted model targets can block eligibility
    health, sustainability preferences require bounded review, and projected negative net cashflow
    can raise cash-liquidity attention without claiming client income-needs planning.
    ESG/restriction-aware construction consumes `lotus-core` `ClientRestrictionProfile:v1` and
    `SustainabilityPreferenceProfile:v1` through the stateful core-sourcing path when source gates
    are enabled. Client restriction profile violations block matching candidate trades, source
    profile gaps degrade explicitly, and sustainability allocation/classification gaps remain
    pending-review rather than unsupported ESG claims. Gateway and Workbench are not yet integrated
    with this surface; paired
    realization RFCs have been created and must be implemented/proven downstream before a full
    front-office product outcome is claimed.
14. RFC-0040 has delivered the implementation-backed manage pre-trade proof-pack backend
    foundation: durable `DpmPreTradeProofPack` JSON, deterministic Markdown summary, report-input
    handoff, AI-evidence handoff with forbidden-action/field guardrails, immutable in-memory and
    PostgreSQL persistence, append-only refs, retention metadata, section/content hashes, source
    lineage, source-backed mandate-context attachment from persisted RFC-0038 mandate twin and
    health evidence when available, certified `/api/v1/rebalance/proof-packs/*` APIs, and
    canonical Postgres-backed live proof under `output/rfc0040-proof/20260503-135112`,
    post-merge audit rerun `output/rfc0040-proof/20260503-142438`, and mandate-context hardening
    rerun `output/rfc0040-proof/20260503-145818`. Gateway proof-pack composition is merged and
    wiki-published through `lotus-gateway` PR #195. The first-wave Workbench proof-pack review UX
    is merged and wiki-published through `lotus-workbench` PR #156, consumes Gateway/BFF proof-pack
    routes only, and renders proof-pack identity, supportability, sections, source hashes,
    Markdown/report/AI posture, and action eligibility without reconstructing proof-pack evidence
    in the browser. `lotus-manage` PR #117 made deterministic proof-pack source identities
    replay-safe across idempotency keys, and governed platform proof
    `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-124405.json`
    validates the first-wave full product path with `dpm.proof_pack` classified `ready` for
    `dpp_c09f73d0`. RFC40-WTBD-004 proof-pack report materialization is now implemented in the
    owning report/render/archive repositories through `lotus-render` PR #11, `lotus-report` PR #90,
    and `lotus-archive` PR #23. RFC40-WTBD-005 governed PM memo support is now implemented in
    the owning AI/Gateway/Workbench repositories through `lotus-ai` PR #61, `lotus-gateway`
    PR #198, and `lotus-workbench` PR #166, then live-proven by rebuilt canonical front-office QA
    `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260507-210641.json`.
    RFC40-WTBD-006 manage proof-pack enrichment is implemented for selected construction
    alternatives: `risk_impact` and `performance_context` sections preserve source-owned
    `AuthoritativeRiskContext` and `AuthoritativePerformanceContext` supportability, lineage refs,
    content hashes, reason codes, and bounded source-emitted measures without manage-local
    risk/performance methodology. RFC40-WTBD-007 manage proof-pack enrichment is implemented for
    source-owned observed transaction-cost evidence: stateful core sourcing can consume
    `lotus-core` `TransactionCostCurve:v1`, attach `AuthoritativeTransactionCostContext` to
    construction alternatives, and preserve supportability, source refs, content hashes, reason
    codes, evidence windows, missing securities, bounded curve points, and represented observation
    counts in the proof-pack `turnover_and_cost` section. Local estimated construction cost remains
    labelled separately. RFC40-WTBD-009 manage proof-pack enrichment is implemented for
    selected-alternative scenario-pack evidence and generation-time direct source-owned scenario
    context: `scenario_and_regime_evidence` preserves `lotus-risk` / CIO
    `RegimeScenarioPackEvaluation:v1` supportability, source refs, canonical
    `regime_stress_context` hashes, scenario pack id, worst-case loss, policy threshold, and bounded
    reason codes when the selected alternative carries the authority context or the caller supplies
    it directly for proof-pack generation. Selected-alternative evidence takes precedence; Manage
    does not calculate scenario methodology, contribution rows, CIO approval workflow, effective
    period exceptions, or portfolio/mandate applicability evidence. RFC39-WTBD-006 is now
    implemented for source-owned observed-cost
    construction comparison: the `COST_AWARE` method applies `TransactionCostCurve:v1` observed
    average bps to candidate trade notionals, emits `ESTIMATED_COST` objective/constraint traces,
    and degrades when the curve is missing or does not cover traded securities. Manage does not
    claim predictive execution quotes, market-impact modelling, venue routing, or true min-cost
    optimization from observed booked-fee evidence. RFC40-WTBD-010 now has a manage backend portfolio-memory
    foundation through `/api/v1/rebalance/portfolio-memory/{portfolio_id}` and
    `src/core/portfolio_memory/`: it composes persisted mandate health snapshots, monitoring
    exceptions, proof packs, proof-pack-local decision timeline events, RFC-0041 wave events,
    internal handoff refs, and RFC-0042 outcome-review events into a deterministic, source-backed,
    hashable timeline without reconstructing mandate health, risk, performance, execution, tax,
    cash, FX, or source-owner methodology. RFC42-WTBD-006 source-owner methodology depth now
    includes merged and wiki-published issuer active-risk source truth through `lotus-performance`
    PR #165 (`191a405`, wiki `46a9124`) and `lotus-risk` PR #138 (`8ae3e4a`, wiki
    `616a10c`): performance owns benchmark issuer exposure context from lotus-core index-catalog
    issuer labels, and risk owns stateful `ACTIVE_RISK + ISSUER` historical attribution
    consumption. Manage records the proof posture only and does not reconstruct benchmark issuer
    exposure, covariance, tracking-error, or issuer attribution locally. It also includes the
    merged and wiki-published `lotus-core`
    `HoldingsAsOf:v1` methodology slice from PR #348
    (`0a8785e0a4be7ea737b40eded07bd9c7f8002f25`, wiki `2a428eb`), which pins booked holdings,
    explicit as-of holdings, projected-inclusive holdings, cash-balance reads,
    reporting-currency cash balances, snapshot-versus-history fallback, position weights,
    supportability states, and explicit non-claims for liquidity ladders, income-needs planning,
    performance returns, risk exposure methodology, tax advice, execution quality, and OMS
    acknowledgement. It also includes the merged and wiki-published `lotus-core`
    `MarketDataCoverageWindow:v1` methodology slice from PR #349
    (`4101f1ba321b8464093c12358e57f5c448440413`, wiki `9be04cc`), which pins latest price and FX
    observation selection, configurable max-staleness policy, missing/stale market-data posture,
    populated DPM source-readiness support, and explicit non-claims for valuation methodology, FX
    attribution, liquidity ladders, market impact, execution quality, best execution, venue
    routing, and OMS acknowledgement. It also includes the merged and wiki-published `lotus-core`
    `DpmSourceReadiness:v1` methodology slice from PR #350
    (`c17bfa3298470375faa0b5e15bf369fa88a70597`, wiki `e3fd859`), which pins mandate binding,
    model target, eligibility, tax-lot, and market-data coverage composition, deterministic
    instrument-universe assembly, fail-closed source-family precedence, supportability and
    data-quality mapping, and explicit non-claims for mandate approval, client suitability, tax
    advice, valuation methodology, FX attribution, liquidity ladders, execution quality, best
    execution, venue routing, and OMS acknowledgement. It also includes the merged and
    wiki-published `lotus-risk` rolling tracking-error methodology slice from PR #113
    (`e00ece9279082a96071bd9e745b7211232b82db6`, wiki `d1330ee`), rolling information-ratio
    methodology slice from PR #114 (`ffa881e3266c09a4d48044b50df5bb2db43bd489`, wiki
    `105b716`), rolling volatility methodology slice from PR #117
    (`8f04b24276bd73dd34ef5ce3edf59e81453858ae`, wiki `c6eef3c`), rolling Sharpe
    methodology slice from PR #118 (`3f4bbfe6d536a1f3d68b773f917a3f059987db51`, wiki
    `0b96201`), rolling beta methodology slice from PR #119
    (`ffcfddbc24484811152c85582398528c0c879d98`, wiki `bcccb0c`), and rolling maximum drawdown
    methodology slice from PR #120 (`2c205372a5ac3bfc024a7eb61c0bd44383895078`, wiki
    `429e284`) for `RollingRiskMetricsReport:v1`; they pin pp-to-decimal conversion, `ddof=1`,
    annualized decimal volatility output, annualized decimal tracking-error output, dimensionless
    Sharpe, beta, and information-ratio output, decimal drawdown-ratio output, warm-up/null
    behavior, source-owned risk-free/benchmark alignment posture, no-aligned dependency posture,
    zero-excess-volatility Sharpe flagging, zero-benchmark-variance beta flagging, and
    zero-tracking-error information-ratio flagging.
    It also includes the merged and wiki-published `lotus-risk` `MAX_DRAWDOWN` methodology slice
    from PR #129 (`6ac31ac860275561cb5770a49f1c2d7aeb7440e6`, wiki `3f2e37a`) for
    `DrawdownAnalyticsReport:v1`; it pins percentage-point input conventions, decimal
    cumulative-wealth and running-peak drawdown behavior, decimal `summary.max_drawdown` output,
    episode peak/trough/recovery semantics, empty-period insufficient-data posture,
    never-underwater zero-drawdown posture, duration-unit day-counter behavior, and episode-list
    filter isolation from the summary maximum-drawdown value.
    It also includes the merged and wiki-published `lotus-risk` `AVERAGE_DRAWDOWN` methodology
    slice from PR #130 (`d96651d0c34e2414f61fb70c2e1a3106134c3632`, wiki `01d181b`) for
    `DrawdownAnalyticsReport:v1`; it pins percentage-point input conventions, decimal
    cumulative-wealth and running-peak drawdown behavior, decimal `summary.average_drawdown`
    output, strictly-underwater observation inclusion, empty-period insufficient-data posture,
    never-underwater zero-drawdown posture, duration-unit day-counter isolation, and episode-list
    filter isolation from the summary average-drawdown value.
    It also includes the merged and wiki-published `lotus-risk` `ULCER_INDEX` methodology slice
    from PR #131 (`ce129e4ba52ff20f6e620df837238a852d7a522c`, wiki `6f244d1`) for
    `DrawdownAnalyticsReport:v1`; it pins percentage-point input conventions, decimal
    cumulative-wealth and running-peak drawdown behavior, non-negative decimal
    `summary.ulcer_index` output, full-path squared drawdown inclusion including zero peak
    observations, empty-period insufficient-data posture, never-underwater zero-drawdown posture,
    duration-unit day-counter isolation, and episode-list filter isolation from the summary
    ulcer-index value.
    It also includes the merged and wiki-published `lotus-risk` `TIME_UNDER_WATER_DAYS`
    methodology slice from PR #132 (`d44aae1ec899c59565169b5fd4434cdedb00f76d`, wiki
    `8a7e507`) for `DrawdownAnalyticsReport:v1`; it pins percentage-point input conventions,
    decimal cumulative-wealth and running-peak drawdown behavior, observation-count
    `summary.time_under_water_days`, strictly-underwater observation counting, explicit
    non-duration posture for calendar/business-day settings, empty-period insufficient-data
    posture, never-underwater zero posture, duration-unit day-counter isolation, and episode-list
    filter isolation.
    It also includes the merged and wiki-published `lotus-risk` `POSITION_HHI` methodology slice
    from PR #133 (`dea20b5a6f99403a9b8e974ac9da823c691c5465`, wiki `1e2f926`) for
    `ConcentrationRiskReport:v1`; it pins stateless, stateful, and simulation source paths,
    positive numeric position-value extraction, market-value versus quantity fallback precedence,
    decimal position-weight construction, conventional `0..10000` Herfindahl-Hirschman scaling,
    six-decimal response rounding, proposed-state fallback to current HHI when projected values
    are unavailable, input-universe option boundaries, and issuer-enrichment isolation from
    `risk_proxy.hhi_*` outputs.
    It also includes the merged and wiki-published `lotus-risk` `TOP_POSITION_WEIGHT` methodology
    slice from PR #134 (`21ef697a1c308a3d8ea7c8e40e06019544be7e93`, wiki `dd25844`) for
    `ConcentrationRiskReport:v1`; it pins stateless, stateful, and simulation source paths,
    positive numeric position-value extraction, market-value versus quantity fallback precedence,
    decimal `0..1` top-position weight output, six-decimal response rounding, proposed-state
    fallback to current top-position weight when projected values are unavailable, deterministic
    top-position driver selection, input-universe option boundaries, and issuer-enrichment
    isolation from `single_position_concentration.top_position_*` outputs.
    It also includes the merged and wiki-published `lotus-risk` `TOP_N_CUMULATIVE_WEIGHT`
    methodology slice from PR #135 (`02352279c4a990f386ec582e8f839fc3c359437f`, wiki `59277e5`)
    for `ConcentrationRiskReport:v1`; it pins stateless, stateful, and simulation source paths,
    positive numeric position-value extraction, market-value versus quantity fallback precedence,
    decimal `0..1` top-N cumulative weight output, six-decimal response rounding, request-contract
    `top_n` bounds, proposed-state fallback to current top-N cumulative weight when projected
    values are unavailable, top-N sorted-weight summation, input-universe option boundaries, and
    issuer-enrichment isolation from
    `single_position_concentration.top_n_cumulative_weight_*` outputs.
    It also includes the merged and wiki-published `lotus-risk` `ISSUER_HHI` methodology slice
    from PR #136 (`ed9dba4663b718ae86c326f7d1f7ae591177e322`, wiki `3dc7293`) for
    `ConcentrationRiskReport:v1`; it pins stateless, stateful, and simulation source paths,
    positive numeric position-value extraction, market-value versus quantity fallback precedence,
    conventional `0..10000` issuer-HHI output, six-decimal response rounding, proposed-state
    fallback to current issuer HHI when projected issuer buckets are unavailable, covered-subset
    issuer aggregation, legal versus ultimate-parent issuer grouping, issuer-enrichment
    precedence, issuer coverage/supportability posture, and isolation from `risk_proxy.hhi_*` and
    `single_position_concentration.*` outputs.
    It also includes the merged and wiki-published `lotus-risk` `TOP_ISSUER_WEIGHT` methodology
    slice from PR #137 (`2da6e3a8346d5a188484750436a0258776918620`, wiki `1e1eb14`) for
    `ConcentrationRiskReport:v1`; it pins stateless, stateful, and simulation source paths,
    positive numeric position-value extraction, market-value versus quantity fallback precedence,
    decimal `0..1` top-issuer weight output, six-decimal response rounding, proposed-state
    fallback to current top issuer when projected issuer buckets are unavailable, covered-subset
    issuer aggregation, legal versus ultimate-parent issuer grouping, issuer-enrichment
    precedence, deterministic top-issuer driver selection, issuer coverage/supportability posture,
    and isolation from `risk_proxy.hhi_*` and `single_position_concentration.*` outputs.
    It also includes the merged and wiki-published `lotus-risk` `VOLATILITY` methodology slice
    from PR #121 (`457f28dedea2a9db386192f5d00a6905e2f1c49a`, wiki `2c09ab2`) for
    `RiskMetricsReport:v1`; it pins percentage-point input conventions, optional log-return
    transformation, frequency compounding before volatility, `ddof=1` sample standard deviation,
    decimal `details.standard_deviation`, annualized percentage-point
    `metrics.VOLATILITY.value`, annualization-factor resolution, no benchmark or risk-free
    dependency posture, no-denominator posture, and insufficient-data failure behavior.
    It also includes the merged and wiki-published `lotus-risk` `SHARPE` methodology slice from
    PR #122 (`932600162df7482a6d9c01a7470760238cab57ce`, wiki `cdb25df`) for
    `RiskMetricsReport:v1`; it pins percentage-point input conventions, optional log-return
    transformation, frequency compounding before Sharpe, `ddof=1` sample standard deviation,
    decimal `details.mean_return`, `details.volatility`, and
    `details.periodic_risk_free_rate`, dimensionless annualized `metrics.SHARPE.value`,
    annualization-factor resolution, no benchmark dependency posture, zero-volatility fail-closed
    posture, and insufficient-data failure behavior.
    It also includes the merged and wiki-published `lotus-risk` `SORTINO` methodology slice from
    PR #126 (`dbe16b647f972ff626a8b6eb11e06041b6e0f46a`, wiki `81f787e`) for
    `RiskMetricsReport:v1`; it pins percentage-point input conventions, optional log-return
    transformation, frequency compounding before Sortino, annual-to-periodic MAR conversion,
    full-sample mean excess return, downside-only root-mean-square denominator, decimal
    `details.periodic_mar`, `details.mean_return`, `details.excess_return`,
    `details.annualized_excess_return`, and `details.downside_deviation`, dimensionless
    annualized `metrics.SORTINO.value`, no benchmark dependency posture, no risk-free
    dependency posture, no-downside-observation fail-closed posture, and insufficient-data
    failure behavior.
    It also includes the merged and wiki-published `lotus-risk` `DRAWDOWN` methodology slice from
    PR #128 (`4784839067027d991500ff2d19c728122e227466`, wiki `edde5df`) for
    `RiskMetricsReport:v1`; it pins percentage-point input conventions, frequency compounding
    before drawdown, explicit no-log-return posture, cumulative-wealth and running-peak behavior,
    signed percentage-point `metrics.DRAWDOWN.value`, signed `details.max_drawdown`,
    peak/trough/recovery episode timing details, no benchmark dependency posture, no risk-free
    dependency posture, no annualization-factor posture, no-denominator posture beyond the running
    peak wealth path, and insufficient-data failure behavior.
    It also includes the merged and wiki-published `lotus-risk` `VAR` methodology slice from
    PR #127 (`957d1a4d37e75e70a9915e65584fc41e7328f082`, wiki `85116ab`) for
    `RiskMetricsReport:v1`; it pins percentage-point input conventions, optional log-return
    transformation, frequency compounding before VaR, historical, Gaussian, and Cornish-Fisher
    method behavior, signed return-threshold output in percentage points, square-root-of-time
    horizon scaling, optional expected-shortfall calculation, signed `details.base_var`,
    `details.base_expected_shortfall`, and `details.expected_shortfall`, no benchmark dependency
    posture, no risk-free dependency posture, no annualization-factor posture, and
    insufficient-data failure behavior.
    It also includes the merged and wiki-published `lotus-risk` `BETA` methodology slice from
    PR #123 (`d6c50e126fa81250ab16f0299380fb0ad9022619`, wiki `7738cac`) for
    `RiskMetricsReport:v1`; it pins percentage-point input conventions, optional log-return
    transformation, frequency compounding before beta, strict inner date alignment, `ddof=1`
    sample covariance and benchmark variance, percentage-point-squared `details.covariance` and
    `details.benchmark_variance`, dimensionless slope `metrics.BETA.value`, no risk-free
    dependency posture, zero-benchmark-variance fail-closed posture, and
    insufficient-aligned-observation failure behavior.
    It also includes the merged and wiki-published `lotus-risk` `TRACKING_ERROR` methodology
    slice from PR #124 (`46eddb4dc332bb1e4a79c22b1bd557f2b2db2cb9`, wiki `a1d8898`) for
    `RiskMetricsReport:v1`; it pins percentage-point input conventions, optional log-return
    transformation, frequency compounding before tracking error, strict inner date alignment,
    `ddof=1` sample active-return standard deviation, decimal
    `details.active_volatility` and `details.annualized_tracking_error`, annualized
    percentage-point `metrics.TRACKING_ERROR.value`, no risk-free dependency posture,
    no-denominator posture, constant-active-return zero tracking-error posture, and
    insufficient-aligned-observation failure behavior.
    It also includes the merged and wiki-published `lotus-risk` `INFORMATION_RATIO` methodology
    slice from PR #125 (`7ccf5667e6676b8f1865ebd9768b8913262d3d3b`, wiki `7a0aa9e`) for
    `RiskMetricsReport:v1`; it pins percentage-point input conventions, optional log-return
    transformation, frequency compounding before information ratio, strict inner date alignment,
    active-return construction, `ddof=1` sample active-return standard deviation, decimal
    `details.portfolio_mean_return`, `details.benchmark_mean_return`,
    `details.active_mean_return`, `details.tracking_error`,
    `details.annualized_active_return`, and `details.annualized_tracking_error`, dimensionless
    annualized `metrics.INFORMATION_RATIO.value`, no risk-free dependency posture,
    zero-tracking-error fail-closed denominator posture, and insufficient-aligned-observation
    failure behavior.
    It also includes the merged and wiki-published `lotus-performance`
    `currency_attribution_totals` source-product slice from PR #164
    (`cbda83fcd8fbabf957c187b19ca98247a11a9812`, wiki `f76a954`), which pins
    portfolio-level Karnosky-Singer local allocation, local selection, currency allocation,
    currency selection, total effect, and currency-count output in the source-owned attribution
    response without requiring Manage, Gateway, Workbench, or reporting consumers to reconstruct
    portfolio-level FX attribution from rendered currency rows.
    It also includes the merged and wiki-published `lotus-core`
    `PortfolioCashflowProjection:v1` methodology slice from PR #344
    (`3a29c3ea92fce92d39fbc91f325bd04cb1157d20`, wiki `231bd75`), which pins booked-only
    versus projected mode behavior, latest-cashflow-row selection, settlement-dated external
    `DEPOSIT`/`WITHDRAWAL` inclusion, same-day booked/projected additivity, portfolio-base-currency
    output, and explicit non-claims for tax methodology, performance returns, market impact, and
    OMS execution forecasting while still leaving FX, execution, and broader methodology depth to
    future source-owner work. The
    record also includes the merged and wiki-published `lotus-core`
    `PortfolioLiquidityLadder:v1` methodology slice from PR #356
    (`d47eb716e2992ea0988ddbb92e402594d4193dec`, wiki `28c4ae2`), which pins opening cash,
    fixed horizon buckets, booked/projected/net cashflow, cumulative cash, shortfall,
    asset-liquidity-tier exposure, source-product catalog/security posture, and explicit
    non-claims for advice, funding recommendations, income-needs planning, tax methodology,
    FX attribution, market impact, best execution, venue routing, and OMS acknowledgement. The
    record also includes the merged and wiki-published `lotus-core`
    `PortfolioRealizedTaxSummary:v1` methodology slice from PR #363
    (`a349dc0cefc2d254c539d240073f5a5aa44a0a00`, wiki `1170afd`), which pins
    portfolio-level explicit realized-tax evidence, withholding-tax and other-interest-deduction
    aggregation by ledger currency, optional reporting-currency restatement, lineage/supportability
    posture, source-product catalog/security profiles, and explicit non-claims for tax advice,
    after-tax optimization, tax-loss harvesting suitability, jurisdiction-specific recommendation,
    client-tax approval, tax-reporting certification, FX attribution, execution quality, and OMS
    acknowledgement. It also includes the merged and wiki-published `lotus-core`
    `PortfolioCashMovementSummary:v1` methodology slice from PR #364
    (`486136affef18d7c9d51886be1d52a804cfd2867`, wiki `ad67cf6`), which pins latest cashflow row
    selection per transaction, grouping by classification/timing/currency/position-flow/
    portfolio-flow posture, signed cash movement totals, movement direction, evidence timestamp,
    data-quality posture, source-product catalog/security profiles, and explicit non-claims for
    cashflow forecasting, liquidity advice, income-needs planning, funding recommendations,
    treasury instructions, tax methodology, predictive execution, execution quality, and OMS
    acknowledgement. The matching `lotus-platform` PR #331
    (`500a1b83dddb85842b79e6218595bd13f237d949`) mirrors the source product into platform mesh
    discovery and certification artifacts. The
    canonical current-horizon cashflow/liquidity proof from PR #360
    (`e83f0c85ac0bdaa738af831a8224709e1b29a7fd`, wiki `3956cb6`) keeps
    `PB_SG_GLOBAL_BAL_001` seeded with a deterministic projected withdrawal so Core, Gateway, and
    Workbench live validation exercise non-zero projected settlement cashflow without turning the
    seed into client income-needs planning, funding advice, or OMS forecasting. The
    record also includes the merged and wiki-published `lotus-core`
    `TransactionLedgerWindow:v1` methodology slice from PR #347
    (`7aef82bc8f9232c62333b8386001527b19829f86`, wiki `6bb1041`), which pins booked and
    projected-inclusive ledger modes, effective as-of resolution,
    portfolio/instrument/security/transaction type/FX-event/date-window filters, joined
    transaction-cost and linked-cashflow row preservation, optional reporting-currency
    restatement, empty/complete/paged data-quality posture, and explicit non-claims for tax
    advice, FX attribution, transaction-cost methodology,
    execution-quality assessment, and OMS acknowledgement; the merged and wiki-published
    `lotus-core`
    `PortfolioTaxLotWindow:v1` methodology slice from PR #346
    (`e48d85a98ae3f53199bdccbe2e83f6304c9e050c`, wiki `f37af67`), which pins effective-date lot
    selection, optional security filtering, open/closed lot posture, deterministic paging,
    open-quantity status derivation, cost-basis preservation, empty-source supportability, and
    explicit non-claims for jurisdiction-specific tax advice, realized-tax optimization,
    wash-sale treatment, client-tax approval, tax-reporting certification, execution methodology,
    and OMS acknowledgement. It also includes the merged and wiki-published `lotus-core`
    `TransactionCostCurve:v1` methodology
    slice from PR #345 (`83d791d0e599f06a2c0caab6eaba647f717d4658`, wiki `154ae27`), which pins
    observed booked-fee grouping by `(security_id, transaction_type, currency)`, fee-field
    precedence, zero-fee and zero-notional exclusion, notional-weighted average bps, min/max bps,
    deterministic paging, supportability states, and explicit non-claims for predictive execution
    quotes, market impact, venue routing, best execution, and OMS acknowledgement. First-wave
    Gateway/Workbench product realization is also merged and live-proven through `lotus-gateway`
    PR #199, `lotus-workbench` PR #167, `lotus-platform` PR #307, and canonical Workbench evidence
    `lotus-workbench/output/playwright/live-canonical/dpm-portfolio-memory-live.png`.
    Manage now emits stable event identity plus retention, redaction, access, audit policy, and
    explicit source-event family posture in the portfolio-memory API contract. The posture lists
    supported manage/report/AI/archive families, marks external OMS execution as deferred, and
    supports bounded PM quality score-run lineage for persisted score runs whose source-owned Core
    PM-book membership evidence includes the requested portfolio, without copying raw score
    payloads or creating portfolio-level rankings.
    `lotus-report` PR #92 adds the report-side bounded
    `portfolio_memory_context` consumer for proof-pack, rebalance-wave, and outcome-review report
    jobs without reconstructing manage-owned portfolio-memory events, and `lotus-report` PR #93
    adds the report-owned source-event family at
    `GET /reports/jobs/{job_id}/portfolio-memory-events` for report lifecycle, snapshot, render,
    and archive evidence. Manage report-input APIs now attach that bounded context to proof-pack,
    rebalance-wave, and outcome-review report inputs while keeping portfolio-memory hashes separate
    from recursive report-input evidence hashes. `lotus-ai` PR #62
    adds bounded DPM PM memo and outcome-review narrative consumers that validate portfolio
    identity, capped event refs, source content hash, `NO_RAW_PAYLOADS`, and no-reconstruction
    source-authority policy before exposing compact portfolio-memory lineage summaries. `lotus-ai`
    PR #64 adds the AI-owned workflow-pack source-event family for no-raw-payload AI run, review,
    and lineage events at `/platform/workflow-packs/source-events` and
    `/platform/workflow-packs/runs/{run_id}/source-events`. `lotus-archive` PR #25 adds the
    archive-owned generated-document/client-delivery source-event family at
    `/documents/{document_id}/source-events` for generated-document archive, supersession,
    correction, and client-delivery reissue lineage without raw document bytes, storage keys, raw
    report payloads, or raw client references. Future OMS remains downstream source-owner scope,
    while PM operating quality policy administration and score-run preview/create/read/list is
    supported separately by `lotus-manage` with bank-supplied policy, required bank approval and
    fairness-review evidence for enabled policies, source-backed evidence, and optional
    source-owned lotus-core `PortfolioManagerBookMembership:v1` scope materialization.
    Portfolio memory now projects those persisted source-backed score runs as
    `PM_QUALITY_SCORE_RUN` lineage events for matching PM-book members only.
    Manage also supports bounded PM operating quality fairness-analysis preview at
    `POST /api/v1/rebalance/pm-operating-quality/fairness-analyses/preview` through
    `PmOperatingQualityFairnessAnalysis:v1`: callers supply persisted score-run ids and
    source-defined segment evidence for mandate type, region, book profile, client constraint
    profile, market regime, or custom source segments; Manage validates common policy/as-of scope,
    minimum scorable segment counts, and governed average-score spread without inferring protected
    classes or creating PM rankings, HR, compensation, conduct, approval, client-contact,
    execution, or OMS decisions.
    `lotus-gateway` PR #213 (`62ce4c4`) adds the bounded PM operating quality BFF route family at
    `/api/v1/dpm/command-center/pm-operating-quality/*` and published Gateway wiki source at
    `a4c9db9`, preserving Manage policy and score-run truth without Gateway-local scoring,
    ranking, policy administration, HR, compensation, conduct, approval, client-contact,
    execution, or OMS claims. Workbench PM-quality UI remains future owner scope.
    `lotus-manage` remains evidence and report-input authority only; it does not generate, render,
    archive, retain, retrieve documents, construct AI prompts, generate PM memos, approve trades,
    issue recommendations, or use PM quality score runs for HR, compensation, conduct enforcement,
    or autonomous ranking. Richer attribution/contribution/scenario source
    depth, client restrictions, sustainability profiles, predictive execution methodology, min-cost
    optimization, and broader cross-RFC portfolio-memory source-event completion remain downstream
    WTBD work in the owning repositories.
15. RFC-0041 is `DONE` for implementation-backed manage backend authority over explicit
    portfolio-list rebalance waves: durable preview/create,
    source-check, RFC-0039-backed ready-item simulation, item-level selection, RFC-0040 proof-pack
    linkage, approval-with-exceptions, staging, internal operations handoff evidence with
    `external_execution_claimed=false`, actor-attributed pre-execution cancellation,
    repository-backed wave search/detail/item/proof-pack posture/report-input/supportability read models,
    OpenAPI certification, and aggregate reconciliation under
    `output/rfc0041-wave-proof/20260504-231914`. The canonical proof used Postgres-backed manage
    repositories via `DPM_MANAGE_POSTGRES_DSN`. Source-owned wave risk/performance aggregate
    enrichment is implemented for manage aggregate authority: wave simulation accepts per-item
    `ConstructionAuthorityContext`, `RISK_AWARE` can consume configured lotus-risk concentration
    authority, and `aggregate_metrics.source_analytics` preserves source-family, supportability,
    lineage refs, reason codes, and source-emitted scalar values without manage-local risk or
    performance methodology. Wave simulation item diagnostics now preserve bounded
    `proposed_changes` from construction alternatives as PM-review evidence only, with no order,
    execution, fill, venue-routing, or OMS claim. Wave report materialization is now implemented in
    owning repositories through `lotus-manage` PR #124, `lotus-report` PR #91, `lotus-render`
    PR #12, and `lotus-archive` PR #24: manage remains deterministic wave report-input authority,
    while report/render/archive own job materialization, the `rebalance-wave` template, generated
    artifact metadata, retention posture, and archive lifecycle. PM-book discovery is implemented
    for `PM_BOOK_REVIEW` and for RFC-0038 command-center monitoring cohorts through lotus-core
    `PortfolioManagerBookMembership:v1`; `lotus-ai` PR #63
    implements the owner-side `dpm_wave_pm_memo.pack@v1` workflow over Manage-owned
    `DpmWaveReportInput` with forbidden-field/action/output guardrails and review-required
    support-only output. `lotus-gateway` PR #201 and `lotus-workbench` PR #168 complete the
    first-wave AI memo product path: Gateway preserves Manage wave evidence identity and passes AI
    forbidden-action guardrails, while Workbench exposes report-input and AI memo request posture
    without constructing prompts or memo content locally. `lotus-ai` PR #66 adds conservative
    workflow-pack default-version resolution for the AI control plane, selecting only registered,
    activation-eligible, non-superseded pack versions without changing Manage workflow authority.
    `lotus-ai` PR #67 adds the owner-side `dpm_operations_handoff_summary.pack@v1` workflow over
    Manage-owned `DpmWaveReportInput` handoff evidence with handoff/source-ref requirements,
    forbidden-action/output guardrails, mixed memo/handoff rejection, review-required support-only
    output, and no external execution claim. `lotus-gateway` PR #209 and PR #210 plus
    `lotus-workbench` PR #182 now expose first-wave Gateway/Workbench invocation for exception
    summaries and operations handoff summaries without direct browser prompt construction,
    client-message generation, PM scoring, routing, approval, or execution claims.
    CIO model-change discovery is now
    implemented for `CIO_MODEL_CHANGE` through lotus-core `CioModelChangeAffectedCohort:v1`.
    RFC41-WTBD-003 now has its first risk-event source-owner and manage-consumer path through
    `lotus-risk` `RiskEventAffectedCohort:v1` at
    `POST /analytics/risk/risk-event-cohorts/evaluate`, merged in `lotus-risk` PR #115
    (`bd69d1576d8c01bdcfd2309202ef37f780cc2d06`), wiki-published at `91f933a`, mirrored into
    platform mesh governance through `lotus-platform` PR #313
    (`4218d4319d5dac82e87106429fadb14247c36515`), and consumed by `lotus-manage` for bounded
    `RISK_EVENT` wave preview/create over caller-supplied candidate portfolios with
    source-supplied exposure weights. Tactical house-view wave consumption is now implemented
    through `lotus-advise` `TacticalHouseViewAffectedCohort:v1`: Manage requires bank-authored
    tactical-view refs and source-backed candidate portfolios, preserves Advise cohort refs, and
    fails closed without recomputing advisory, house-view, holdings, exposure, alignment, or mandate
    facts. `BULK_REVIEW_CAMPAIGN` additionally preserves optional
    Manage-owned approval, expiry, access-purpose, source-ref, and actor-entitlement governance
    evidence without discovering source-owned cohorts. Gateway campaign-definition BFF composition
    is merged through `lotus-gateway` PR #212 for list/get/upsert of Manage-owned campaign
    definitions without Gateway-local cohort or membership calculation. Workbench PR #184 renders
    the first-wave active campaign-definition list through Gateway/BFF without browser-side cohort
    or membership calculation. Persisted campaign discovery is now implemented at
    `GET /api/v1/rebalance/waves/campaign-discovery` as a Manage-owned
    `BulkReviewCampaignDiscovery:v1` read model over immutable `BulkReviewCampaignDefinition:v1`
    records; it exposes campaign identity, governance posture, expiry posture, source-ref count,
    source-backed candidate counts, and preview references without discovering the global portfolio
    universe, recalculating campaign membership, or owning source facts. Broader campaign workflow
    surfaces, wave risk/performance analytics posture, and external OMS execution remain
    unpromoted until owning implementations are live-proven.
16. RFC-0042 is `DONE` for manage backend authority:
    source-backed outcome-review preview/create/retrieve/search, immutable persistence and
    append-only events, source-refresh eventing, report-input and AI-evidence handoff contracts,
    supportability diagnostics, bounded metrics/logging, source-owned realized adapters for
    `lotus-risk` `RiskMetricsReport:v1`, drawdown analytics maximum drawdown, average drawdown,
    ulcer index, and time under water, concentration response position HHI and selected measures, rolling metrics selected
    metric/statistic/window measures, and historical attribution selected set/contributor measures,
    `lotus-performance` workspace-summary TWR/active/MWR returns,
    contribution selected measures, and attribution reconciliation/level/currency selected
    measures, and `lotus-core` `HoldingsAsOf:v1` cash totals plus
    `MarketDataCoverageWindow:v1` price/FX freshness posture,
    `TransactionLedgerWindow:v1` explicit transaction-row trade-fee, withholding-tax,
    realized-FX-P&L, linked-cashflow measures, and `PortfolioCashflowProjection:v1` total net
    cashflow, live
    canonical manage proof under `output/rfc0042-outcome-proof/20260505-024352`, and Slice 12 hardening proof under
    `output/rfc0042-outcome-proof/20260505-025613`. The proof found and fixed stale listener
    restart handling in `scripts/Start-CanonicalManage.ps1`, OpenAPI What/When/How gaps on
    outcome-review GET routes, same-key changed-evidence idempotency conflict handling, and invalid
    search-state filter validation. Full product support remains downstream until Gateway/Workbench
    implementation where surfaced is complete and canonically proven.

## Architecture And Module Map

Primary areas:

1. `src/`
   management APIs, workflow logic, and supporting modules.
   RFC-0038 mandate digital-twin and health-scoring domain primitives live in
   `src/core/mandates.py`; repository and persistence primitives live in
   `src/core/mandate_repository.py` and `src/infrastructure/mandates/`; mandate API orchestration
   lives in `src/api/services/mandate_service.py`, `src/api/routers/mandates.py`, and
   `src/api/routers/monitoring.py`, including the bounded command-center summary endpoint.
   RFC-0039 construction-alternative domain primitives live in `src/core/construction/`;
   construction persistence lives in `src/core/construction/repository.py` and
   `src/infrastructure/construction/`; construction API orchestration lives in
   `src/api/services/construction_service.py` and `src/api/routers/construction.py`.
   RFC-0042 outcome-review authority lives in `src/core/outcomes/`; outcome persistence lives in
   `src/infrastructure/outcomes/`; API orchestration lives in
   `src/api/services/outcome_review_service.py` and `src/api/routers/outcome_reviews.py`.
   RFC-0040/RFC-0041/RFC-0042 portfolio-memory read-model primitives live in
   `src/core/portfolio_memory/`; API orchestration lives in
   `src/api/routers/portfolio_memory.py`.
2. `scripts/`
   OpenAPI, vocabulary, migration, and governance scripts.
3. `docs/`
   project overview, runbooks, standards, demo evidence, and RFC documentation.
4. `wiki/`
   canonical authored source for repository wiki publication and operator onboarding summaries.
5. `tests/`
   unit, integration, and e2e validation.
6. `contracts/domain-data-products/`
   repo-native producer and consumer declarations for governed upstream domain data products and
   management workflow products.
7. `contracts/trust-telemetry/`
   repo-native RFC-0087/RFC-0091 trust telemetry snapshots for governed management products.

## Runtime And Integration Boundaries

Runtime model:

1. FastAPI service,
2. depends on `lotus-core` as source-data authority for governed stateful source-data resolution,
   while default execution consumes explicit stateless request bundles,
3. primarily consumed through `lotus-gateway`,
4. canonical host runtime is exposed through `manage.dev.lotus`.

Boundary rules:

1. management workflows belong here,
2. proposal and advisor-led flows belong in `lotus-advise` and should not be reintroduced here,
3. host runtime identity and coexistence with `lotus-advise` are part of the operational contract,
4. management capabilities should remain aligned with gateway-facing product expectations,
5. `lotus-core` remains the source-data authority for core-referenced portfolio, market-data, price, and FX inputs,
6. REST/OpenAPI remains the canonical integration contract; gRPC is not justified for current management workflows.

## Repo-Native Commands

Use these commands as the primary local contract:

1. install
   `make install`
2. fast local gate
   `make check`
3. PR-grade local gate
   `make ci`
4. feature-lane local gate
   `make ci-local`
5. Docker parity
   `make ci-local-docker`
6. canonical host runtime
   `make run-canonical`
7. domain-data-product contract validation
   `make domain-product-validate`

## Validation And CI Expectations

`lotus-manage` uses explicit CI lanes:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Important validation expectations:

1. no-alias, OpenAPI, API vocabulary, migration smoke, and security audit are active,
2. PR-grade validation includes coverage-backed full test execution,
3. host/runtime coexistence assumptions matter for canonical front-office startup,
4. README changes should preserve the local Docker runtime contract language enforced by
   `tests/unit/test_local_docker_runtime_contract.py`,
5. DPM supportability and OpenAPI-facing docs changes should respect the targeted contract tests in
   `tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py`,
6. current operational evidence docs under `docs/demo/` and runbooks should preserve canonical
   `lotus-manage` service, image, and ingress identity while clearly labeling historical local-only
   debug paths.
7. RFC/docs/wiki/context work must include stranded-truth reconciliation before RFC start, final
   closure, post-merge audit, and move-on to the next RFC. Run `git fetch origin --prune` and
   `git branch -r --no-merged origin/main`, inspect unmerged branches touching `docs/rfcs/`,
   `wiki/`, `README.md`, `REPOSITORY-ENGINEERING-CONTEXT.md`, `AGENTS.md`, contracts, standards,
   OpenAPI/vocabulary, migrations, CI workflows, or supported-features material, and classify each
   branch as `must-merge`, `cherry-pick`, `superseded`, `delete`, or `active`. This is mandatory
   because RFC-0036 through RFC-0042 work previously exposed a failure mode where
   `docs/rfcs/RFC-worktobedone.md` and an RFC-0041 post-closure documentation correction were
   stranded on unmerged side branches instead of reaching `main`.

## Standards And RFCs That Govern This Repository

Most relevant current governance:

1. `../lotus-platform/rfcs/RFC-0066-lotus-advise-to-lotus-advise-and-lotus-manage-split.md`
2. `../lotus-platform/rfcs/RFC-0067-centralized-api-vocabulary-inventory-and-openapi-documentation-governance.md`
3. `../lotus-platform/rfcs/RFC-0071-centralized-environment-scoped-service-addressing-and-ingress-governance.md`
4. `../lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`
5. `../lotus-platform/rfcs/RFC-0073-lotus-ecosystem-engineering-context-and-agent-guidance-system.md`
6. `../lotus-platform/rfcs/RFC-0082-lotus-core-domain-authority-and-analytics-serving-boundary-hardening.md`
7. `docs/standards/RFC-0082-upstream-contract-family-map.md`

## Known Constraints And Implementation Notes

1. management/advisory boundary clarity remains a real quality concern after the split,
2. canonical local host runtime matters because port coexistence with `lotus-advise` is intentional,
3. local `pip check` and project-scoped security posture still matter for repo truth here,
4. stateful `portfolio_id` mode is disabled by default through
   `DPM_STATEFUL_CORE_SOURCING_ENABLED=false`; integration capabilities must not publish
   `stateful` unless `DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED=true`,
   `DPM_STATEFUL_CORE_SOURCING_ENABLED=true`, `DPM_CORE_BASE_URL` is configured, and any configured
   core resolver path is not the retired monolithic `dpm-execution-context` route,
5. `DpmModelPortfolioTarget:v1`, `DiscretionaryMandateBinding:v1`,
   `InstrumentEligibilityProfile:v1`, `PortfolioTaxLotWindow:v1`,
   `MarketDataCoverageWindow:v1`, and `DpmSourceReadiness:v1` are the core source products used to
   prove stateful manage execution against the canonical mandate portfolio,
6. this repo should stay operationally aligned with gateway and platform startup sequences,
7. repo-local `wiki/` content should stay concise, operator-focused, and derived from repo truth
   rather than duplicating the full `docs/` tree,
8. enterprise audit and readiness surfaces must emit `lotus-manage` service identity rather than
   stale split-era names,
9. `make check` may refresh generated API vocabulary output; docs-only slices should inspect that
   diff and avoid committing timestamp-only churn when the semantic inventory is unchanged,
10. the current repo-native domain-data-product declaration intentionally records only governed
    `PortfolioStateSnapshot` input consumption through caller-supplied management request payloads;
    market-data and future stateful `portfolio_id` resolution must be added only after upstream
    producer approval and an explicit source-data retrieval design.
11. target-state RFC-0037 through RFC-0043 work may redesign or remove stale manage APIs because
    no production downstream dependency is assumed for the revamp surface. Any downstream usage
    discovered during implementation should be documented and migrated to the certified target
    contract rather than preserved through permanent compatibility aliases.
12. durable RFC control artifacts such as `docs/rfcs/RFC-worktobedone.md`, source maps, proof
    indexes, and supported-feature ledgers must be referenced from stable navigation docs and pinned
    by `tests/unit/test_documentation_current_state.py` or an equivalent docs/current-state test
    whenever practical.

## Context Maintenance Rule

Update this document when:

1. management workflow ownership changes,
2. runtime or coexistence assumptions with `lotus-advise` change,
3. repo-native commands or CI expectations change,
4. upstream or downstream integration posture changes materially,
5. RFC-0082 contract-family classification changes,
6. current-state rollout posture changes,
7. README or `wiki/` structure changes the repository-local onboarding or operator navigation model.

## Cross-Links

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`
4. `../lotus-platform/context/Repository-Engineering-Context-Contract.md`
5. [Lotus Developer Onboarding](../lotus-platform/docs/onboarding/LOTUS-DEVELOPER-ONBOARDING.md)
6. [Lotus Agent Ramp-Up](../lotus-platform/docs/onboarding/LOTUS-AGENT-RAMP-UP.md)
