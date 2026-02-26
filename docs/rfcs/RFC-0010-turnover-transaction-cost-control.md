# RFC-0010: Turnover & Transaction Cost Control

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-17 |
| **Implemented On** | 2026-02-18 |
| **Doc Location** | docs/rfcs/RFC-0010-turnover-transaction-cost-control.md |

---

## 0. Executive Summary

This RFC adds a deterministic turnover budget to Stage 4 intent selection so rebalances can stop at a configured turnover ceiling instead of always taking the full candidate set.

Implemented outcomes:
1. Option-controlled turnover cap (`max_turnover_pct`).
2. Deterministic intent ranking and subset selection when proposed turnover exceeds budget.
3. Explicit diagnostics for dropped intents and partial-rebalance warning.

---

## 1. Problem Statement

Full convergence can produce low-value extra trades and higher implementation churn. The engine now supports deterministic “best-effort” execution under a turnover budget.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Add `max_turnover_pct` to engine options.
2. Select a deterministic subset of candidate security intents under budget.
3. Preserve compatibility when option is unset.
4. Expose dropped intents and warning codes.

### 2.2 Non-Goals
1. Partial sizing of a selected intent.
2. Explicit spread/impact/commission calibration.
3. Multi-period turnover planning.

---

## 3. Implemented Design

### 3.1 Data Model Changes (`src/core/models.py`)

Implemented:
```python
class EngineOptions(BaseModel):
    max_turnover_pct: Optional[Decimal] = None

class DroppedIntent(BaseModel):
    instrument_id: str
    reason: str
    potential_notional: Money
    score: Decimal

class DiagnosticsData(BaseModel):
    dropped_intents: List[DroppedIntent] = Field(default_factory=list)
```

Validation:
1. `max_turnover_pct` must be within `[0, 1]` when provided.

### 3.2 Stage-4 Intent Selection (`src/core/dpm/engine.py`)

Implemented in `_apply_turnover_limit(...)`, called after `_generate_intents(...)` and before Stage 5 simulation.

Algorithm:
1. If `max_turnover_pct` is `None`, keep existing behavior.
2. Compute budget:
   1. `budget = portfolio_value_base * max_turnover_pct`
3. Compute proposed turnover:
   1. `proposed = sum(abs(intent.notional_base.amount))`
4. If proposed is within budget, keep all intents.
5. Else rank candidate intents by:
   1. primary: descending score (`abs(notional_base) / portfolio_value_base`)
   2. secondary: lower absolute notional first
   3. tertiary: `instrument_id` ascending
   4. quaternary: `intent_id` ascending
6. Iterate ranked intents:
   1. keep if `used + notional <= budget`
   2. otherwise drop and continue (skip-and-continue)
7. For each dropped intent, append diagnostics:
   1. `reason = TURNOVER_LIMIT`
   2. `potential_notional` in base currency
   3. computed score
8. If any dropped intents exist, append warning:
   1. `PARTIAL_REBALANCE_TURNOVER_LIMIT`

---

## 4. Test Plan and Coverage

Implemented tests:
1. Contract tests (`tests/unit/shared/contracts/test_contract_models.py`)
   1. `max_turnover_pct` bounds validation.
   2. diagnostics support for dropped intents.
2. Engine tests (`tests/unit/dpm/engine/test_engine_turnover_control.py`)
   1. Skip-and-continue selection under cap.
   2. Exact-fit deterministic combination.
   3. Backward compatibility when cap is unset.
3. Golden scenarios:
   1. `tests/unit/dpm/golden_data/scenario_10_turnover_cap.json`
   2. `tests/unit/dpm/golden_data/scenario_10_turnover_exact_fit.json`

---

## 5. Rollout and Compatibility

1. Backward compatible by default (`max_turnover_pct=None`).
2. Existing endpoint contracts remain unchanged:
   1. `POST /rebalance/simulate`
   2. `POST /rebalance/analyze`
3. Stage-5 safety/compliance and reconciliation behavior remains intact.

### 5.1 Carry-Forward Requirements from RFC-0001 to RFC-0007A

1. Canonical single-run endpoint remains `POST /rebalance/simulate`.
2. Safety checks (`NO_SHORTING`, `INSUFFICIENT_CASH`, reconciliation) remain active post-selection.
3. Universe locking behavior for non-zero holdings is preserved.

---

## 6. Deferred Scope

1. Explicit transaction-cost model (spread/commission/slippage terms) is deferred to RFC-0015.
2. Partial intent sizing is deferred to RFC-0015.

---

## 7. Status and Reason Code Conventions

1. Run statuses remain `READY`, `PENDING_REVIEW`, `BLOCKED`.
2. New reason/warning codes:
   1. `TURNOVER_LIMIT` (dropped intent reason)
   2. `PARTIAL_REBALANCE_TURNOVER_LIMIT` (diagnostic warning)

---

## 8. Behavior Reference (Implemented)

### 8.1 Budget Application Behavior

1. If `max_turnover_pct` is not set, all eligible intents proceed (legacy behavior).
2. If set, turnover budget is computed from current portfolio base value.
3. If proposed turnover is above budget, deterministic subset selection is applied.

### 8.2 Deterministic Selection Behavior

1. Candidate intents are ranked using documented tie-break rules.
2. The engine uses skip-and-continue inclusion under budget.
3. Kept intents are executed; dropped intents are recorded with notional and score.
4. This can result in intentionally partial convergence by design.

### 8.3 Status and Diagnostics Behavior

1. Dropped intents produce `TURNOVER_LIMIT` reason entries in diagnostics.
2. Partial selection adds warning `PARTIAL_REBALANCE_TURNOVER_LIMIT`.
3. Turnover logic alone does not force `BLOCKED`; final status still depends on
   downstream hard and soft rule outcomes.
