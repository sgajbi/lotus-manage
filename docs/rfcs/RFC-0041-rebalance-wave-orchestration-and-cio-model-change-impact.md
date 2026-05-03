# RFC-0041: Rebalance Wave Orchestration and CIO Model Change Impact

| Metadata | Details |
| --- | --- |
| **Status** | PROPOSED |
| **Created** | 2026-05-03 |
| **Depends On** | RFC-0018, RFC-0020, RFC-0023, RFC-0036, RFC-0037, RFC-0038, RFC-0039, RFC-0040 |
| **Doc Location** | `docs/rfcs/RFC-0041-rebalance-wave-orchestration-and-cio-model-change-impact.md` |

---

## 0. Executive Summary

RFC-0041 adds multi-portfolio DPM orchestration. It lets a CIO/model change, tactical house view, or
PM book action create a rebalance wave, determine affected mandates, check source readiness,
simulate alternatives, route exceptions, stage selected actions, and prepare execution handoff
evidence.

This is how `lotus-manage` scales from one-portfolio analysis to real discretionary portfolio
management across a PM book.

---

## 1. Problem Statement

Single-portfolio simulation is necessary but insufficient. A private-bank DPM desk needs to answer:

1. Which portfolios are affected by a model or house-view change?
2. Which portfolios are ready to rebalance?
3. Which are blocked by data, policy, tax, liquidity, or workflow?
4. How much aggregate notional will be traded?
5. Which currencies require funding?
6. Which securities create liquidity or concentration issues?
7. Which PM/CIO/compliance approvals are required?
8. What can operations safely stage?

Without a wave aggregate, PMs and operations must stitch together many independent runs manually.

## 1.5 Business Outcomes

This RFC targets the following business outcomes:

1. **Scale DPM operations**
   move from individual portfolio actions to coordinated PM-book and CIO-driven rebalance waves.
2. **Improve CIO implementation control**
   show how model changes and house views affect mandates before trading begins.
3. **Reduce operational bottlenecks**
   separate ready, blocked, review-required, staged, and handoff-ready portfolios in one governed
   workflow.
4. **Improve risk and liquidity planning**
   aggregate expected trade notional, FX needs, liquidity warnings, and blocked cohorts before
   execution handoff.
5. **Increase governance quality**
   preserve actor-attributed approval, staging, cancellation, and retry decisions at both wave and
   item level.
6. **Create a premium management dashboard story**
   enable Workbench to show CIO/PM wave progress with real backend state, not UI-only summaries.

---

## 2. Goals and Non-Goals

### 2.1 Goals

1. Add `DpmRebalanceWave` aggregate.
2. Add CIO model-change impact analysis.
3. Identify affected mandates from model, risk profile, region, currency, PM book, or explicit list.
4. Run source-readiness checks across the wave.
5. Generate alternatives per wave item.
6. Allow item-level review and selection.
7. Stage approved items for handoff.
8. Persist wave, wave items, state transitions, and supportability.
9. Expose wave APIs and command-center integration.

### 2.2 Non-Goals

1. Actual OMS/EMS execution.
2. Client consent workflows.
3. Replacing report batch scheduler.
4. Replacing core transaction booking.
5. Solving all portfolios as one global optimization problem. First-wave scope is coordinated
   orchestration with item-level construction.

---

## 3. Wave Triggers

Supported trigger types:

1. `CIO_MODEL_CHANGE`
2. `TACTICAL_HOUSE_VIEW`
3. `PM_BOOK_REVIEW`
4. `RISK_BREACH_REMEDIATION`
5. `CASH_DRAG_CAMPAIGN`
6. `TAX_YEAR_END_REVIEW`
7. `ESG_RESTRICTION_UPDATE`
8. `MANUAL_PORTFOLIO_LIST`

Each trigger must record:

1. trigger id,
2. trigger type,
3. source system,
4. source event id,
5. effective date,
6. created by,
7. rationale,
8. affected model ids,
9. affected mandate filters,
10. lineage.

---

## 4. Wave State Machine

Wave states:

1. `DRAFT`
2. `SOURCE_CHECK`
3. `SIMULATING`
4. `REVIEWING`
5. `APPROVED`
6. `STAGED`
7. `HANDOFF_READY`
8. `HANDOFF_SENT`
9. `PARTIALLY_COMPLETED`
10. `COMPLETED`
11. `CANCELLED`
12. `FAILED`

Wave item states:

1. `PENDING_SOURCE_CHECK`
2. `SOURCE_BLOCKED`
3. `READY_TO_SIMULATE`
4. `SIMULATION_BLOCKED`
5. `ALTERNATIVES_READY`
6. `REVIEW_REQUIRED`
7. `SELECTED`
8. `APPROVED`
9. `STAGED`
10. `HANDOFF_READY`
11. `HANDOFF_SENT`
12. `COMPLETED`
13. `CANCELLED`
14. `FAILED`

State rules:

1. a wave can be `PARTIALLY_COMPLETED` if at least one item completed and at least one item is
   blocked, failed, or cancelled,
2. item-level `BLOCKED` simulation outcomes do not fail the whole wave,
3. wave transitions are actor-attributed,
4. every state transition is append-only.

---

## 5. Domain Models

### 5.1 DpmRebalanceWave

Required fields:

1. `wave_id`
2. `wave_name`
3. `trigger`
4. `state`
5. `as_of_date`
6. `portfolio_manager_id`
7. `tenant_id`
8. `selection_criteria`
9. `items`
10. `aggregate_metrics`
11. `source_readiness_summary`
12. `approval_summary`
13. `handoff_summary`
14. `lineage`
15. `created_at`
16. `updated_at`

### 5.2 DpmRebalanceWaveItem

Required fields:

1. `wave_item_id`
2. `wave_id`
3. `portfolio_id`
4. `mandate_id`
5. `state`
6. `source_readiness_state`
7. `alternative_set_id`
8. `selected_alternative_id`
9. `proof_pack_id`
10. `rebalance_run_id`
11. `blocking_reasons`
12. `approval_state`
13. `handoff_state`
14. `lineage`

### 5.3 DpmCioModelChangeImpact

Required fields:

1. `impact_id`
2. `model_change_event_id`
3. `affected_model_ids`
4. `affected_portfolio_count`
5. `affected_mandate_count`
6. `estimated_trade_count`
7. `estimated_turnover_base`
8. `estimated_fx_by_currency`
9. `source_blocked_count`
10. `policy_blocked_count`
11. `approval_required_count`
12. `top_exposures`
13. `lineage`

---

## 6. API Surface

### 6.1 Create Wave

`POST /api/v1/rebalance/waves`

Purpose:

1. create wave from trigger and selection criteria,
2. persist draft wave and candidate items.

### 6.2 Preview Affected Portfolios

`POST /api/v1/rebalance/waves/preview`

Purpose:

1. estimate affected portfolios without creating durable wave,
2. support CIO and PM planning.

### 6.3 Source Check

`POST /api/v1/rebalance/waves/{wave_id}/source-check`

Purpose:

1. call core readiness for each item,
2. classify item readiness,
3. update wave source summary.

### 6.4 Simulate Wave

`POST /api/v1/rebalance/waves/{wave_id}/simulate`

Purpose:

1. generate alternatives for ready items,
2. preserve blocked item reasons,
3. update aggregate metrics.

### 6.5 Approve Wave or Items

`POST /api/v1/rebalance/waves/{wave_id}/approve`

Purpose:

1. approve all eligible items or selected item ids,
2. preserve actor/rationale,
3. fail safely for blocked items.

### 6.6 Stage and Handoff

1. `POST /api/v1/rebalance/waves/{wave_id}/stage`
2. `POST /api/v1/rebalance/waves/{wave_id}/handoff`

Purpose:

1. prepare operations handoff package,
2. mark handoff state,
3. do not execute externally.

### 6.7 Search and Inspect

1. `GET /api/v1/rebalance/waves`
2. `GET /api/v1/rebalance/waves/{wave_id}`
3. `GET /api/v1/rebalance/waves/{wave_id}/items`
4. `GET /api/v1/rebalance/waves/{wave_id}/proof-pack`

---

## 7. Persistence

Tables:

1. `dpm_rebalance_waves`
2. `dpm_rebalance_wave_items`
3. `dpm_rebalance_wave_events`
4. `dpm_cio_model_change_impacts`

Indexes:

1. `(state, updated_at desc)`
2. `(portfolio_manager_id, created_at desc)`
3. `(trigger_type, created_at desc)`
4. `(wave_id, state)`
5. `(portfolio_id, created_at desc)`

Retention:

1. completed waves: 7 years,
2. cancelled drafts with no approvals: 1 year,
3. failed waves with operational incident refs: 7 years.

---

## 8. Aggregate Metrics

Wave aggregate metrics:

1. portfolio count,
2. mandate count,
3. ready count,
4. blocked count,
5. review required count,
6. approved count,
7. staged count,
8. estimated trade count,
9. estimated turnover,
10. estimated cost,
11. estimated realized tax,
12. FX buy/sell by currency,
13. top instruments by notional,
14. liquidity warnings,
15. risk warnings.

All aggregate metrics must be derived from item evidence and reproducible.

---

## 9. Implementation Slices

### Slice 0 - Model-Change and Wave Design

1. define wave trigger inputs,
2. map model-change source gaps,
3. define first-wave selection filters,
4. define item state machine.

### Slice 1 - Wave Domain and Repository

1. add wave models,
2. add event model,
3. add repository and migrations,
4. add state transition guards.

### Slice 2 - Affected Portfolio Preview

1. identify candidate mandates from existing source products,
2. generate preview response,
3. support empty and partial-source states.

### Slice 3 - Source Check and Simulation

1. source-check all items,
2. call RFC-0039 alternatives for ready items,
3. persist item outcomes.

### Slice 4 - Approval, Staging, and Handoff

1. approve item or wave,
2. stage selected alternatives,
3. generate handoff package,
4. preserve no-external-execution boundary.

### Slice 5 - Supportability, Proof, and Docs

1. wave proof pack,
2. supportability APIs,
3. live evidence,
4. docs/wiki/supported-features.

---

## 10. Testing Requirements

1. state machine tests,
2. affected portfolio selection tests,
3. source-check partial readiness tests,
4. item simulation tests,
5. aggregate metrics tests,
6. approval/staging/handoff tests,
7. repository parity tests,
8. OpenAPI certification,
9. live canonical model-change wave proof.

---

## 11. Acceptance Criteria

RFC-0041 is complete when:

1. a wave can be created from a CIO/model trigger or explicit portfolio list,
2. source readiness is evaluated per item,
3. alternatives are generated per ready item,
4. blocked items retain reasons without failing the whole wave,
5. wave approval/staging/handoff states are persisted and actor-attributed,
6. aggregate metrics are reproducible,
7. APIs are certified,
8. canonical live evidence shows a multi-portfolio wave.
