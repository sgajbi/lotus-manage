# RFC-0038 Source-Data Field Map

This document is the Slice 0 evidence map for RFC-0038. It records what the first mandate digital
twin and health-engine implementation can source from current `lotus-core` RFC-087 products, what
is derived in `lotus-manage`, and what remains an explicit source-data gap for later core or
enrichment work.

The rule for RFC-0038 is strict: no mandate field may be silently invented. Every field must be
classified as source-backed, derived, local policy, or a known gap.

## Minimum Viable Mandate Twin

| Twin field | Current source | Current implementation | Gap posture |
| --- | --- | --- | --- |
| `mandate_id` | `DiscretionaryMandateBinding:v1.mandate_id` | Source-backed in `compile_mandate_digital_twin_from_core`. | None. |
| `portfolio_id` | `DiscretionaryMandateBinding:v1.portfolio_id` | Source-backed. | None. |
| `mandate_version` | `DiscretionaryMandateBinding:v1.binding_version` | Source-backed as a string version. | None. |
| `as_of_date` | Caller/business date used for source resolution | Source-backed by resolver call context. | None. |
| `source_system` | Source product authority | Fixed to `lotus-core` because mandate and model source products come from core. | None. |
| `base_currency` | `DpmModelPortfolioTarget:v1.base_currency` | Source-backed. | Confirm whether portfolio base currency and model base currency can diverge in future. |
| `reference_currency` | Caller override or model base currency | Derived fallback. | Needs dedicated client reference-currency source if it differs from model currency. |
| `risk_profile` | `DiscretionaryMandateBinding:v1.risk_profile` | Source-backed and normalized to uppercase. | None. |
| `investment_objective` | `DiscretionaryMandateBinding:v1.mandate_objective` when available | Source-backed from the core mandate administration binding; falls back to `LONG_TERM_TOTAL_RETURN` only with explicit `MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED`. | None for first-wave mandate objective. |
| `time_horizon` | `DiscretionaryMandateBinding:v1.investment_horizon` | Source-backed and normalized to uppercase. | None. |
| `model_portfolio_id` | `DiscretionaryMandateBinding:v1.model_portfolio_id` | Source-backed. | None. |
| `model_portfolio_version` | `DpmModelPortfolioTarget:v1.model_portfolio_version` | Source-backed. | None. |
| `benchmark_id` | `BenchmarkAssignment:v1.benchmark_id` when available | Source-backed from core benchmark assignment; nullable only when the optional source product is unavailable. | Performance benchmark analytics remain future enrichment. |
| `constraints.cash_band_min_weight` | `DiscretionaryMandateBinding:v1.rebalance_bands.cash_reserve_weight` | Source-backed. | None for MVP. |
| `constraints.cash_band_max_weight` | Derived from cash reserve with conservative default | Local policy fallback set to at least `0.10`. | Needs explicit mandate cash-band source. |
| `constraints.turnover_budget` | Not yet available | Local policy fallback `0.15`. | Policy-pack or mandate restriction source should own this. |
| concentration, tax, tracking-error, active-share limits | Not yet available | Nullable, not invented. | Needs mandate restriction/profile products. |
| restricted instruments/issuers/sectors | `ClientRestrictionProfile:v1` when the source product is available | Active instrument-level client restrictions are preserved on the twin and assessed against active model targets in mandate health. Missing profiles remain explicit gap codes. | Issuer, sector, country, and product taxonomy restriction matching remain future enrichment unless source products provide security-level joins. |
| sustainability preferences | `SustainabilityPreferenceProfile:v1` when the source product is available | Active preference framework and bounded preference codes are preserved on the twin. Allocation bands, exclusions, and positive tilts trigger `SUSTAINABILITY_REVIEW_REQUIRED` rather than automatic ESG approval. | Security-level sustainability classification and regulatory suitability approval remain source-owner follow-up. |
| review frequency | `DiscretionaryMandateBinding:v1.review_cadence` with `rebalance_frequency` fallback | Source-backed and normalized to uppercase. Fallback remains gap-coded with `MANDATE_REVIEW_SCHEDULE_NOT_YET_SOURCED`. | None for first-wave review cadence. |
| last review date | `DiscretionaryMandateBinding:v1.last_review_date` | Source-backed when returned by core. | None for first-wave review-date evidence. |
| next review due date | `DiscretionaryMandateBinding:v1.next_review_due_date` | Source-backed when returned by core and used by mandate health review-cadence scoring. | None for first-wave review-date evidence. |
| source lineage | Core source product lineage fields | Preserved as `DpmSourceProductLineage`. | None for source-backed products. |

## Health Engine Source Map

| Health dimension | Current inputs | Behavior in Slice 1 | Future enrichment |
| --- | --- | --- | --- |
| `SOURCE_READINESS` | Source-readiness state, missing/degraded/stale families, market-data coverage supportability | `INCOMPLETE`/`UNAVAILABLE` or missing source families block; degraded/stale source families create pending review. | Direct `DpmSourceReadiness:v1` integration in API slice. |
| `ALLOCATION_DRIFT` | Current and target instrument weights | Computes max absolute instrument drift against the initial 2.5% attention band. Missing weights create pending review, not a false ready state. | Band-aware drift from model target min/max and asset-class policy bands. |
| `RISK_DRIFT` | Tracking error plus mandate max tracking-error when available | Ready when risk enrichment is absent; pending review when supplied tracking error breaches supplied threshold. | `lotus-risk` enrichment and benchmark-aware risk decomposition. |
| `CASH_LIQUIDITY` | Cash weight, mandate cash band, and optional `PortfolioCashflowProjection:v1.total_net_cashflow` | Pending review when below/above band. Negative source-owned projected net cashflow creates `PROJECTED_CASHFLOW_PRESSURE` when current cash is within band. | Client income-need profile, settlement ladder, overdraft risk, and richer horizon semantics. |
| `TAX_TURNOVER` | Missing tax-lot securities and turnover budget usage | Missing tax lots block; turnover usage above 80% of budget creates pending review. | Tax budget source, realized gain forecast, wash-sale/local tax rules where applicable. |
| `ELIGIBILITY_RESTRICTIONS` | Restricted held instruments, mandate restricted instruments, and optional `ClientRestrictionProfile:v1` active buy restrictions | Restricted holdings and restricted active model targets block with `RESTRICTED_INSTRUMENT_HELD`. | Issuer, sector, ESG and product-shelf rationale. |
| `PERFORMANCE_ATTENTION` | Explicit performance-under-review flag | Pending review when flagged; otherwise neutral until performance enrichment exists. | `lotus-performance` benchmark-relative underperformance and attribution flags. |
| `WORKFLOW_READINESS` | Workflow blocked / approval required flags and optional `SustainabilityPreferenceProfile:v1` review posture | Blocked workflows block; approval required and sustainability review requirements create pending review. | Persisted workflow-gate integration and source-owner sustainability classification. |
| `REVIEW_CADENCE` | `DiscretionaryMandateBinding:v1.next_review_due_date` | Overdue review creates pending review. | Manage-owned review workflow remains a future operational workflow; source date evidence is now core-backed. |
| `MODEL_FRESHNESS` | Model effective end date when available | Expired model creates pending review. | CIO model-change events and model approval lifecycle. |

## Explicit Core Enhancement Candidates

The following source products remain valid candidates from RFC-0038 Section 4.2:

1. Manage-owned review workflow history beyond source review dates.
2. `ClientRestrictionProfile:v1` - implemented for active instrument-level restriction preservation
   and model-target health blocking.
3. `SustainabilityPreferenceProfile:v1` - implemented for preference preservation and bounded
   review-required posture.
4. `PortfolioCashflowProjection:v1` - implemented for projected net-cashflow pressure; a separate
   client income-need profile is still not sourced.
5. `ModelChangeEvent:v1`

They are not blockers for Slice 1 because the pure engine records field gaps and does not claim
those dimensions as source-backed. They become important before API/live-proof slices can be
promoted to full supported features.
