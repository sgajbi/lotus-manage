# Lotus Manage Domain Data Product Declarations

This directory stores `lotus-manage` repo-native declarations for governed Lotus domain data
products.

`lotus-manage` owns discretionary portfolio-management execution and supportability. It does not
own canonical portfolio ledger state, market-data source truth, performance analytics, risk
analytics, advisory-only workflows, reporting, or UI composition.

Current declarations:

1. `lotus-manage-consumers.v1.json`
   Consumer declaration for governed `lotus-core` products used by management execution workflows.
   It includes the request-payload `PortfolioStateSnapshot:v1` dependency, stateful
   `DpmModelPortfolioTarget:v1`, `DiscretionaryMandateBinding:v1`,
   `InstrumentEligibilityProfile:v1`, `PortfolioTaxLotWindow:v1`,
   `MarketDataCoverageWindow:v1`, and `DpmSourceReadiness:v1` dependencies used by stateful
   source-backed execution, mandate
   health, source readiness, and tax/market-data supportability,
   `ClientRestrictionProfile:v1` / `SustainabilityPreferenceProfile:v1` dependencies used by
   ESG/restriction-aware construction and proof-pack source preservation, the
   `PortfolioCashflowProjection:v1`, `ClientIncomeNeedsSchedule:v1`,
   `LiquidityReserveRequirement:v1`, and `PlannedWithdrawalSchedule:v1` dependencies used for
   bounded cash/liquidity reference evidence, and the
   `lotus-risk:RiskEventAffectedCohort:v1` API-read dependency used by source-owned
   risk-event rebalance waves, plus the `lotus-advise:TacticalHouseViewAffectedCohort:v1`
   API-read dependency used by Advise-owned tactical house-view rebalance waves. It also declares
   `lotus-core:CioModelChangeAffectedCohort:v1` for source-owned CIO model-change wave
   discovery, `lotus-core:TransactionCostCurve:v1` for source-owned observed cost evidence,
   `lotus-risk:RegimeScenarioPackEvaluation:v1` for source-owned regime-stress evidence, and
   the `lotus-core:PortfolioManagerBookMembership:v1` API-read dependency used by PM-book
   rebalance-wave discovery and optional PM operating quality score-run scope materialization, and
   `lotus-core:DpmPortfolioUniverseCandidate:v1` for bounded source-owned
   `BULK_REVIEW_CAMPAIGN` candidate discovery with fail-closed empty/truncated page handling, and
   the caller-supplied `lotus-risk:MandateRiskHealthContext:v1` and
   `lotus-performance:MandatePerformanceHealthContext:v1` dependencies used to preserve
   source-owned mandate risk/performance health posture in recalculated mandate-health snapshots
   without local risk or performance methodology ownership, and
   the stateful `lotus-core:ExternalCurrencyExposure:v1`, `ExternalHedgePolicy:v1`,
   `ExternalEligibleHedgeInstrument:v1`, `ExternalFXForwardCurve:v1`, and
   `ExternalHedgeExecutionReadiness:v1` dependencies used to preserve fail-closed external
   treasury exposure, policy, eligible-instrument, forward-curve, and readiness posture in
   currency-overlay diagnostics, plus `ExternalOrderExecutionAcknowledgement:v1` for fail-closed
   external OMS acknowledgement boundary evidence.
2. `lotus-manage-products.v1.json`
   Producer declaration for `lotus-manage:PortfolioActionRegister:v1`, surfaced through the
   implemented rebalance supportability, not-certified `lotus-idea` action-intake
   route-foundation, artifact, and workflow route families, and
   `lotus-manage:BulkReviewCampaignMembership:v1`, surfaced through bounded
   `BULK_REVIEW_CAMPAIGN` rebalance wave preview/create over source-backed candidate portfolios
   with optional approval/expiry/actor-entitlement governance evidence and optional persisted
   `BulkReviewCampaignDefinition:v1` definitions,
   and `lotus-manage:PmOperatingQualityScoreRun:v1`, surfaced through immutable PM operating
   quality policy administration, bank approval and fairness-review governance evidence, optional
   source-owned PM-book scope evidence, preview, create/read/list score-run lifecycle,
   review-action ledger, and summary-invocation history routes. The scoring and fairness
   methodology is published at
   `docs/methodologies/pm-quality/scoring-and-fairness.md`.

Local validation:

```powershell
python scripts/validate_domain_data_product_contracts.py
```

Make target:

```powershell
make domain-product-validate
```

Trust telemetry validation:

```powershell
make trust-telemetry-validate
```

Repo-native trust telemetry snapshots must cover every active producer declaration. Current
snapshots are:

1. `contracts/trust-telemetry/portfolio-action-register.telemetry.v1.json`
2. `contracts/trust-telemetry/bulk-review-campaign-membership.telemetry.v1.json`
3. `contracts/trust-telemetry/pm-operating-quality-score-run.telemetry.v1.json`

These snapshots are deterministic contract fixtures validated by the feature and PR-merge lanes.
They do not by themselves assert live-environment runtime certification.
The PM operating quality snapshot is intentionally `blocked`/`quality_blocked` and operator-only
until linked PM-quality certification blockers are merged to `main` and runtime trust evidence is
regenerated; do not treat active product declaration coverage as customer-reliance readiness.

Consumer adapter rule:

Core and Risk source-product response mappings fail closed before domain model construction. Core
portfolio snapshots must provide portfolio identity, business date, valuation currency,
`positions_baseline`, `portfolio_totals`, row identifiers, explicit quantities, row currencies, and
position market values. Risk concentration, regime-scenario, and risk-event cohort responses must
provide source metadata, product/version or methodology version, request fingerprint,
supportability, and required numeric measures. Explicit source-supplied zero values are valid;
omitted values must not be represented as `USD`, `v1`, an empty fingerprint, an empty section, or a
zero measure.

Full mesh contract validation:

```powershell
make mesh-contract-validate
```

Current watchlist:

1. `lotus-manage` stateful source consumption must stay aligned with certified producer
   declarations. New source products should be added here only after source-owner approval,
   trust metadata, tests, and live proof exist.
2. Market-data request payloads remain source-data-authority sensitive, but raw `MarketDataWindow`
   is not currently approved for `lotus-manage` in the upstream producer declaration. Manage
   declares only the bounded `MarketDataCoverageWindow:v1` supportability product and must not
   treat it as raw market-data or valuation-methodology ownership.
3. `BenchmarkAssignment:v1` is approved for bounded `lotus-manage` benchmark-identity lineage
   consumption only. Manage preserves only active assignments; missing, unavailable, incomplete, or
   non-active assignments remain explicit degraded source posture through
   `BENCHMARK_ASSIGNMENT_NOT_YET_SOURCED`. Keep benchmark composition, active-risk, performance
   attribution, benchmark analytics, and model-approval methodology in their owning source
   services.
4. The `lotus-idea` action-intake route is route-foundation evidence only. It clears the
   cross-repo missing-route proof when validated by `lotus-idea`, but it does not persist an action
   register row, grant rebalance authority, create orders, authorize client publication, or promote
   a supported feature.
