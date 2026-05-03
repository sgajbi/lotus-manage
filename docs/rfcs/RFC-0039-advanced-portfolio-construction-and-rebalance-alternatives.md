# RFC-0039: Advanced Portfolio Construction and Rebalance Alternatives

| Metadata | Details |
| --- | --- |
| **Status** | PROPOSED |
| **Created** | 2026-05-03 |
| **Depends On** | RFC-0008, RFC-0009, RFC-0010, RFC-0011, RFC-0012, RFC-0013, RFC-0022, RFC-0036, RFC-0037, RFC-0038 |
| **Doc Location** | `docs/rfcs/RFC-0039-advanced-portfolio-construction-and-rebalance-alternatives.md` |

---

## 0. Executive Summary

RFC-0039 turns `lotus-manage` from a single-result rebalance engine into a portfolio construction
decision system. The target is to generate, compare, explain, and select multiple rebalance
alternatives for a discretionary mandate, each with transparent trade-offs across drift, risk,
turnover, tax, transaction cost, liquidity, FX, ESG, and mandate constraints.

This is the core analytical differentiator for `lotus-manage`. Large private banks sell DPM as
professional portfolio construction under mandate discipline. This RFC gives Lotus the backend
foundation for that story.

Primary outcome:

1. a PM asks for alternatives for one mandate,
2. `lotus-manage` produces a bounded `DpmRebalanceAlternativeSet`,
3. each alternative has objective, constraints, trades, expected outcomes, reason codes, solver
   trace, feasibility state, and evidence,
4. the selected alternative can flow into proof-pack and workflow APIs in later RFCs.

---

## 1. Current Baseline

Existing `lotus-manage` already has:

1. deterministic rebalance simulation,
2. explicit stateless/stateful execution envelopes,
3. heuristic target generation,
4. solver-capable target generation foundation,
5. tax-lot support through core sourcing,
6. turnover and transaction-cost controls,
7. settlement awareness,
8. what-if analysis,
9. policy-pack configuration,
10. supportability, lineage, idempotency, and artifacts.

Current gaps:

1. one execution request generally produces one primary result,
2. alternatives are not a first-class API/product concept,
3. solver objective and constraint trade-offs are not presented as comparable PM choices,
4. tax, turnover, risk, liquidity, and ESG trade-offs are not normalized into a decision matrix,
5. infeasible or relaxed constraint evidence is not rich enough for PM/CIO/compliance review,
6. `lotus-risk` and `lotus-performance` enrichment is not yet part of construction comparison.

## 1.5 Business Outcomes

This RFC targets the following business outcomes:

1. **Better PM decisions**
   let portfolio managers compare multiple valid paths instead of accepting one generated trade
   plan without understanding trade-offs.
2. **More personalized DPM**
   support different client/mandate priorities such as tax sensitivity, low turnover, liquidity,
   ESG constraints, income needs, and risk reduction.
3. **Higher investment quality**
   bring solver-backed construction, objective functions, and constraint governance into the core
   DPM decision process.
4. **Improved review and approval quality**
   expose why an alternative is selected, why another is rejected, and what constraints or
   relaxations shaped the result.
5. **Stronger client and sales narrative**
   show sophisticated portfolio construction as a visible value proposition, not a hidden engine
   detail.
6. **Reduced unnecessary trading**
   explicitly optimize and compare turnover, costs, tax, and liquidity impact before action.

---

## 2. Goals and Non-Goals

### 2.1 Goals

1. Add first-class rebalance alternative generation.
2. Support multiple construction methods:
   `HEURISTIC_EXPLAINABLE`, `SOLVER_CONSTRAINED`, `MIN_TURNOVER`, `TAX_AWARE`,
   `LIQUIDITY_AWARE`, `RISK_AWARE`, `ESG_AWARE`, `CURRENCY_OVERLAY`,
   `REGIME_STRESS_AWARE`, and `DO_NOTHING_BASELINE`.
3. Produce comparable metrics for each alternative.
4. Persist alternative sets and selected alternatives.
5. Expose solver status, objective terms, constraints, relaxations, infeasibility reasons, and
   fallback decisions.
6. Preserve existing status vocabulary: `READY`, `PENDING_REVIEW`, `BLOCKED`.
7. Prepare selected alternatives for RFC-0040 proof packs and RFC-0041 wave orchestration.

### 2.2 Non-Goals

1. Execute trades.
2. Replace `lotus-risk` as the risk analytics authority.
3. Replace `lotus-performance` as performance authority.
4. Create client proposal or consent workflows.
5. Allow AI to choose alternatives.
6. Guarantee globally optimal portfolio outcomes under all constraints; infeasible and bounded
   fallback behavior must be explicit.

---

## 3. Ownership and Boundaries

`lotus-manage` owns:

1. alternative set orchestration,
2. construction objective registry,
3. constraint registry and mapping to mandate/policy packs,
4. solver invocation and fallback governance,
5. alternative comparison metrics,
6. selection workflow and evidence.

External authorities:

| Authority | Responsibility |
| --- | --- |
| `lotus-core` | portfolio state, tax lots, model targets, eligibility, prices, FX, market coverage, liquidity/reference data when available |
| `lotus-risk` | risk impact, tracking error, concentration, stress, drawdown, factor risk when available |
| `lotus-performance` | benchmark context, realized performance, attribution context |
| `lotus-report` | downstream reporting package generation |
| `lotus-ai` | narrative summaries only, not construction decisions |

---

## 4. Construction Methods

### 4.1 DO_NOTHING_BASELINE

Purpose:

1. compare every action against no action,
2. quantify current drift, risk, cash, tax, and restriction posture,
3. avoid pretending action is always better.

Output expectations:

1. no trade intents,
2. current state as after state,
3. health and rule results preserved,
4. expected drift reduction equals zero.

### 4.2 HEURISTIC_EXPLAINABLE

Purpose:

1. preserve current deterministic baseline,
2. give explainable target-difference logic,
3. act as fallback when solver is unavailable.

Rules:

1. no hidden relaxations,
2. no stochastic behavior,
3. same input produces same output,
4. reason codes must explain capping, suppression, funding, and blocking.

### 4.3 SOLVER_CONSTRAINED

Purpose:

1. optimize against objective function,
2. respect constraints,
3. quantify trade-offs.

Required solver trace:

1. solver engine,
2. solver version,
3. objective terms,
4. constraint set id,
5. time budget,
6. solve status,
7. gap/tolerance where available,
8. relaxed constraints,
9. infeasible constraints,
10. fallback method when used.

### 4.4 MIN_TURNOVER

Purpose:

1. reduce drift while minimizing unnecessary trading,
2. support fee-sensitive or low-activity mandates,
3. reduce operational burden.

Primary metrics:

1. turnover weight,
2. number of trades,
3. drift reduction,
4. expected tracking error after trade.

### 4.5 TAX_AWARE

Purpose:

1. reduce realized gains within tax budget,
2. use available tax-lot windows,
3. flag missing tax lots explicitly.

Lot-selection posture:

1. `HIFO`
2. `LIFO`
3. `FIFO`
4. `MIN_GAIN`
5. `TAX_LOTS_UNAVAILABLE`

No tax-aware alternative may be marked `READY` if required tax lots are missing and the mandate
requires tax-aware execution.

### 4.6 LIQUIDITY_AWARE

Purpose:

1. protect cash buffers,
2. respect known cashflow needs,
3. avoid illiquid trades where liquidity profile is weak,
4. preserve settlement readiness.

Inputs:

1. current cash,
2. settlement ladder,
3. known cashflow forecast when available,
4. instrument liquidity profile when available.

### 4.7 RISK_AWARE

Purpose:

1. reduce or control tracking error,
2. mitigate concentration,
3. avoid increasing drawdown or stress posture beyond mandate limits,
4. use `lotus-risk` enrichment where available.

Risk-aware alternatives may be generated in degraded mode with local concentration metrics, but
must clearly mark missing `lotus-risk` enrichment.

### 4.8 ESG_AWARE

Purpose:

1. apply sustainability exclusions,
2. avoid restricted sectors and issuers,
3. prefer eligible sustainable instruments where mandate requires it,
4. expose ESG degradation when source profiles are incomplete.

### 4.9 CURRENCY_OVERLAY

Purpose:

1. compare unhedged, partially hedged, and fully hedged mandate outcomes,
2. separate strategic currency exposure from operational trade funding,
3. respect currency exposure bands and hedge-ratio bands from the mandate digital twin,
4. avoid creating hedge trades when hedge instruments, FX rates, forward points, settlement
   calendars, or eligibility evidence are missing.

Required evidence:

1. current currency exposure by currency, sleeve, and asset class,
2. target currency exposure after cash funding and proposed trades,
3. proposed hedge adjustments where permitted,
4. residual exposure after hedge,
5. hedge cost estimate and settlement readiness,
6. reason codes for hedge created, hedge changed, hedge suppressed, hedge blocked, and hedge
   degraded.

### 4.10 REGIME_STRESS_AWARE

Purpose:

1. compare alternatives under named market-regime and stress packs,
2. reject or downgrade alternatives that improve drift while materially worsening unacceptable
   downside or concentration risk,
3. support CIO-required scenario checks for model-change waves,
4. expose degraded state when `lotus-risk` scenario packs or exposure inputs are incomplete.

Required evidence:

1. scenario pack id and version,
2. current, target, and after-trade scenario impacts,
3. breached scenario limits,
4. main contributors to scenario loss,
5. mitigation reason codes,
6. risk-authoritative source refs from `lotus-risk`.

---

## 5. Objective Function

The target solver objective is a weighted sum:

```text
minimize:
    w_drift * drift_distance
  + w_tracking_error * tracking_error
  + w_turnover * turnover
  + w_cost * transaction_cost
  + w_tax * realized_tax
  + w_cash * cash_band_penalty
  + w_liquidity * liquidity_penalty
  + w_esg * esg_penalty
  + w_concentration * concentration_penalty
  + w_currency_overlay * currency_overlay_penalty
  + w_scenario_loss * scenario_loss_penalty
```

Objective weights come from:

1. mandate digital twin,
2. policy pack,
3. construction method default,
4. explicit request override where allowed.

Every objective term must be exposed in the alternative trace.

---

## 6. Constraint Registry

Initial constraint families:

1. `ASSET_CLASS_BAND`
2. `INSTRUMENT_WEIGHT_MAX`
3. `ISSUER_WEIGHT_MAX`
4. `SECTOR_WEIGHT_MAX`
5. `REGION_WEIGHT_MAX`
6. `CURRENCY_EXPOSURE_MAX`
7. `TRACKING_ERROR_MAX`
8. `TURNOVER_MAX`
9. `TAX_REALIZATION_MAX`
10. `CASH_BAND`
11. `MIN_TRADE_NOTIONAL`
12. `NO_SHORTING`
13. `NO_OVERDRAFT`
14. `SETTLEMENT_CASH_LADDER`
15. `SHELF_ELIGIBILITY`
16. `CLIENT_RESTRICTION`
17. `SUSTAINABILITY_EXCLUSION`
18. `LIQUIDITY_MINIMUM`
19. `CURRENCY_HEDGE_RATIO_BAND`
20. `FX_FORWARD_ELIGIBILITY`
21. `SCENARIO_LOSS_MAX`
22. `REGIME_POLICY_BAND`
23. `STRESS_CONTRIBUTION_MAX`

Constraint severities:

1. `HARD`: cannot be relaxed without `BLOCKED`,
2. `SOFT`: may produce `PENDING_REVIEW`,
3. `INFO`: evidence only.

Relaxation rules:

1. hard constraints cannot be silently relaxed,
2. every soft relaxation must include reason, magnitude, actor or policy authority, and evidence,
3. default target-state implementation should avoid relaxations unless explicitly configured.

---

## 7. Domain Models

### 7.1 DpmRebalanceAlternativeSet

Required fields:

1. `alternative_set_id`
2. `portfolio_id`
3. `mandate_id`
4. `as_of_date`
5. `input_mode`
6. `requested_methods`
7. `generated_methods`
8. `source_readiness`
9. `alternatives`
10. `comparison_summary`
11. `recommended_alternative_id`
12. `recommendation_basis`
13. `lineage`
14. `created_at`

### 7.2 DpmRebalanceAlternative

Required fields:

1. `alternative_id`
2. `alternative_type`
3. `status`
4. `construction_method`
5. `objective_trace`
6. `constraint_trace`
7. `before`
8. `target`
9. `intents`
10. `after_simulated`
11. `rule_results`
12. `diagnostics`
13. `decision_metrics`
14. `risk_impact`
15. `tax_impact`
16. `turnover_impact`
17. `cost_impact`
18. `liquidity_impact`
19. `fx_impact`
20. `explanation`
21. `lineage`

### 7.3 DpmAlternativeDecisionMetrics

Required metrics:

1. `drift_before`
2. `drift_after`
3. `drift_reduction`
4. `turnover_weight`
5. `trade_count`
6. `estimated_transaction_cost_base`
7. `estimated_realized_gain_base`
8. `cash_after_weight`
9. `risk_score_before`
10. `risk_score_after`
11. `tracking_error_before`
12. `tracking_error_after`
13. `restriction_breach_count`
14. `source_readiness_state`

---

## 8. API Surface

### 8.1 Generate Alternatives

`POST /api/v1/rebalance/alternatives`

Purpose:

1. generate a bounded alternative set for one mandate/portfolio,
2. support stateless or stateful source input,
3. persist the alternative set and lineage.

Request fields:

1. `input_mode`
2. `portfolio_id` or stateless input bundle,
3. `as_of`
4. `mandate_id`
5. `requested_methods`
6. `policy_pack_id`
7. `max_alternatives`
8. `include_risk_enrichment`
9. `include_performance_context`
10. `include_tax_impact`
11. `solver_time_budget_ms`

Response:

1. full `DpmRebalanceAlternativeSet`,
2. status per alternative,
3. source readiness and degradation details.

### 8.2 Retrieve Alternatives

`GET /api/v1/rebalance/alternatives/{alternative_set_id}`

Purpose:

1. retrieve persisted alternative set,
2. support Workbench comparison and proof-pack generation.

### 8.3 Select Alternative

`POST /api/v1/rebalance/alternatives/{alternative_set_id}/select`

Purpose:

1. mark selected alternative,
2. persist actor, rationale, and timestamp,
3. prepare for proof pack or workflow review.

Rules:

1. only one selected alternative per selection version,
2. selecting `BLOCKED` alternative requires explicit override and remains `PENDING_REVIEW` or
   `BLOCKED` according to policy,
3. selection does not execute trades.

---

## 9. Persistence

Tables:

1. `dpm_alternative_sets`
2. `dpm_rebalance_alternatives`
3. `dpm_alternative_selection_events`

Required indexes:

1. `(portfolio_id, created_at desc)`
2. `(mandate_id, created_at desc)`
3. `(alternative_set_id)`
4. `(selected_alternative_id)`
5. `(status, created_at desc)`

Retention:

1. selected alternatives: 7 years,
2. unselected alternatives: configurable, default 2 years,
3. blocked alternatives linked to audit or compliance review: 7 years.

---

## 10. Implementation Slices

### Slice 0 - Design Tightening and RFC Review

1. validate current solver capabilities,
2. map all constraints to existing engine/policy-pack fields,
3. identify source-data gaps for risk, tax, liquidity, ESG, and costs,
4. define minimum viable alternative methods.

Exit evidence:

1. field-by-field source map,
2. gap list for `lotus-core`, `lotus-risk`, `lotus-performance`,
3. agreed method list for first implementation.

### Slice 1 - Domain Models and Pure Alternative Engine

1. add alternative set models,
2. add objective and constraint traces,
3. wrap existing heuristic output as one alternative,
4. add do-nothing baseline,
5. add pure comparison metrics.

Exit evidence:

1. unit tests for model validation,
2. deterministic comparison tests,
3. no persistence required yet.

### Slice 2 - Solver and Method Registry

1. define method registry,
2. expose solver availability posture,
3. add solver trace,
4. add fallback handling,
5. add infeasibility classification.

Exit evidence:

1. solver success test,
2. solver unavailable test,
3. infeasible constraints test,
4. fallback trace test.

### Slice 3 - Tax, Turnover, Liquidity, and Cost Enrichment

1. connect tax lots,
2. calculate turnover and estimated cost,
3. calculate liquidity/cash posture,
4. classify missing inputs.

Exit evidence:

1. tax-lot present/missing tests,
2. turnover budget tests,
3. liquidity/cash buffer tests.

### Slice 4 - Risk and Performance Context

1. call or prepare seam for `lotus-risk`,
2. call or prepare seam for `lotus-performance`,
3. support degraded mode,
4. include enrichment supportability.

Exit evidence:

1. mocked upstream tests,
2. unavailable upstream tests,
3. response examples with and without enrichment.

### Slice 5 - Persistence and APIs

1. add migrations and repositories,
2. add generate/retrieve/select APIs,
3. add OpenAPI docs and examples,
4. add supportability.

Exit evidence:

1. repository parity tests,
2. API tests,
3. OpenAPI certification.

### Slice 6 - Live Proof and Closure

1. prove canonical portfolio alternatives,
2. capture full request/response evidence,
3. update README/wiki/supported-features,
4. create follow-up RFCs or issues for gaps.

Exit evidence:

1. live evidence reviewed,
2. CI green,
3. docs and wiki current.

---

## 11. Testing Strategy

Required tests:

1. deterministic alternative generation,
2. objective trace completeness,
3. constraint trace completeness,
4. solver success/failure/fallback,
5. tax-aware lot selection,
6. turnover budget enforcement,
7. liquidity-aware cash preservation,
8. risk/performance enrichment degraded behavior,
9. selection event persistence,
10. OpenAPI examples and field documentation,
11. canonical live evidence.

---

## 12. Acceptance Criteria

RFC-0039 is complete when:

1. at least four alternative methods are implemented and certified,
2. alternative sets are persisted and retrievable,
3. every alternative includes comparable decision metrics,
4. solver status and infeasibility are explainable,
5. selected alternative is actor-attributed,
6. OpenAPI is complete,
7. live proof shows a realistic discretionary mandate comparison,
8. no AI or UI layer chooses the alternative on behalf of the PM.
