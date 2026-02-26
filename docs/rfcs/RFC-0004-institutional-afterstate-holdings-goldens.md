# RFC-0004: Institutional After-State + Holdings-aware Golden Scenarios (Demo-tight, Pre-Persistence)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-14 |
| **Target Release** | Completed |
| **Doc Location** | docs/rfcs/RFC-0004-institutional-afterstate-holdings-goldens.md |

---

## 0. Executive Summary

Before adding persistence, we will make the simulation **institution-grade** and demo-ready by:

1.  Implementing a **complete before/after state** (allocations, holdings, cash by currency, exposures) that is consistent, explainable, and verifiable.
2.  Ensuring all valuation logic works for **real portfolios with holdings** (positions, sells, buys, multi-currency).
3.  Expanding the **golden scenario suite** to cover realistic discretionary mandate cases, including `SELL_ONLY` and `RESTRICTED` shelf behavior, missing market data, and rounding/dust suppression.
4.  Updating **sample examples** (sample snapshots + sample responses) so demos are credible and cover multiple institutional edge cases.

This RFC is strictly **pre-persistence** (runs may still be in-memory).

### 0.1 Implementation Alignment (As of 2026-02-17)

1. Holdings-aware `before`/`after_simulated` state is implemented in `src/core/valuation.py`.
2. Golden suite is implemented with filenames `scenario_101...scenario_114` under `tests/unit/dpm/golden_data/`.
3. Rule and diagnostics outputs are present and exercised by golden tests.

---

## 1. Problem Statement

The current implementation is close to RFC-0003 but is not "institution-grade" because:

* Many existing scenarios are effectively **cash-only** portfolios (positions empty), reducing confidence for real holdings.
* Sample response `before/after_simulated.allocation` is empty/simplistic, making outputs hard to demo and audit.
* Universe coverage, diagnostics, and rule results need stronger realism when holdings exist.
* A demo needs curated examples that cover *real* DPM behaviors (drift rebalance, sell-to-fund, FX funding, shelf restrictions, missing data, etc.).

---

## 2. Goals

### 2.1 Functional Goals (Must)
* Produce **complete before and after state** for every simulation:
    * total value (base)
    * allocations by asset class and by instrument
    * cash balances by currency
    * holdings list (instrument, quantity, value in base/instrument)
* Ensure **valuation correctness** from:
    * snapshot-provided `market_value` (base) OR
    * computed value from `quantity * price * FX`
* Ensure simulation supports:
    * portfolios with holdings across multiple currencies
    * sell-to-fund behavior (SELL intents and resulting cash impact)
    * FX intent generation and dependency mapping
    * rounding, min trade, dust suppression, and diagnostics
* Expand and lock in **holdings-aware golden scenarios** and demo bundles.

### 2.2 Demo Goals (Must)
* Provide a curated "demo pack":
    * `docs/demo/` containing 6–10 runnable scenarios with JSON requests + expected response highlights.
* Each scenario must be understandable to a non-engineer (PM/BA/Stakeholder) and show clear before/after allocation change.

---

## 3. Non-Goals
* PostgreSQL persistence and durable idempotency store (will be in RFC-0004B).
* OMS execution and approval workflow.
* Advanced optimization solver.

---

## 4. Institutional After-State Specification

### 4.1 Required Output Enhancements

The `POST /rebalance/simulate` response MUST populate:

#### 4.1.1 `before` object
* `total_value` (base)
* `cash_balances[]` by currency
* `positions[]` summary (holdings)
* `allocation_by_asset_class[]`
* `allocation_by_instrument[]`

#### 4.1.2 `after_simulated` object
After applying intents assuming:
* execution at `MarketDataSnapshot` price/FX
* immediate cash impact (no settlement lag in this RFC)

### 4.2 Data Structures

#### PositionSummary (required in before/after)
```json
{
  "instrument_id": "ins_us_eq_etf",
  "quantity": 1000.0,
  "instrument_currency": "USD",
  "price": { "amount": 500.0, "currency": "USD", "price_type": "MID" },
  "value_in_instrument_ccy": { "amount": 500000.0, "currency": "USD" },
  "value_in_base_ccy": { "amount": 675000.0, "currency": "SGD" },
  "weight": 0.5625
}

```

#### AllocationByAssetClass (required)

```json
{ "bucket": "EQUITY", "value": { "amount": 720000.0, "currency": "SGD" }, "weight": 0.60 }

```

#### AllocationByInstrument (required)

```json
{
  "instrument_id": "ins_us_eq_etf",
  "asset_class": "EQUITY",
  "value": { "amount": 675000.0, "currency": "SGD" },
  "weight": 0.5625
}

```

### 4.3 Valuation Rules (Institution-grade)

All valuation and weights MUST be computed in base currency.
For each position:

1. If snapshot provides `market_value` in base currency: use as truth.
2. Else compute:
* `value_instr = quantity * price(instr_ccy)`
* `value_base = value_instr * fx(instr_ccy/base_ccy)`


3. If both `market_value_base` and computed value exist:
* if delta > tolerance (e.g., 0.5%), add warning in diagnostics: `POSITION_VALUE_MISMATCH`



**Total portfolio value:**

* `total_value = sum(position_base_values) + sum(cash_base_values)`

**Weights:**

* `weight = value_base / total_value`

---

## 5. Trade Application Rules (After-State Simulator)

### 5.1 Security Trade

**BUY:**

* position quantity increases by `quantity`
* cash decreases by notional (base) OR by instrument currency cash if using multi-cash ledger

**SELL:**

* position quantity decreases by `quantity`
* if quantity would become negative (no shorting):
* BLOCKED with diagnostics `SELL_EXCEEDS_HOLDINGS`


* cash increases by notional (base) / instrument currency cash

### 5.2 FX Spot

Apply FX intents to cash balances:

* decrease `sell_currency` cash
* increase `buy_currency` cash

---

## 6. Target + Intent Fidelity Improvements

### 6.1 Target must be populated

`target.targets[]` must include final weights and target values in base currency.

### 6.2 Suppressed trades must be recorded

Any dust or min-notional suppression MUST append:

* `instrument_id`, `notional_base`, `min_required_base`, `reason_code`

---

## 7. Rule Results & Diagnostics Enhancements

### 7.1 Mandatory Rule Results

* `SINGLE_POSITION_MAX` (HARD) evaluated on after_state
* `CASH_BAND` (SOFT) evaluated on after_state
* `MIN_TRADE_SIZE` (SOFT or INFO) reflected in diagnostics

### 7.2 Data Quality

* `price_missing`, `fx_missing`, `shelf_missing`

---

## 8. Holdings-aware Golden Scenarios (Must Implement)

Scenarios under `tests/unit/dpm/golden_data/` are implemented as `scenario_10x_*` and `scenario_11x_*` files:

* **GOLDEN_101:** Simple drift rebalance with holdings (same currency).
* **GOLDEN_102:** Cash inflow with holdings.
* **GOLDEN_103:** Sell-to-fund (cash insufficient).
* **GOLDEN_104:** Multi-currency holdings with FX funding.
* **GOLDEN_105:** SELL_ONLY holding (liquidation allowed, buy blocked).
* **GOLDEN_106:** RESTRICTED instrument.
* **GOLDEN_107:** Missing price for held instrument.
* **GOLDEN_108:** Missing FX for held USD instrument.
* **GOLDEN_109:** Rounding creates slight drift; post-trade `SINGLE_POSITION_MAX` check.
* **GOLDEN_110:** Dust trades suppressed but recorded.

---

## 9. Demo Pack

Create `docs/demo/` with curated scenarios and `expected_highlights.md`.

---

## 10. Implementation Plan

1. Implement complete `before` state builder (models + engine).
2. Implement complete `after_state` simulator.
3. Add holdings-aware golden scenarios (101–110).
4. Create demo pack.
