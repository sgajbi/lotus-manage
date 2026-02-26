# RFC-0006B: Pre-Persistence Hardening - Rules Configurability, Dependency Fidelity & Scenario Matrix

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-15 |
| **Target Release** | Completed |
| **Doc Location** | docs/rfcs/RFC-0006B-pre-persistence-rules-scenarios-demo.md |

---

## 0. Executive Summary

RFC-0006B bridges the gap between a functional calculator and a demo-credible, institution-ready engine. It focuses on **configurability**, **auditability**, and **regression depth** by:

1.  **Configurable Rules:** Replacing hard-coded thresholds (e.g., 5% cash, 10% concentration) with overrideable options/policies.
2.  **Explicit Dependencies:** Ensuring every FX-funded Security Buy explicitly links to its funding FX trade in the `dependencies` list.
3.  **Institutional Scenario Matrix:** Implementing the `GOLDEN_3xx` suite—12+ scenarios covering real-world lotus-manage edge cases (Drift, Sell-to-Fund, Multi-Currency, Restricted Assets).
4.  **Demo Pack Tightening:** Updating `docs/demo/` so all scenarios are triggerable purely via JSON input, without code manipulation.

### 0.1 Implementation Alignment (As of 2026-02-17)

1. 300-series golden scenarios are implemented as `scenario_301` to `scenario_312` files.
2. Dependency linking for FX-funded buys is implemented in `_generate_fx_and_simulate`.
3. Rule emission includes all core rule IDs; `MIN_TRADE_SIZE` currently emits as `SOFT/PASS` with diagnostics context.

---

## 1. Problem Statement

Despite recent hardening (RFC-0006A), the engine remains rigid and difficult to demo effectively:

* **Rigid Rules:** `CASH_BAND` (5%) and `SINGLE_POSITION_MAX` are often hard-coded or inconsistently applied.
* **Implicit Ordering:** Downstream systems (OMS) must guess trade execution order; the engine does not explicitly state "Buy AAPL *after* selling SGD/USD".
* **Gap in Coverage:** Existing golden scenarios are simplistic. We lack a comprehensive matrix covering complex multi-currency rebalancing, partial funding, and regulatory locking.
* **Demo Friction:** Current demos often require "pretending" logic exists or manually tweaking code to trigger specific blocks.

---

## 2. Goals

### 2.1 Rules & Configurability
* **Source of Truth:** Rule parameters must be derived from `options` (request-scoped overrides) with sensible system defaults.
* **Standardized Emission:** The response `rule_results` must **always** contain entries for the core rule set (PASS or FAIL):
    * `SINGLE_POSITION_MAX` (Hard)
    * `CASH_BAND` (Soft)
    * `MIN_TRADE_SIZE` (Info/Soft)
    * `DATA_QUALITY` (Hard)
    * `NO_SHORTING` (Hard)

### 2.2 Dependency Fidelity
* **Linkage:** If a `SECURITY_TRADE` (Buy) requires foreign currency, it must list the corresponding `FX_SPOT` intent ID in its `dependencies`.
* **Determinism:** Generate at most one consolidated FX intent per currency pair per run (Hub-and-Spoke model).

### 2.3 Golden Scenario Matrix (The 300 Series)
Implement a robust suite (`tests/unit/dpm/golden_data/GOLDEN_3xx_*.json`) covering:
* **301:** Drift Rebalance (Sell Overweight / Buy Underweight, same currency).
* **302:** Sell-to-Fund (Cash insufficient; Sell must precede Buy).
* **303:** Multi-Currency + FX Funding.
* **304:** Partial Funding (Use existing foreign cash + Top-up FX).
* **305:** `SELL_ONLY` asset held (Buy blocked, Liquidation allowed).
* **306:** `RESTRICTED` asset (Excluded if allow=false, Included if allow=true).
* **307:** `SUSPENDED` asset (Locked/Frozen).
* **308:** `BANNED` asset (Forced liquidation or Locked).
* **309:** Missing Price (Hard Block).
* **310:** Missing FX Rate (Hard Block).
* **311:** Post-Rounding Constraint Breach (e.g., rounding up causes >10% weight).
* **312:** Dust Suppression (Trades < Min Notional suppressed & logged).

---

## 3. Implementation Specification

### 3.1 Options Configuration
The `EngineOptions` model will be expanded to support granular overrides:

```python
class EngineOptions(BaseModel):
    # Rules
    cash_band_min_weight: Decimal = Decimal("0.01")
    cash_band_max_weight: Decimal = Decimal("0.05")
    single_position_max_weight: Optional[Decimal] = Decimal("0.10") # Default 10%
    min_trade_notional: Optional[Money] = None # e.g., 2000 SGD

    # Behavior
    allow_restricted: bool = False
    suppress_dust_trades: bool = True
    fx_buffer_pct: Decimal = Decimal("0.01")
    block_on_missing_prices: bool = True
    block_on_missing_fx: bool = True

```

### 3.2 Dependency Logic Update

In `src/core/dpm/engine.py` -> `_generate_fx_and_simulate`:

1. Identify net cash flow per currency.
2. Generate required FX intents.
3. **Pass 2:** Iterate all `SECURITY_TRADE` Buys.
* If `buy_currency != base_currency`:
* Find the FX intent ID for that currency.
* Append to `intent.dependencies`.





### 3.3 Demo Pack Deliverables

The `docs/demo/` directory will be reorganized:

* `01_standard_drift.json` (Golden 301)
* `02_sell_to_fund.json` (Golden 302)
* `03_multi_currency_fx.json` (Golden 303)
* `04_safety_sell_only.json` (Golden 305)
* `05_safety_hard_block_price.json` (Golden 309)

---

## 4. Acceptance Criteria (DoD)

1. **Configurability:** Changing `options.cash_band_max_weight` in the request directly affects the `CASH_BAND` rule result status.
2. **Dependencies:** A multi-currency run produces a JSON response where `intents[x].dependencies` contains the ID of the FX trade.
3. **Regression:** All 12 `GOLDEN_3xx` scenarios pass in `pytest` with exact JSON matching.
4. **Cleanliness:** No hard-coded `0.05` or `0.10` constants remain in `src/core/compliance.py` or `engine.py`.

## 5. Behavior Reference (Implemented)

### 5.1 Rules Configurability in Runtime

1. Request `options` are the first-level source of truth for rule thresholds.
2. If an option is omitted, model defaults apply.
3. Rule outputs are always present for the core set, even if a rule is passing.
4. This guarantees stable response shape for downstream consumers.

### 5.2 FX Dependency Fidelity

1. When a buy requires non-base currency funding, the engine creates `FX_SPOT` intents as needed.
2. The dependent buy intent includes the relevant FX intent id in `dependencies`.
3. Dependency ordering is deterministic and stable for the same payload.
4. If required FX data is unavailable and blocking is enabled, status is `BLOCKED`.

### 5.3 Demo and Golden Behavior Guarantees

1. Golden 300-series scenarios are used as behavioral contracts, not only smoke tests.
2. A scenario that should block must consistently block with expected reason codes.
3. A scenario that should pass must preserve deterministic intent ordering and diagnostics.
4. Demo JSON files are aligned to these contracts so business walkthroughs match API behavior.
