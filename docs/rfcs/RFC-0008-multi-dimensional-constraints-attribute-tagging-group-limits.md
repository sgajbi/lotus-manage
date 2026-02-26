# RFC-0008: Multi-Dimensional Constraints (Attribute Tagging and Group Limits)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-17 |
| **Target Release** | Completed |
| **Doc Location** | docs/rfcs/RFC-0008-multi-dimensional-constraints-attribute-tagging-group-limits.md |

---

## 0. Executive Summary

This RFC adds portfolio-level diversification constraints using attribute tags on instruments and max-weight rules by group (for example, `sector=TECH <= 20%`).

It extends Stage 3 target generation so the engine can:
1. Track exposure by arbitrary attributes.
2. Cap constrained groups when overweight.
3. Reallocate released weight to eligible unconstrained assets.

---

## 1. Problem Statement

Current controls (`single_position_max_weight`, `cash_band`) are not sufficient for institutional mandates that constrain aggregate exposure by category.

Example mandate:
`sector=TECH <= 20%` and `region=EM <= 15%`.

Without group constraints, a portfolio can satisfy single-name limits but still violate risk policy at sector or region level.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Add flexible attribute tagging to shelf instruments.
2. Add configurable max-weight group constraints.
3. Enforce these constraints during target generation.
4. Surface post-run allocation breakdown by attribute for auditability.

### 2.2 Non-Goals
1. Minimum group exposure constraints (`>=`) in this RFC.
2. Cross-group optimization with strict global optimality (handled by RFC-0012).
3. Tax, turnover, or settlement logic changes.

---

## 3. Proposed Design

### 3.1 Data Model Changes (`src/core/models.py`)

```python
class ShelfEntry(BaseModel):
    instrument_id: str
    status: Literal["APPROVED", "RESTRICTED", "BANNED", "SUSPENDED", "SELL_ONLY"]
    asset_class: str = "UNKNOWN"
    min_notional: Optional[Money] = None
    attributes: Dict[str, str] = Field(default_factory=dict)

class GroupConstraint(BaseModel):
    max_weight: Decimal  # 0 <= max_weight <= 1

class EngineOptions(BaseModel):
    # Key format: "<attribute_key>:<attribute_value>", for example "sector:TECH"
    group_constraints: Dict[str, GroupConstraint] = Field(default_factory=dict)

```

Validation rules:

1. Reject malformed keys without exactly one `:`.
2. Reject `max_weight < 0` or `max_weight > 1`.

### 3.2 Target-Generation Logic (`src/core/dpm/engine.py`)

Apply group constraints in Stage 3 before single-position max check.

Algorithm (deterministic order by key):

1. Parse each constraint key into `(attr_key, attr_value)`.
2. Compute `group_weight` from current candidate target weights.
3. If `group_weight <= max_weight`, continue.
4. If breached:
1. Compute `scale = max_weight / group_weight`.
2. Scale all instruments in that group by `scale`.
3. Add released weight into `excess_pool`.


5. Redistribute `excess_pool` proportionally across eligible instruments not in the breached group, excluding blocked instruments.
6. Normalize to 1.0 within tolerance.

Tie-break and safety rules:

1. If no eligible destination exists for redistribution, return `BLOCKED` with reason `NO_ELIGIBLE_REDISTRIBUTION_DESTINATION`.
2. Record diagnostics: breached groups, released weight, redistribution recipients.

### 3.3 Reporting (`src/core/valuation.py` and result models)

Add optional attribute-level breakdown:

```python
class SimulatedState(BaseModel):
    # Existing fields...
    allocation_by_attribute: Dict[str, List[AllocationMetric]] = Field(default_factory=dict)

```

This enables direct verification of group-limit compliance from response payloads.

---

## 4. Test Plan

Add `tests/unit/dpm/golden_data/scenario_08_sector_cap.json`.

Scenario:

1. Initial portfolio is 100% cash.
2. Model targets: `Tech_A=15%`, `Tech_B=15%`, `Bond_C=70%`.
3. Shelf tags: `Tech_A/Tech_B -> {"sector":"TECH"}`.
4. Constraint: `sector:TECH <= 20%`.

Expected:

1. `Tech_A + Tech_B == 20%` (scaled from 30%).
2. `Bond_C == 80%`.
3. Status `READY`.
4. Diagnostics include `CAPPED_BY_GROUP_LIMIT`.

---

## 5. Rollout and Compatibility

1. Backward compatible: default `group_constraints={}` preserves current behavior.
2. Add warnings for unknown attribute keys in constraints.
3. Update API docs with key format and validation errors.

### 5.1 Carry-Forward Requirements from RFC-0001 to RFC-0007A

1. Canonical simulate endpoint remains `POST /rebalance/simulate`.
2. Universe-locking semantics use `qty != 0` so group exposure accounts for all non-zero held positions.
3. Do not assume persistence-backed idempotency store exists; keep behavior compatible with current stateless run flow.

---

## 6. Open Questions

1. Should group-key parsing remain string-based or evolve to structured config (`attribute`, `value`)?
2. Should instrument-level hard caps be reapplied after each redistribution pass or once at the end?

---

## 7. Status and Reason Code Conventions

1. Run status values remain aligned to RFC-0007A: `READY`, `PENDING_REVIEW`, `BLOCKED`.
2. Constraint events are emitted as diagnostics reason codes in upper snake case.
3. This RFC introduces reason codes:
1. `CAPPED_BY_GROUP_LIMIT`
2. `NO_ELIGIBLE_REDISTRIBUTION_DESTINATION`

---

## 8. Behavior Reference (Implemented)

### 8.1 Group Cap Enforcement

1. The engine computes provisional target weights first.
2. Each configured group limit is evaluated in deterministic key order.
3. If a group exceeds its cap, all members of that group are scaled down proportionally.
4. Released weight is redistributed to eligible instruments outside breached groups.

### 8.2 Redistributed Weight Safety

1. Redistribution excludes blocked or ineligible instruments.
2. If there is no valid destination for released weight, the run is blocked with
   `NO_ELIGIBLE_REDISTRIBUTION_DESTINATION`.
3. Final target weights are normalized with tolerance-aware precision handling.

### 8.3 Observable Output for BA and Control Teams

1. Group-cap effects are visible through diagnostics reason codes.
2. Allocation breakdowns remain auditable in the simulated after-state outputs.
3. Status contract remains unchanged (`READY`, `PENDING_REVIEW`, `BLOCKED`), so no
   downstream status integration changes are required.
