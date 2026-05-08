# RFC-0039 Source-Data And Method Map

This document is the Slice 0 evidence map for RFC-0039. It records the first implementation wave
for advanced discretionary portfolio construction alternatives, what the current `lotus-manage`
engine can reuse, which upstream products own each input, and which gaps must remain explicit
instead of being silently patched inside manage.

The rule for RFC-0039 is strict: no construction alternative may claim a `READY` posture for a
dimension whose required source data is missing, stale, incomplete, or owned by another Lotus app
and unavailable. The implementation may degrade, block, or omit a method, but it must not fabricate
risk, performance, ESG, tax, market-data, or portfolio-source truth.

## Slice 0 Result

| Slice 0 requirement | Result |
| --- | --- |
| Field-by-field source map exists | This document is the governed map for first-wave and authority-backed construction alternatives. |
| First-wave method list is explicit | `DO_NOTHING_BASELINE`, `HEURISTIC_EXPLAINABLE`, `MIN_TURNOVER`, and `TAX_AWARE` are the first wave. |
| Current engine and solver capability is verified | Existing rebalance engine supports heuristic and solver target generation, turnover caps, tax-aware HIFO-style lot allocation, FX funding, settlement awareness, rule evaluation, diagnostics, and workflow gates. Solver support is optional through `cvxpy`/`numpy` and must remain an explicit posture, not a hidden dependency. |
| Missing upstream fields are listed by owner | Missing fields are listed in this map by source owner and must not be locally invented. |
| Method semantics are unambiguous before implementation | Each first-wave and authority-backed method has a bounded purpose, required data posture, comparison metrics, fallback/degraded behavior, and source-authority evidence. |

## First-Wave Method Set

| Method | Business purpose | Reused current capability | Additional implementation needed | Support promotion gate |
| --- | --- | --- | --- | --- |
| `DO_NOTHING_BASELINE` | Let PMs compare active construction against staying invested as-is. | Existing valuation, rules, diagnostics, mandate health/twin context, and before-state simulation. | Add first-class alternative model with no trade intents, current-state drift metrics, rule posture, and reason code `baseline_no_action`. | Must show no trades, unchanged after-state, current drift, breaches, cash posture, and source readiness. |
| `HEURISTIC_EXPLAINABLE` | Preserve deterministic target-difference rebalance as a transparent baseline. | `src/core/rebalance/engine.py`, `targets.py`, `intents.py`, `execution.py`, diagnostics, rule results, gate decision. | Wrap current simulation as a construction alternative with objective terms, constraint trace, and normalized comparison metrics. | Must expose capping, suppression, funding, blocking, lot-selection, and workflow reason codes. |
| `MIN_TURNOVER` | Reduce material drift while minimizing trading, cost, and operational burden. | Current turnover scoring and `max_turnover_pct` controls in `src/core/rebalance/turnover.py`; scenario comparison in analyze endpoint. | Add a first-class method that optimizes the trade list for turnover and compares drift reduction versus trade count/cost. | Must show turnover weight, trade count, drift before/after, dropped intents, and cost estimate. |
| `TAX_AWARE` | Reduce realized gains within mandate or policy tax budget. | Current tax-aware sell allocation using position tax lots and `max_realized_capital_gains`. Core tax lots are available through `PortfolioTaxLotWindow:v1`. | Add method-level tax supportability, lot-selection trace, realized-gain/loss comparison, and missing-lot degraded/block posture. | Must be blocked or degraded when required tax lots are unavailable; no fabricated tax impact. |

## Authority-Backed Advanced Method Set

| Method | Business purpose | Source authority | Support promotion gate |
| --- | --- | --- | --- |
| `SOLVER_CONSTRAINED` | Use mathematical optimization where it improves construction discipline without hiding infeasibility. | Manage-owned solver registry and target-generation engine. | Solver availability, target-method comparison, fallback, warning taxonomy, and objective/constraint traces are explicit. |
| `RISK_AWARE` | Control concentration risk using risk-owned supportability and concentration output. | `lotus-risk` `/analytics/risk/concentration`. | Manage consumes risk output through the bounded risk-authority client; it does not recalculate risk methodology locally. |
| `LIQUIDITY_AWARE` | Preserve funding, settlement, cash-buffer, projected cash-pressure, and blocked-action posture. | Manage settlement engine plus core-sourced cash/liquidity fields and optional `PortfolioCashflowProjection:v1` evidence. | Cash ladder, funding deficits, minimum cash buffer, liquidity-policy context, and source-owned cashflow projection posture are in diagnostics. |
| `CURRENCY_OVERLAY` | Govern non-base currency exposure using FX readiness and currency policy context. | Core/market-data FX spot plus manage currency-overlay policy context until treasury hedge products exist. | Missing FX blocks; eligible-currency and hedge-ratio policy context are explicit; no non-base exposure degrades truthfully. |
| `REGIME_STRESS_AWARE` | Compare construction against source-backed scenario-pack loss tolerance. | `lotus-risk` `RegimeScenarioPackEvaluation:v1` / CIO scenario pack authority context. | Scenario pack id, source system, worst-case loss, policy loss threshold, and reason codes are present; excess loss is pending review. |

`ESG_AWARE` and broader restriction-aware construction remain explicitly deferred until
`ClientRestrictionProfile:v1` and `SustainabilityPreferenceProfile:v1` or equivalent source-backed
products exist. The method must degrade with `ESG_RESTRICTION_AWARE_CONSTRUCTION_DEFERRED`; it must
not infer sustainability suitability from shelf labels alone.

## Current Engine Capability Baseline

| Capability | Current implementation evidence | RFC-0039 reuse posture |
| --- | --- | --- |
| Heuristic target generation | `src/core/rebalance/targets.py::generate_targets_heuristic` | Reuse as `HEURISTIC_EXPLAINABLE`; add alternative wrapper and trace normalization. |
| Optional solver target generation | `src/core/target_generation.py::generate_targets_solver`; optional dependencies `cvxpy` and `numpy` | Reuse only behind explicit solver availability and fallback posture. |
| Target method comparison | `src/core/rebalance/targets.py::compare_target_generation_methods` | Reuse as diagnostic inspiration; RFC-0039 needs comparable persisted alternatives, not only primary/alternate diagnostics. |
| Turnover control | `src/core/rebalance/turnover.py` | Reuse for `MIN_TURNOVER`; extend into method-level objective and comparison metrics. |
| Tax-aware sell allocation | `src/core/rebalance/intents.py` plus `PortfolioSnapshot.positions[].lots` | Reuse for `TAX_AWARE`; add tax supportability, lot trace, and missing-lot posture. |
| FX funding and settlement awareness | `src/core/rebalance/execution.py` and `EngineOptions.enable_settlement_awareness` | Reuse for `LIQUIDITY_AWARE` and `CURRENCY_OVERLAY`; hedge-specific execution remains future treasury/source-product depth, not a blocker for policy-backed overlay supportability. |
| Rule evaluation and workflow gates | `src/core/compliance.py`, `src/core/common/workflow_gates.py` | Reuse for blocked/pending review status and selected-alternative action gating. |
| Stateful core sourcing | `src/infrastructure/core_sourcing/client.py` | Reuse current composed RFC-087 products; no monolithic DPM context endpoint. |
| Mandate twin and health | `src/core/mandates.py`, mandate repository, mandate API services | Reuse for mandate constraints, source readiness, and construction context; do not duplicate health scoring. |

## Source-Data Field Map

| Field family | Required fields | Source authority | Current Lotus source | Manage behavior | Missing/gap posture |
| --- | --- | --- | --- | --- | --- |
| Portfolio identity | `portfolio_id`, `tenant_id`, `booking_center_code`, `as_of_date` | `lotus-core` for stateful source; caller for stateless request | `DpmStatefulInput`, `DiscretionaryMandateBinding:v1`, `PortfolioStateSnapshot/CoreSnapshot` | Preserve selectors and lineage; reject ambiguous stateful selector. | None for first wave when stateful gates are enabled and core is configured. |
| Holdings and cash | positions, quantities, cash balances, base currency, snapshot id | `lotus-core` for stateful source; caller for stateless request | `/integration/portfolios/{portfolio_id}/core-snapshot` transformed into `PortfolioSnapshot` | Use for valuation, drift, liquidity, cash, and no-action baseline. | Must block or degrade when required holdings or base currency are unavailable. |
| Prices and FX spot | instrument prices, local currency, valuation currency, FX pairs | `lotus-core` | `MarketDataCoverageWindow:v1` through `/integration/market-data/coverage` | Use for valuation, funding, turnover notional, cash, and FX diagnostics. | Missing price/FX follows existing `block_on_missing_prices` and `block_on_missing_fx` behavior; no stale valuation fabrication. |
| Model targets | model id/version, instrument target weights, target bands where available | `lotus-core` and CIO/model governance | `DpmModelPortfolioTarget:v1` | Use as target objective for heuristic, min-turnover, and optional solver methods. | Target bands exist where core provides them; asset-class/model-level band semantics remain a future enrichment if not present. |
| Mandate binding | mandate id/version, model binding, risk profile, horizon, tax-awareness allowed, rebalance bands, policy pack | `lotus-core` | `DiscretionaryMandateBinding:v1`; mandate digital twin derived in manage | Use for method eligibility, cash bands, policy selection, and trace context. | Dedicated objective profile, review dates, benchmark, explicit turnover budget, and client restrictions are still gaps unless supplied by policy pack or later core products. |
| Instrument eligibility | buy/sell permission, shelf status, restriction reasons, settlement days, liquidity tier, issuer, asset class, country of risk | `lotus-core` | `InstrumentEligibilityProfile:v1` through `/integration/instruments/eligibility-bulk` | Use for universe, restriction blocks, liquidity diagnostics, and group/concentration traces. | ESG labels, sustainability preference fit, and deeper product governance are gaps for ESG-aware methods. |
| Tax lots | lot id, open quantity, acquisition date, cost basis, local/base currency, status, source transaction id | `lotus-core` | `PortfolioTaxLotWindow:v1` through `/integration/portfolios/{portfolio_id}/tax-lots` | Use for `TAX_AWARE` lot selection and tax impact. | Tax budget source, jurisdiction-specific rules, wash-sale/local tax treatment, and closed-lot history are not first-wave source-backed. |
| Liquidity and settlement | liquidity tier, settlement days/calendar, cash balances, cash ladder, minimum cash buffer, source-owned total net cashflow projection | `lotus-core` for security liquidity, cash, and `PortfolioCashflowProjection:v1`; manage derives settlement ladder and policy posture | Eligibility product plus existing settlement-aware engine plus optional cashflow projection context | Use for liquidity-aware supportability, blockers, and pending-review posture. Source-owned negative projected cashflow can move an otherwise ready alternative to pending review when adjusted cash would breach policy. | Client income-need and liability-planning source products remain future depth; absence does not justify fabricating income needs. |
| Transaction cost | estimated spread/commission/market-impact per instrument | Future source product or platform cost service | Not currently available as authoritative source | Use documented local approximation only if clearly labelled as estimated construction diagnostic. | Authoritative transaction-cost curve/product is missing. |
| Risk context | tracking error, volatility, stress, concentration, drawdown, risk contribution | `lotus-risk` | `POST /analytics/risk/concentration` through the manage risk-authority client for concentration supportability; caller-supplied authority context for risk fields not yet exposed by a risk endpoint | Consume risk supportability and concentration outputs; fail closed or degrade when risk authority is unavailable. | Do not recompute authoritative risk. Tracking error, volatility, stress contribution, and drawdown remain future risk-authority enrichments unless supplied as source-backed context. |
| Performance context | benchmark id, active return, attribution, realized performance, underperformance flags | `lotus-performance` | Not currently integrated for RFC-0039 alternatives | Preserve enrichment seam and mark missing performance context. | Benchmark binding and performance attention source are missing for first-wave alternatives. |
| ESG and restrictions | sustainability preference, exclusions, ESG ratings, sector controversy, client restriction profile | `lotus-core` or sustainability source product, with product-shelf enforcement in core | Eligibility restrictions are present; full sustainability profile is not | Only use current eligibility/restriction data for first wave. | `SustainabilityPreferenceProfile:v1` and `ClientRestrictionProfile:v1` are required before ESG-aware support promotion. |
| Currency overlay | strategic currency exposure, hedge-ratio bands, forward points, hedging eligibility, settlement evidence | `lotus-core` plus market-data/treasury source | FX spot coverage exists; manage accepts bounded currency-overlay policy context | Use FX readiness, eligible currency set, hedge-ratio bands, and settlement awareness to govern `CURRENCY_OVERLAY`. | Forward curves, hedge instruments, and treasury execution readiness remain future depth. |
| Regime/scenario | named scenario pack, shock vectors, stress result authority | `lotus-risk` / CIO scenario service | `RegimeScenarioPackEvaluation:v1` through `POST /analytics/risk/regime-scenario-pack/evaluate`; manage still accepts caller-supplied source-backed regime-stress authority context | Use scenario pack id, worst-case loss, policy threshold, and reason codes to govern `REGIME_STRESS_AWARE`; when `DPM_RISK_BASE_URL` is configured, manage resolves the source product automatically for the method. | Broader scenario assumptions, approvals, scenario contribution rows, and product-surface display remain future depth; manage must not generate scenario methodology locally. |

## Objective And Constraint Trace Map

| Trace element | First-wave requirement | Source/derivation | Required posture |
| --- | --- | --- | --- |
| `objective_terms.drift` | Present for every alternative. | Manage computes from current weight versus model target weight. | Deterministic decimal calculation with documented tolerance. |
| `objective_terms.turnover` | Present for trade-generating alternatives. | Manage computes from generated security trade notionals versus portfolio value. | Must reconcile to intents and dropped-intent diagnostics. |
| `objective_terms.tax_impact` | Present for tax-aware alternative. | Manage derives from source-backed tax lots and sell allocation. | Must be degraded/blocked if required tax lots are missing. |
| `objective_terms.estimated_cost` | Present only when cost method is implemented. | Local approximation until an authoritative cost source exists. | Must be labelled estimated and methodology-backed. |
| `constraints.cash_band` | Present for all alternatives. | Mandate binding and/or policy pack. | Missing explicit band must be a local policy fallback with reason code. |
| `constraints.eligibility` | Present for all trade-generating alternatives. | Core eligibility profile. | Buy/sell blocked instruments must be traceable. |
| `constraints.tax_budget` | Present for tax-aware alternative when configured. | Policy pack or request option. | Absence must be explicit; no implied tax budget. |
| `constraints.turnover_budget` | Present for min-turnover and configured alternatives. | Policy pack or request option. | Dropped intents must reconcile to budget. |
| `constraints.solver` | Present only for solver method. | Solver registry and runtime. | Solver status, version, tolerance, timeout, infeasibility, and fallback must be explicit. |

## Missing Source Products And Owners

| Missing product or field | Owning app / domain | Required for | RFC-0039 posture |
| --- | --- | --- | --- |
| `MandateObjectiveProfile:v1` | `lotus-core` | objective profile, benchmark binding, review cadence, income need | Not first-wave blocker; required before richer mandate personalization. |
| `ClientRestrictionProfile:v1` | `lotus-core` or client governance source | ESG/restriction-aware alternatives | Required before ESG-aware support promotion. |
| `SustainabilityPreferenceProfile:v1` | `lotus-core` or sustainability source | ESG-aware alternatives | Required before ESG-aware support promotion. |
| `PortfolioCashflowProjection:v1` | `lotus-core` | source-backed projected net-cashflow pressure for liquidity-aware alternatives | First-wave implemented. Manage consumes source-owned total net cashflow, currency, projection window, projected-row posture, freshness, fingerprint, quality status, and reason codes. |
| ClientIncomeNeedProfile / liability-planning source | future source owner | income-need-aware liquidity alternatives | Still deferred. `PortfolioCashflowProjection:v1` is not a client spending, liability, or wealth-planning forecast, so manage must not claim income-need support from projection totals alone. |
| `TransactionCostCurve:v1` | `lotus-core` source authority | proof-pack observed-cost evidence now available; cost-aware and min-cost alternatives still future | Manage can preserve source-owned observed booked-fee evidence in RFC-0040 proof packs. Dedicated cost-aware/min-cost construction must still be implemented and proven before RFC-0039 support promotion; observed curves are not predictive execution quotes. |
| `CurrencyExposurePolicy:v1` | `lotus-core` / treasury policy source | currency overlay alternatives | Future source-product depth; current support accepts explicit currency-overlay authority context and FX readiness. |
| `RiskAlternativeEnrichment:v1` | `lotus-risk` | risk-aware alternatives, stress/drawdown/tracking-error comparison | Future broader risk enrichment; current support consumes `lotus-risk` concentration authority. |
| `PerformanceBenchmarkContext:v1` | `lotus-performance` | benchmark-relative performance context | Required before performance-aware support promotion. |
| `RegimeScenarioPackEvaluation:v1` | `lotus-risk` / CIO scenario authority | regime-stress-aware construction | First-wave implemented. Manage consumes scenario pack id, source service, supportability, worst-case loss, policy threshold, breach reason codes, and source lineage from `POST /analytics/risk/regime-scenario-pack/evaluate` when `DPM_RISK_BASE_URL` is configured. |

## Implementation Guardrails

1. `lotus-manage` owns construction alternatives and selection events, not source data, risk
   analytics, performance analytics, reports, archive, AI, Gateway composition, or Workbench UI.
2. The first API implementation must expose a bounded strategic endpoint family only; no alias
   endpoints should be added for convenience.
3. Source readiness must be carried into alternative-set status and method-level status.
4. Method status must be one of `READY`, `PENDING_REVIEW`, `BLOCKED`, or `DEGRADED`; unsupported
   source data cannot be hidden behind a successful-looking alternative.
5. Solver usage must include a registry posture. If solver dependencies are unavailable, the
   response must say so and identify the fallback method if a fallback was used.
6. Gateway and Workbench realization RFCs must be produced after manage contracts and live evidence
   are stable; this Slice 0 map is not a Gateway or UI integration contract.

