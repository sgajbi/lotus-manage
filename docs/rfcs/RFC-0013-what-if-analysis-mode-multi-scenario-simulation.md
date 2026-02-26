# RFC-0013: "What-If" Analysis Mode (Multi-Scenario Simulation)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-17 |
| **Implemented On** | 2026-02-18 |
| **Doc Location** | docs/rfcs/RFC-0013-what-if-analysis-mode-multi-scenario-simulation.md |

---

## 0. Executive Summary

This RFC adds a batch simulation API for side-by-side strategy analysis. One request carries shared snapshots and multiple option sets. The service returns one result per scenario with consistent baseline data.

Key outcomes:
1. Lower client overhead versus repeated single-scenario calls.
2. Comparable outputs under the same portfolio and market snapshot.
3. Deterministic batch orchestration with per-scenario isolation.

---

## 1. Problem Statement

Advisors and PMs need quick comparison across policy choices. Repeating large requests for each scenario adds latency and can create accidental snapshot mismatch between calls.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Introduce a batch endpoint that accepts shared snapshots and multiple scenarios.
2. Reuse existing single-run engine path for each scenario.
3. Return stable, named per-scenario results with common batch metadata.
4. Allow frontend to compare key metrics directly.

### 2.2 Non-Goals
1. Cross-scenario optimization.
2. Scenario dependency graphing (scenario B depends on A).
3. Asynchronous distributed execution in this RFC.
4. Batch-level tax-impact comparison metrics (deferred to RFC-0015).

---

## 3. Implemented Design

### 3.1 Data Model Changes (`src/core/models.py`)

Implemented:
```python
class PortfolioSnapshot(BaseModel):
    snapshot_id: Optional[str] = None
    ...

class MarketDataSnapshot(BaseModel):
    snapshot_id: Optional[str] = None
    ...

class SimulationScenario(BaseModel):
    description: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)

class BatchRebalanceRequest(BaseModel):
    MAX_SCENARIOS_PER_REQUEST: ClassVar[int] = 20
    ...
    scenarios: Dict[str, SimulationScenario]

class BatchRebalanceResult(BaseModel):
    batch_run_id: str
    run_at_utc: str
    base_snapshot_ids: Dict[str, str]
    results: Dict[str, RebalanceResult]
    comparison_metrics: Dict[str, BatchScenarioMetric]
    failed_scenarios: Dict[str, str]
    warnings: List[str]

class BatchScenarioMetric(BaseModel):
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"]
    security_intent_count: int
    gross_turnover_notional_base: Money
```

Validation:
1. Require at least one scenario.
2. Enforce scenario name format (`[a-z0-9_\\-]{1,64}`).
3. Enforce maximum `20` scenarios per request.

Design note:
1. Scenario `options` is intentionally accepted as a loose dict and validated per scenario at runtime.
2. This enables partial batch success when one scenario has invalid options.

### 3.2 API and Orchestration (`src/api/main.py`)

Implemented endpoint:
1. `POST /rebalance/analyze`
2. Deterministic processing by sorted scenario names.
3. Reuses `run_simulation(...)` for each scenario with `request_hash=f"{batch_id}:{scenario_name}"`.
4. Per-scenario isolation:
   1. Invalid options -> `failed_scenarios[name] = "INVALID_OPTIONS: ..."`
   2. Runtime exception -> `failed_scenarios[name] = "SCENARIO_EXECUTION_ERROR: <Type>"`
5. Batch warning:
   1. Add `PARTIAL_BATCH_FAILURE` when any scenario fails.
6. Batch metadata:
   1. `base_snapshot_ids.portfolio_snapshot_id` uses `portfolio_snapshot.snapshot_id` fallback to `portfolio_id`.
   2. `base_snapshot_ids.market_data_snapshot_id` uses `market_data_snapshot.snapshot_id` fallback to `"md"`.
7. Comparison metrics included per successful scenario:
   1. `status`
   2. `security_intent_count`
   3. `gross_turnover_notional_base`

---

## 4. Test Plan and Implementation Coverage

Implemented tests:
1. `tests/unit/dpm/api/test_api_rebalance.py`
   1. Batch success flow.
   2. Invalid scenario name validation.
   3. Partial failure for invalid options with one valid scenario succeeding.
   4. Max-scenario cap enforcement.
   5. Snapshot ID fallback behavior.
   6. Deterministic sorted execution ordering.
   7. Runtime exception isolation.
   8. Comparison-metric turnover correctness.
2. `tests/unit/shared/contracts/test_contract_models.py`
   1. Scenario validation and max-scenario contract checks.
   2. Snapshot ID fields contract checks.
3. `tests/unit/dpm/golden_data/scenario_13_what_if_analysis.json`
   1. Single-run golden payload.
   2. Batch fixture payload.
4. `tests/unit/dpm/golden/test_golden_batch_analysis.py`
   1. Golden-style assertion of batch partial-failure behavior and comparison metrics.

---

## 5. Rollout and Compatibility

1. New endpoint is additive and backward compatible.
2. Existing single-run endpoint remains unchanged: `POST /rebalance/simulate`.
3. Per-scenario runs preserve existing status contract (`READY`, `PENDING_REVIEW`, `BLOCKED`).
4. Determinism remains request-bound; no persistence-backed batch replay is assumed.

### 5.1 Carry-Forward Requirements from RFC-0001 to RFC-0007A

1. Canonical single-run endpoint remains `POST /rebalance/simulate`.
2. Batch endpoint route style remains `/rebalance/analyze` (no alternate `/v1` simulate routes).
3. Existing engine safety and status semantics are preserved per scenario run.
4. Baseline assumptions from implemented RFCs (RFC-0007A, RFC-0008, RFC-0012) remain in effect.

---

## 6. Deferred Scope

1. Tax-budget controls are implemented in RFC-0009.
2. Batch-level realized gains/tax-impact comparison remains deferred to RFC-0015.
3. Batch response currently provides a turnover proxy, not tax-impact metrics.

---

## 7. Status and Reason Code Conventions

1. Per-scenario statuses remain: `READY`, `PENDING_REVIEW`, `BLOCKED`.
2. Batch warning vocabulary uses upper snake case, including `PARTIAL_BATCH_FAILURE`.
3. Per-scenario reason codes remain governed by underlying engine RFCs.
