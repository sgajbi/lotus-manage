# RFC-0005: Institutional Tightening (Post-trade Rules, Reconciliation, Demo Pack)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-14 |
| **Target Release** | Completed |
| **Doc Location** | docs/rfcs/RFC-0005-institutional-tightening-post-trade-rules-reconciliation-demo-pack.md |

---

## 0. Executive Summary

RFC-0005 upgrades the rebalance engine from a functional calculator to an **institution-grade simulator**. It strictly enforces domain correctness, auditability, and safety without introducing database persistence.

**Key Deliverables:**
1.  **Complete State Model:** Every run returns a fully reconciled `before` and `after` state (Allocations, Cash, Positions).
2.  **Post-Trade Rule Engine:** A dedicated module verifying `SINGLE_POSITION_MAX` (Hard), `CASH_BAND` (Soft), and `MIN_TRADE_SIZE` (Info) on the *simulated* after-state.
3.  **Reconciliation Invariants:** Mathematical proof that `Before Value ≈ After Value` (within tolerance), ensuring no "vanishing money."
4.  **Holdings-Aware Safety:** Strict blocking of negative holdings (shorting) and correct handling of `SELL_ONLY`/`SUSPENDED` assets.

### 0.1 Implementation Alignment (As of 2026-02-17)

1. Rule engine and reconciliation are implemented.
2. Core orchestration remains in `src/core/dpm/engine.py`; `src/core/compliance.py` and `src/core/valuation.py` are modularized, while `simulation.py` is not a separate module.
3. `MIN_TRADE_SIZE` is emitted as `severity=SOFT` with `status=PASS` and reason `INTENTS_SUPPRESSED` when applicable.

---

## 1. Problem Statement

The current implementation lacks "institution-grade" rigor:
* **Inconsistent State:** `after_simulated` richness varies; allocations are often empty.
* **Ad-hoc Rules:** Compliance checks are scattered and not consistently emitted.
* **Trust Gap:** No explicit reconciliation prevents verifying if FX/rounding caused value leakage.
* **Safety Gap:** Simulation logic could theoretically allow selling more than held (negative inventory).

---

## 2. Goals

### 2.1 Functional Requirements
* **State Completeness:** `before` and `after` objects must populate `positions`, `cash_balances`, `allocation_by_asset_class`, and `allocation_by_instrument`.
* **Rule Engine v2:**
    * **Always** emit results for `SINGLE_POSITION_MAX`, `CASH_BAND`, `MIN_TRADE_SIZE`.
    * Evaluate rules against the *Simulated After-State*.
* **Reconciliation:**
    * Enforce `Abs(After_Total_Value - Before_Total_Value) <= Tolerance`.
    * If mismatched, return `BLOCKED` with `RECONCILIATION_MISMATCH`.
* **Holdings Safety:**
    * Block run if `after_simulated.positions[].quantity < 0`.
    * Enforce `SELL_ONLY` (Block Buys) and `SUSPENDED` (Freeze) logic.

### 2.2 Quality & Standards
* **Modular Architecture:** Refactor `engine.py` into distinct domains (`Valuation`, `Compliance`, `Simulation`) for maintainability.
* **Demo Pack:** Create `docs/demo/` with curated scenarios (Drift, Cash Inflow, Sell-to-Fund, Multi-Currency).

---

## 3. Post-Trade Rule Engine Specification

The Rule Engine must run *after* the simulation step.

| Rule ID | Severity | Logic | Outcome |
| :--- | :--- | :--- | :--- |
| **SINGLE_POSITION_MAX** | **HARD** | `Position_Weight > Limit` | `BLOCKED` |
| **CASH_BAND** | **SOFT** | `Cash_Weight` outside `[Min, Max]` | `PENDING_REVIEW` |
| **MIN_TRADE_SIZE** | **INFO** | `Notional < Min` | `PASS` (Log to Diagnostics) |
| **NO_SHORTING** | **HARD** | `Quantity < 0` | `BLOCKED` |
| **RECONCILIATION** | **HARD** | `Value_Delta > Tolerance` | `BLOCKED` |

---

## 4. Implementation Plan

1.  **Modularization:** Keep `src/core/dpm/engine.py` as orchestrator and use:
    * `valuation.py`: State construction & normalization.
    * `compliance.py`: The Rule Engine.
    * Intent application & FX simulation inside `engine.py`.
2.  **Safety Logic:** Implement negative quantity checks and total value reconciliation.
3.  **Golden Suite:** Update golden scenarios to reflect the new strict rule outputs.

---

## 5. Behavior Reference (Implemented)

### 5.1 Rule Severity to Final Status

1. If any `HARD` rule fails, final status is `BLOCKED`.
2. If no `HARD` rule fails but at least one `SOFT` rule fails, final status is `PENDING_REVIEW`.
3. If all hard and soft rules pass, final status is `READY`.
4. `INFO` rules never downgrade status and are emitted for transparency.

### 5.2 Reconciliation Behavior

1. Engine computes before and after total portfolio value in base currency.
2. A tolerance is applied for rounding and FX precision.
3. If absolute delta exceeds tolerance:
   1. Reason `RECONCILIATION_MISMATCH` is emitted.
   2. Final status is forced to `BLOCKED`.
4. Reconciliation is applied after intents are simulated and rules are evaluated.

### 5.3 Holdings Safety Behavior

1. Any sell instruction that would push quantity below zero is blocked by safety checks.
2. Buy attempts on unsupported shelf statuses (for example `SELL_ONLY` and `SUSPENDED`) are blocked.
3. Safety breaches are treated as hard-fail outcomes and therefore return `BLOCKED`.
