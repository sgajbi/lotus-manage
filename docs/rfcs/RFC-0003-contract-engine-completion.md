# RFC-0003: Rebalance Simulation Contract & Engine Completion (Audit Bundle)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-14 |
| **Target Release** | Completed |
| **Doc Location** | docs/rfcs/RFC-0003-contract-engine-completion.md |

---

## 1. Executive Summary

This RFC completes the transition of the `lotus-advise` from a functional prototype to a **comprehensive audit engine**. It mandates a "No-Throw" policy for domain logic, ensuring that all runs—successful or blocked—return a structured HTTP 200 result containing the full decision context.

**Critical Upgrades:**

1. **The "Why" Trace:** The `target` output will now explicitly show the delta between `model_weight` (input) and `final_weight` (output), with reason codes (e.g., `CAPPED_BY_MAX_WEIGHT`) for every instrument.
2. **No-Throw Architecture:** Domain errors (missing data, infeasible constraints) no longer raise 422 exceptions. Instead, they produce a `BLOCKED` result with a populated `diagnostics` object.
3. **Post-Trade Rule Engine:** Formal implementation of `SINGLE_POSITION_MAX` (Hard), `CASH_BAND` (Soft), and `MIN_TRADE_SIZE` (Info/Soft) on the *simulated after-state*.
4. **Audit Completeness:** Every response must include the `before` state, `after` state, `universe` coverage, and `lineage` to guarantee historical replayability.

### 1.1 Implementation Alignment (As of 2026-02-17)

1. No-throw domain behavior is implemented for valid payloads: run outcomes are surfaced via `status` in `RebalanceResult`.
2. Rule engine currently emits `CASH_BAND`, `SINGLE_POSITION_MAX`, `DATA_QUALITY`, `MIN_TRADE_SIZE`, `NO_SHORTING`, and `INSUFFICIENT_CASH`.
3. Endpoint remains `POST /rebalance/simulate`.

---

## 2. Problem Statement

Current gaps in RFC-0002 prevent full enterprise adoption:

* **Audit Gap:** When a target is capped (e.g., 15% to 10%), the current output only shows the final 10%. Auditors cannot verify why the reduction occurred without manually checking the configuration.
* **Observability Gap:** Critical failures (e.g., "Missing Price") crash the request (422), discarding the "Universe" and "Before State" context that helps support teams debug.
* **Compliance Gap:** `SINGLE_POSITION_MAX` is currently only a target-generation constraint. It is not re-verified on the final simulated portfolio, leaving a risk that rounding or FX movements could cause a post-trade breach.

---

## 3. Goals

### 3.1 Functional Requirements

* **Protocol:** Always return **HTTP 200** for valid schemas. Use the `status` field (`READY`, `PENDING_REVIEW`, `BLOCKED`) to signal the outcome.
* **Target Lineage:** Expose `model_weight`, `constrained_weight`, and `notes` for every asset.
* **Diagnostics:** Granular reporting of `data_quality` (missing Prices, FX, or Shelf entries) and `suppressed_intents` (trades dropped due to `min_notional`).
* **Coverage Metrics:** Calculate and return `price_coverage_pct` and `fx_coverage_pct`.

### 3.2 Rule Engine (After-State Validation)

The engine must strictly evaluate the **Simulated After-State**:

| Rule ID | Type | Severity | Logic |
| --- | --- | --- | --- |
| **SINGLE_POSITION_MAX** | Hard | **FAIL (BLOCKED)** | `Position_Value_Base / Total_Value_Base > Limit` |
| **CASH_BAND** | Soft | **FAIL (PENDING)** | `Total_Cash_Base / Total_Value_Base > Limit` |
| **MIN_TRADE_SIZE** | Info | **PASS** | Log suppressed intents in diagnostics. |

---

## 4. Data Model Schema

### 4.1 Enhanced Target Object (The "Why")

```python
class TargetInstrument(BaseModel):
    instrument_id: str
    model_weight: Decimal         # The requested weight from the Strategy
    final_weight: Decimal         # The actual weight after Shelf/Constraint checks
    final_value: Money            # The monetary value of the final weight
    tags: List[str] = []          # e.g., "CAPPED_SINGLE_POS", "SELL_ONLY_ZEROED"

class TargetData(BaseModel):
    target_id: str
    strategy: Dict[str, Any]      # Strategy metadata
    targets: List[TargetInstrument]

```

### 4.2 Diagnostics & Suppression

```python
class SuppressedIntent(BaseModel):
    instrument_id: str
    reason: str                   # "BELOW_MIN_NOTIONAL"
    intended_notional: Money
    threshold: Money

class DiagnosticsData(BaseModel):
    data_quality: Dict[str, List[str]] # Keys: price_missing, fx_missing, shelf_missing
    suppressed_intents: List[SuppressedIntent] = []
    warnings: List[str] = []

```

---

## 5. Engine Execution Flow (The "Block-Accumulator")

The engine proceeds through stages, accumulating state. If a **Hard Block** occurs, it finalizes the result immediately with the gathered context.

1. **Stage 1: Valuation & Context:** Build `BeforeState`. Check Prices and FX. *Block Condition:* If critical data is missing, return `BLOCKED`.
2. **Stage 2: Universe Construction:** Filter Shelf (Approved/Banned/Sell-Only). *Block Condition:* If critical shelf entries are missing, return `BLOCKED`.
3. **Stage 3: Target Generation:** Map Model Weights and apply `SINGLE_POSITION_MAX` (Cap & Redistribute). *Block Condition:* If infeasible, return `BLOCKED` with `rule_results` explaining the math failure.
4. **Stage 4: Trade Generation:** Diff Targets vs. Current. Apply `min_notional`. Generate `OrderIntents`.
5. **Stage 5: Simulation & Final Compliance:** Create `AfterState`. Run `RuleEngine`.
* **Hard Rule Fail:** `BLOCKED`
* **Soft Rule Fail:** `PENDING_REVIEW`
* **Pass:** `READY`



---

## 6. Test Plan (Golden Scenarios)

| Scenario | Input Feature | Expected Output |
| --- | --- | --- |
| **04_dq_failure** | Asset missing price. | `status="BLOCKED"`, `diagnostics` has ID, `intents=[]`. |
| **05_constraint_fail** | 2 Assets, Max 40%, Target 50/50. | `status="PENDING_REVIEW"` in current goldens (constrained best-effort). |
| **06_suppression** | Trade size < Min Notional. | `status="READY"`, `diagnostics.suppressed_intents` populated. |
| **07_audit_trace** | Model 20% -> Capped 10%. | `target.targets` shows `model: 0.2`, `final: 0.1`, `tags: ["CAPPED..."]`. |

---

## 7. Acceptance Criteria (DoD)

1. **Contract:** All domain errors return HTTP 200 with a `RebalanceResult`.
2. **Transparency:** The `target` object explicitly proves why a weight changed from Model to Final.
3. **Safety:** Post-trade `SINGLE_POSITION_MAX` is evaluated on the final simulated values.
4. **Coverage:** 100% test coverage maintained.
5. **Lineage:** `rebalance_run_id` and `correlation_id` are present in all logs and responses.

