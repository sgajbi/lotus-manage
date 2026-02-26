# RFC-0006A: Pre-Persistence Hardening - Safety, After-State Completeness, Contract Consistency

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-15 |
| **Target Release** | Completed |
| **Doc Location** | docs/rfcs/RFC-0006A-pre-persistence-safety-afterstate.md |

---

## 0. Executive Summary

RFC-0006A closes the highest-risk correctness and demo credibility gaps (excluding persistence):

1.  **Institutional Safety:** Enforce *no-short / no-oversell* logic and make cash insufficiency deterministic.
2.  **Institution-Grade After-State:** `after_simulated` must always include detailed `positions`, `allocations`, and a proof of `reconciliation`.
3.  **Contract Consistency:** Enforce a single canonical endpoint (`/rebalance/simulate`) and strict `Idempotency-Key` behavior across all layers (Docs, Tests, API).

This RFC intentionally does **NOT** expand the scenario matrix or ruleset breadth; it focuses strictly on the correctness of the simulation engine itself.

### 0.1 Implementation Alignment (As of 2026-02-17)

1. Canonical route remains `POST /rebalance/simulate`.
2. `Idempotency-Key` is required at API boundary; durable idempotency persistence is deferred.
3. Reconciliation output is implemented and enforced (`MISMATCH` blocks run).
4. Safety outcomes are surfaced via rule results (`NO_SHORTING`, `INSUFFICIENT_CASH`) and `status=BLOCKED`.

---

## 1. Problem Statement

Current gaps prevent the engine from being "Demo Ready" for institutional stakeholders:

* **Safety Gap:** The simulator can silently create negative holdings if `sell_quantity > held_quantity`.
* **Audit Gap:** `after_simulated` is often "thin" (cash-only), missing the rich position data present in the `before` state.
* **Consistency Gap:** Documentation references `/v1/rebalance`, while tests use `/rebalance/simulate`. `Idempotency-Key` enforcement is loose.

---

## 2. Goals

### 2.1 Must-Have Functional Goals

1.  **Prevent Negative Holdings (Hard Block):**
    * Any intent that reduces a position below zero must result in `status: BLOCKED`.
    * Diagnostics must explicitly cite `SELL_EXCEEDS_HOLDINGS`.

2.  **Complete After-State:**
    * `after_simulated` must mirror `before` structure exactly:
        * `positions[]` (with recalculated weights/values).
        * `allocation_by_asset_class[]`.
        * `allocation_by_instrument[]`.
        * `reconciliation` block (Before Total vs After Total).

3.  **Valuation Correctness:**
    * Negative quantities (if ever allowed via config) must never be filtered out of valuation.

4.  **Contract Alignment:**
    * Canonical Endpoint: `POST /rebalance/simulate`.
    * Header: `Idempotency-Key` is **REQUIRED**.

### 2.2 Non-Goals
* Persistence (PostgreSQL/AsyncPG).
* New business rules (beyond Safety Guards).
* Tax optimization.

---

## 3. Contract Decisions

### 3.1 Canonical Endpoint
We enforce **`POST /rebalance/simulate`** as the single source of truth.
* Update `docs/demo/*.json` and `README.md`.
* Update all `tests/` to use this path.

### 3.2 Reconciliation Block
Every response must include a mathematical proof of value preservation.

```json
"reconciliation": {
  "before_total_value": { "amount": "10000.00", "currency": "SGD" },
  "after_total_value": { "amount": "9999.50", "currency": "SGD" },
  "delta": { "amount": "-0.50", "currency": "SGD" },
  "tolerance": { "amount": "1.00", "currency": "SGD" },
  "status": "OK" // or "MISMATCH"
}

```

---

## 4. Implementation Specification

### 4.1 Safety Guards (The "No-Throw" Domain Logic)

**1. No-Short / No-Oversell:**
During the simulation phase (applying intents to portfolio):

* Calculate `NewQty = CurrentQty - SellQty`.
* If `NewQty < 0`:
* **Action:** Stop Simulation.
* **Result:** `status = BLOCKED`.
* **Rule:** `NO_SHORTING` = FAIL.
* **Diagnostic:** `SELL_EXCEEDS_HOLDINGS` (Instrument ID, Held, Sold).



**2. Cash Insufficiency:**

* After netting sells and buys:
* If `ProjectedCash < 0` (and no FX can cover it):
* **Action:** Stop Simulation.
* **Result:** `status = BLOCKED`.
* **Rule:** `INSUFFICIENT_CASH` = FAIL.



### 4.2 Valuation & State Builder

Refactor `src/core/valuation.py` to be a pure function that generates the **Complete State Object** (`SimulatedState`) from a raw `PortfolioSnapshot` + `MarketData`.

* **Input:** `PortfolioSnapshot`, `MarketData`, `Shelf`.
* **Output:** `SimulatedState` (Total Value, Allocations, Positions Enriched).
* **Logic:**
* Iterate *all* positions (even zero or negative).
* Compute `ValueBase = Qty * Price * FX`.
* Sum buckets for Allocations.



---

## 5. Implementation Plan

### Phase 1: API & Contract Alignment

1. Update `main.py` to enforce `Idempotency-Key`.
2. Refactor tests to use canonical endpoint.

### Phase 2: Valuation Refactor

1. Extract `build_simulated_state(...)` from `valuation.py`.
2. Ensure it populates `positions`, `allocations`, and `total_value` robustly.

### Phase 3: Simulation & Safety Guards

1. Update `engine.py` -> `_apply_intents`.
2. Implement "transactional" application: calculate new state, check guards, then commit or return Blocked.
3. Add `reconciliation` calculation.

### Phase 4: Golden Update

1. Regenerate goldens (outputs will now be richer).
2. Verify `scenario_05` and `scenario_04` (blocked states) still return valid JSON.

---

## 6. Acceptance Criteria

1. **Oversell Block:** Submitting a request to sell 100 units of an asset where only 50 are held returns `BLOCKED` with `NO_SHORTING` rule failure.
2. **Rich Response:** A successful run returns a full list of positions in `after_simulated` with correct weights.
3. **Reconciliation:** Response contains the `reconciliation` object and `status: OK`.
4. **Strict Headers:** Request without `Idempotency-Key` returns HTTP 422.
