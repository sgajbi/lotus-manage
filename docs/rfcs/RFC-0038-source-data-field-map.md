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
| `investment_objective` | Not yet available | Explicit default `LONG_TERM_TOTAL_RETURN` plus field gap code. | `MandateObjectiveProfile:v1` or enhancement to mandate binding. |
| `time_horizon` | `DiscretionaryMandateBinding:v1.investment_horizon` | Source-backed and normalized to uppercase. | None. |
| `model_portfolio_id` | `DiscretionaryMandateBinding:v1.model_portfolio_id` | Source-backed. | None. |
| `model_portfolio_version` | `DpmModelPortfolioTarget:v1.model_portfolio_version` | Source-backed. | None. |
| `benchmark_id` | Not yet available | Nullable; not synthesized. | Core benchmark binding or performance benchmark source product. |
| `constraints.cash_band_min_weight` | `DiscretionaryMandateBinding:v1.rebalance_bands.cash_reserve_weight` | Source-backed. | None for MVP. |
| `constraints.cash_band_max_weight` | Derived from cash reserve with conservative default | Local policy fallback set to at least `0.10`. | Needs explicit mandate cash-band source. |
| `constraints.turnover_budget` | Not yet available | Local policy fallback `0.15`. | Policy-pack or mandate restriction source should own this. |
| concentration, tax, tracking-error, active-share limits | Not yet available | Nullable, not invented. | Needs mandate restriction/profile products. |
| restricted instruments/issuers/sectors | Not yet available | Empty list with gap code; health input can still receive explicit restricted holdings. | `ClientRestrictionProfile:v1`. |
| sustainability exclusions | Not yet available | Empty list with gap code. | `SustainabilityPreferenceProfile:v1`. |
| review frequency | `DiscretionaryMandateBinding:v1.rebalance_frequency` | Source-backed and normalized to uppercase. | Need separate review cadence if different from rebalance cadence. |
| last/next review dates | Not yet available | Nullable, not invented. | `MandateObjectiveProfile:v1` or mandate operations source. |
| source lineage | Core source product lineage fields | Preserved as `DpmSourceProductLineage`. | None for source-backed products. |

## Health Engine Source Map

| Health dimension | Current inputs | Behavior in Slice 1 | Future enrichment |
| --- | --- | --- | --- |
| `SOURCE_READINESS` | Source-readiness state, missing/degraded/stale families, market-data coverage supportability | `INCOMPLETE`/`UNAVAILABLE` or missing source families block; degraded/stale source families create pending review. | Direct `DpmSourceReadiness:v1` integration in API slice. |
| `ALLOCATION_DRIFT` | Current and target instrument weights | Computes max absolute instrument drift against the initial 2.5% attention band. Missing weights create pending review, not a false ready state. | Band-aware drift from model target min/max and asset-class policy bands. |
| `RISK_DRIFT` | Tracking error plus mandate max tracking-error when available | Ready when risk enrichment is absent; pending review when supplied tracking error breaches supplied threshold. | `lotus-risk` enrichment and benchmark-aware risk decomposition. |
| `CASH_LIQUIDITY` | Cash weight and mandate cash band | Pending review when below or above band. | Cashflow forecast, settlement ladder, income need, overdraft risk. |
| `TAX_TURNOVER` | Missing tax-lot securities and turnover budget usage | Missing tax lots block; turnover usage above 80% of budget creates pending review. | Tax budget source, realized gain forecast, wash-sale/local tax rules where applicable. |
| `ELIGIBILITY_RESTRICTIONS` | Restricted held instruments and mandate restricted instruments | Restricted holdings block. | Client restriction, issuer, sector, ESG and product-shelf rationale. |
| `PERFORMANCE_ATTENTION` | Explicit performance-under-review flag | Pending review when flagged; otherwise neutral until performance enrichment exists. | `lotus-performance` benchmark-relative underperformance and attribution flags. |
| `WORKFLOW_READINESS` | Workflow blocked / approval required flags | Blocked workflows block; approval required creates pending review. | Persisted workflow-gate integration in API slice. |
| `REVIEW_CADENCE` | Next review due date when available | Overdue review creates pending review. | Core mandate review schedule or manage-owned review workflow. |
| `MODEL_FRESHNESS` | Model effective end date when available | Expired model creates pending review. | CIO model-change events and model approval lifecycle. |

## Explicit Core Enhancement Candidates

The following source products remain valid candidates from RFC-0038 Section 4.2:

1. `MandateObjectiveProfile:v1`
2. `ClientRestrictionProfile:v1`
3. `SustainabilityPreferenceProfile:v1`
4. `PortfolioCashflowForecast:v1`
5. `ModelChangeEvent:v1`

They are not blockers for Slice 1 because the pure engine records field gaps and does not claim
those dimensions as source-backed. They become important before API/live-proof slices can be
promoted to full supported features.
