# RFC-0042: Post-Trade Outcome Feedback Loop

| Metadata | Details |
| --- | --- |
| **Status** | PROPOSED |
| **Created** | 2026-05-03 |
| **Depends On** | RFC-0017, RFC-0019, RFC-0023, RFC-0036, RFC-0037, RFC-0038, RFC-0039, RFC-0040, RFC-0041 |
| **Doc Location** | `docs/rfcs/RFC-0042-post-trade-outcome-feedback-loop.md` |

---

## 0. Executive Summary

RFC-0042 closes the DPM decision loop. After a rebalance is approved and execution records arrive
from `lotus-core`, `lotus-manage` should compare expected versus realized outcomes across drift,
risk, performance, turnover, cost, tax, FX, cash, and execution quality.

This creates a feedback system for PMs, CIO teams, operations, risk oversight, and sales demos. It
proves not only what the engine proposed, but whether the decision achieved its intended outcome.

---

## 1. Problem Statement

Without outcome feedback:

1. expected drift reduction is not compared to realized drift reduction,
2. expected risk improvement is not compared to realized risk,
3. transaction cost and tax estimates are not checked,
4. execution slippage and partial fills are not measured,
5. PMs cannot learn which construction method performed best,
6. CIO teams cannot see whether model-change waves were implemented effectively,
7. audit evidence stops before the outcome.

## 1.5 Business Outcomes

This RFC targets the following business outcomes:

1. **Close the discretionary management loop**
   prove whether approved actions achieved their intended drift, risk, liquidity, tax, and cost
   outcomes.
2. **Improve PM accountability**
   give PMs and leaders evidence on expected versus realized impact without relying on manual
   post-trade analysis.
3. **Improve model and construction quality**
   reveal which construction methods produce better realized outcomes under different mandate
   conditions.
4. **Strengthen governance and audit**
   connect pre-trade proof, execution evidence, risk/performance outcomes, and post-trade review in
   one traceable chain.
5. **Reduce future errors**
   identify recurring slippage, partial-fill, tax, cash, source-data, or risk variance patterns.
6. **Create high-value reporting content**
   provide outcome review material for client reports, PM reviews, CIO reviews, and sales demos.

---

## 2. Goals and Non-Goals

### 2.1 Goals

1. Add post-trade outcome review model and APIs.
2. Compare expected versus realized outcomes.
3. Integrate with `lotus-core` execution/transaction records.
4. Integrate with `lotus-risk` for post-trade risk.
5. Integrate with `lotus-performance` for post-trade returns and attribution.
6. Link outcome review to proof packs, alternatives, waves, and runs.
7. Persist outcome evidence and supportability.
8. Produce PM quality and method quality metrics.

### 2.2 Non-Goals

1. Book transactions.
2. Calculate authoritative performance or risk locally.
3. Replace operations break management.
4. Trigger client communications directly.
5. Use AI to judge PM quality.

---

## 3. Outcome Dimensions

Required dimensions:

1. `DRIFT_OUTCOME`
2. `RISK_OUTCOME`
3. `PERFORMANCE_OUTCOME`
4. `TURNOVER_OUTCOME`
5. `TRANSACTION_COST_OUTCOME`
6. `TAX_OUTCOME`
7. `FX_OUTCOME`
8. `CASH_OUTCOME`
9. `EXECUTION_QUALITY`
10. `RULE_OUTCOME`
11. `SOURCE_DATA_OUTCOME`

Each dimension includes:

1. expected value,
2. realized value,
3. variance,
4. tolerance,
5. state,
6. reason code,
7. source refs.

---

## 4. Outcome Classification

Outcome states:

1. `READY`: outcome is within expected tolerance or positive,
2. `PENDING_REVIEW`: variance exceeds soft tolerance or requires PM explanation,
3. `BLOCKED`: source evidence is incomplete or outcome breach requires formal review.

Reason codes:

1. `DRIFT_REDUCTION_ACHIEVED`
2. `DRIFT_REDUCTION_SHORTFALL`
3. `RISK_REDUCTION_ACHIEVED`
4. `RISK_INCREASED`
5. `COST_ABOVE_ESTIMATE`
6. `TAX_ABOVE_BUDGET`
7. `SLIPPAGE_ABOVE_TOLERANCE`
8. `PARTIAL_FILL_IMPACT`
9. `FX_RESIDUAL_VARIANCE`
10. `CASH_RESIDUAL_OUT_OF_BAND`
11. `PERFORMANCE_BELOW_EXPECTATION`
12. `SOURCE_EVIDENCE_INCOMPLETE`

---

## 5. Domain Models

### 5.1 DpmPostTradeOutcomeReview

Required fields:

1. `outcome_review_id`
2. `portfolio_id`
3. `mandate_id`
4. `rebalance_run_id`
5. `alternative_set_id`
6. `selected_alternative_id`
7. `wave_id`
8. `proof_pack_id`
9. `review_window_start`
10. `review_window_end`
11. `overall_state`
12. `dimension_results`
13. `expected_snapshot`
14. `realized_snapshot`
15. `variance_summary`
16. `source_lineage`
17. `created_at`

### 5.2 DpmOutcomeDimensionResult

Required fields:

1. `dimension`
2. `state`
3. `reason_code`
4. `expected`
5. `realized`
6. `variance`
7. `tolerance`
8. `explanation`
9. `source_refs`

### 5.3 DpmExecutionQualitySummary

Required fields:

1. `expected_trade_count`
2. `executed_trade_count`
3. `cancelled_trade_count`
4. `partial_fill_count`
5. `estimated_cost_base`
6. `realized_cost_base`
7. `estimated_tax_base`
8. `realized_tax_base`
9. `slippage_base`
10. `residual_cash_base`

---

## 6. API Surface

### 6.1 Create Outcome Review

`POST /api/v1/rebalance/outcome-reviews`

Purpose:

1. create outcome review for a run, alternative, or wave item,
2. source realized evidence,
3. persist review.

Request fields:

1. `rebalance_run_id`
2. `alternative_set_id`
3. `selected_alternative_id`
4. `wave_id`
5. `wave_item_id`
6. `review_window_start`
7. `review_window_end`
8. `include_risk`
9. `include_performance`
10. `actor`

### 6.2 Retrieve Outcome Review

`GET /api/v1/rebalance/outcome-reviews/{outcome_review_id}`

### 6.3 Find Outcome Review By Run

`GET /api/v1/rebalance/runs/{rebalance_run_id}/outcome-review`

### 6.4 Search Outcome Reviews

`GET /api/v1/rebalance/outcome-reviews`

Filters:

1. `portfolio_id`
2. `mandate_id`
3. `wave_id`
4. `overall_state`
5. `reason_code`
6. `from`
7. `to`

---

## 7. Source Integrations

`lotus-core`:

1. transaction/fill window,
2. post-trade holdings,
3. cash movements,
4. FX executions,
5. tax-lot realization data.

`lotus-risk`:

1. risk after execution,
2. risk before/after comparison,
3. concentration and stress posture.

`lotus-performance`:

1. return since rebalance,
2. contribution and attribution,
3. benchmark-relative impact.

If any source is unavailable, the outcome review must degrade explicitly.

---

## 8. Persistence

Tables:

1. `dpm_outcome_reviews`
2. `dpm_outcome_dimension_results`
3. `dpm_outcome_source_refs`

Indexes:

1. `(rebalance_run_id)`
2. `(portfolio_id, created_at desc)`
3. `(mandate_id, created_at desc)`
4. `(wave_id, created_at desc)`
5. `(overall_state, created_at desc)`

Retention:

1. 7 years for selected/approved rebalance outcomes,
2. 3 years for diagnostic-only reviews not tied to execution,
3. legal/audit hold support must be compatible with future archive policy.

---

## 9. Implementation Slices

### Slice 0 - Source Evidence Mapping

1. map expected fields from proof pack and alternatives,
2. map realized fields from core/risk/performance,
3. identify gaps,
4. define first-wave review window semantics.

### Slice 1 - Pure Outcome Comparison

1. add domain models,
2. compare expected vs realized from provided fixtures,
3. implement variance and tolerance logic,
4. add reason codes.

### Slice 2 - Persistence and APIs

1. add migrations,
2. add repositories,
3. add create/retrieve/search APIs,
4. add OpenAPI docs.

### Slice 3 - Core/Risk/Performance Integration

1. add source clients or seams,
2. add degraded-source handling,
3. add supportability and lineage.

### Slice 4 - Live Proof and Reporting Handoff

1. generate outcome review from canonical executed example,
2. link proof pack and report evidence,
3. update docs/wiki.

---

## 10. Testing Requirements

1. pure variance calculations,
2. tolerance thresholds,
3. source-unavailable degradation,
4. partial fills,
5. slippage,
6. tax variance,
7. risk/performance enrichment,
8. repository persistence,
9. API and OpenAPI,
10. live canonical evidence.

---

## 11. Acceptance Criteria

RFC-0042 is complete when:

1. outcome review can be generated from a selected rebalance,
2. expected versus realized metrics are decomposed,
3. degraded source behavior is explicit,
4. reviews are persisted and searchable,
5. APIs are certified,
6. live proof shows at least one post-trade feedback story,
7. outcome feedback can feed future PM dashboards without recomputing domain truth in UI.

---

## 12. Gold-Standard Execution Contract

RFC-0042 closes the investment feedback loop. It must compare what `lotus-manage` expected before
trade with what actually happened after execution, using source-authoritative evidence rather than
PM anecdotes or UI-side recomputation.

### 12.1 Supported-Features Ledger

| Feature | Support state before implementation | Promotion rule |
| --- | --- | --- |
| Outcome review creation | Proposed | Promote only after expected and realized data are reconciled with source refs. |
| Variance decomposition | Proposed | Promote only after drift, cost, tax, FX, risk, performance, and execution-quality dimensions are tested. |
| Source-degraded outcome review | Proposed | Promote only after missing core/risk/performance data is explicit and non-misleading. |
| Searchable outcome memory | Proposed | Promote only after reviews are persisted, searchable, and linked to runs, waves, and proof packs. |
| Feedback to future construction | Proposed | Promote only after feedback outputs are safe for future PM dashboards and construction quality review. |

### 12.2 Architecture and Domain Direction

Implementation must preserve source authority:

1. `lotus-core` owns fills, transactions, cash movements, FX executions, holdings, and tax
   realizations,
2. `lotus-risk` owns post-trade risk and stress posture,
3. `lotus-performance` owns post-trade returns, attribution, contribution, and benchmark context,
4. `lotus-manage` owns expected-versus-realized decision review and PM workflow memory,
5. no UI or AI layer may recompute outcome truth from partial evidence.

### 12.3 Mandatory Delivery Slices

These slices are mandatory in addition to the feature-specific slices in Section 9.

#### Mandatory Slice A - Platform Automation and Scaffolding Improvement

Review whether platform scaffolding should provide reusable outcome-review evidence patterns,
source-degraded examples, post-trade telemetry fields, and OpenAPI examples for reconciliation
surfaces. Improve platform automation for repeatable gaps; otherwise record a no-change decision.

#### Mandatory Slice B - Cleanup and Structure

Separate pure variance calculations from source clients, persistence, and API presentation. Remove
any generic "review result" naming that should be outcome, variance, execution-quality, or
expected-versus-realized terminology.

#### Mandatory Slice C - Implementation Proof

Capture evidence for at least one post-trade review linked to a proof pack and selected alternative.
Review every expected value, realized value, tolerance, variance, classification, and degraded-source
reason.

#### Mandatory Slice D - Second-Last Hardening and Review

Review numerical determinism, source staleness, tolerance policy, OpenAPI field examples, bounded
metrics/logs, retention posture, error handling, and test-pyramid adequacy.

#### Mandatory Slice E - Final Closure

Update wiki with outcome-feedback behavior and business value, update supported-features only after
live proof, update context/skills decisions, and leave branch/PR/CI clean.

### 12.4 Evidence Expectations

Closure evidence must include:

1. outcome review creation request/response,
2. source lineage for expected and realized values,
3. variance/tolerance worked example,
4. source-unavailable degraded example,
5. search/filter example,
6. OpenAPI/API certification summary,
7. local and GitHub check summary.

### 12.5 Enterprise Baseline

This RFC inherits RFC-0037 Section 19.4. Completion requires expected-versus-realized lineage,
source-readiness metadata, outcome audit events, bounded variance metrics, structured logs,
operator diagnostics, API certification, and GitHub lane evidence for every outcome-review endpoint.
