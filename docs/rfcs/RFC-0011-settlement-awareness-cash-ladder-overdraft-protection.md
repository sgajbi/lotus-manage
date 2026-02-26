# RFC-0011: Settlement Awareness (Cash Ladder & Overdraft Protection)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-17 |
| **Target Release** | 2026-02-18 |
| **Doc Location** | docs/rfcs/RFC-0011-settlement-awareness-cash-ladder-overdraft-protection.md |

---

## 0. Executive Summary

This RFC adds settlement-time-aware cash simulation. The engine will no longer assume same-day netting between buys and sells with different settlement cycles.

Key outcomes:
1. Instrument-level settlement metadata (`settlement_days`).
2. Per-currency cash ladder from T+0 to configured horizon.
3. Hard block when any day breaches available cash unless overdraft is enabled.

---

## 1. Problem Statement

Current simulation is timing-blind. It can approve a set of trades that is net-cash-neutral at run level but negative on settlement dates. This produces settlement failures and invalid execution instructions.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Add settlement-day metadata to tradable instruments.
2. Build per-currency cash ladder in Stage 5.
3. Enforce no-negative-balance policy by settlement date.
4. Surface ladder diagnostics with breach details.

### 2.2 Non-Goals
1. Intraday settlement windows.
2. Credit-line pricing and optimization.
3. Settlement netting rules by broker/custodian variant.

---

## 3. Proposed Implementation

### 3.1 Data Model Changes (`src/core/models.py`)

```python
class ShelfEntry(BaseModel):
    instrument_id: str
    settlement_days: int = Field(default=2, ge=0, le=10)

class CashLadderPoint(BaseModel):
    date_offset: int
    currency: str
    projected_balance: Decimal

class DiagnosticsData(BaseModel):
    cash_ladder: List[CashLadderPoint] = Field(default_factory=list)
```

Implemented extension:
1. `options.max_overdraft_by_ccy: Dict[str, Decimal]`.

Runtime toggle:
1. Settlement behavior is request-scoped via `options.enable_settlement_awareness`.
2. Default is `False` for backward compatibility.

### 3.2 Simulation Logic (`src/core/dpm/engine.py`)

Modify Stage 5 simulation to evaluate settlement timing.

Algorithm:
1. Build `flows[currency][day]` initialized to zero through `horizon_days`.
2. Seed day 0 with currently settled cash.
3. Map each intent:
   1. Security buy: negative cash flow at `settlement_days`.
   2. Security sell: positive cash flow at `settlement_days`.
   3. FX: apply pair flows at configured FX settlement day (default 2).
4. Compute cumulative balances by day per currency.
5. Validate each day:
   1. If balance drops below allowed overdraft threshold, block run.
   2. Attach reason code `OVERDRAFT_ON_T_PLUS_N`.
6. Persist full ladder to diagnostics.

Determinism:
1. Use stable ordering of intents and currencies.
2. Round only at final reporting boundary, not during accumulation.





---

## 4. Test Plan

Add `tests/unit/dpm/golden_data/scenario_11_settlement_fail.json`.

Scenario:
1. Settled cash: 0.
2. Sell `Slow_Fund` (T+3) and buy `Fast_Stock` (T+1) for equal notional.

Expected:
1. Negative balance on T+1 and T+2.
2. Status `BLOCKED`.
3. Diagnostics contain ladder points and first breach day.

Add second case with overdraft allowance and verify status changes from `BLOCKED` to `READY` with warning diagnostics.

---

## 5. Rollout and Compatibility

1. Backward compatible via default `settlement_days=2`.
2. Existing scenarios without settlement metadata continue to run unchanged.
3. Update UI/docs to show day-level cash availability.

### 5.1 Carry-Forward Requirements from RFC-0001 to RFC-0007A

1. Canonical simulate endpoint remains `POST /rebalance/simulate`.
2. Settlement ladder checks are additive and must not weaken existing hard-block safety checks (`NO_SHORTING`, `INSUFFICIENT_CASH`, reconciliation mismatch block).
3. Non-zero holdings locking (`qty != 0`) from RFC-0007A is already implemented and must be preserved.

---

## 6. Open Questions

1. Settlement horizon is implemented as `max(configured_horizon, max_intent_settlement_day)` to avoid truncating intent cash flows.
2. Should FX settlement days be instrumented by currency pair or globally configured?

---

## 7. Status and Reason Code Conventions

1. Run status values remain aligned to RFC-0007A: `READY`, `PENDING_REVIEW`, `BLOCKED`.
2. Overdraft breaches are blocking and use diagnostics reason codes in upper snake case.
3. This RFC introduces reason and warning codes:
   1. `OVERDRAFT_ON_T_PLUS_N` (blocking reason pattern)
   2. `SETTLEMENT_OVERDRAFT_UTILIZED` (non-blocking warning when overdraft facility is used)
