# RFC-0002: Rebalance Simulation MVP Hardening & Enterprise Completeness

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-13 |
| **Target Release** | Completed |
| **Doc Location** | docs/rfcs/RFC-0002-rebalance-simulation-mvp-hardening-enterprise-completeness.md |

---

## 0. Executive Summary

RFC-0001 delivered the baseline functional simulation engine and API. This RFC hardens and completes the MVP to **enterprise/production-grade** status by closing critical operational, audit, and compliance gaps.

The focus of this phase is **Safety, Auditability, and Completeness**:
1.  **Golden Endpoint Expansion:** Upgrading the response to include deterministic `before`/`after` states, `universe` composition, `rule_results`, and cryptographic `lineage`.
2.  **Persistence & Idempotency:** Guaranteeing safe retries in a distributed system via strict idempotency keys and request hashing.
3.  **Currency Truth Model:** Standardizing on Base Currency valuation to eliminate floating-point and multi-currency drift risks.
4.  **Post-Trade Compliance:** Simulating the after-state and routing it through a v1 Rule Engine for Hard/Soft constraint validation.
5.  **Product Shelf Completeness:** Encoding enterprise shelf semantics (`RESTRICTED`, `SELL_ONLY`) and mapping FX funding dependencies.
6.  **RFC 7807 Error Model:** Standardizing domain failures (e.g., Infeasible Constraints) into machine-readable Problem Details payloads.

### 0.1 Implementation Alignment (As of 2026-02-17)

1. Implemented endpoint is `POST /rebalance/simulate`.
2. Implemented contract returns full `RebalanceResult` with `before`, `after_simulated`, `rule_results`, `diagnostics`, `lineage`.
3. Domain failures are represented as `status=BLOCKED` within HTTP 200 for valid payloads.
4. PostgreSQL persistence and idempotency key store are not implemented.
5. `Reconciliation` is implemented with `status: OK|MISMATCH` and mismatch blocks the run.

---

## 1. Problem Statement

While the current MVP successfully generates mathematically correct trade intents, it lacks the surrounding scaffolding required by a regulated private bank:
* **Audit Deficit:** It does not persist the exact inputs and outputs, making point-in-time historical reconstruction difficult.
* **Operational Risk:** Without idempotency, upstream timeouts could result in duplicate heavy computations or duplicate trade file generation.
* **Compliance Gap:** The engine caps single positions during target generation but does not formally evaluate the *simulated after-state* against soft policies (e.g., Cash Drag) or output standardized Reason Codes.
* **Observability Void:** Missing correlation IDs and standardized metric emission prevents automated alerting on data quality (DQ) failures.

---

## 2. Goals

### 2.1 Functional Goals
* **Golden Contract:** `POST /rebalance/simulate` returns the audit bundle (Before, Target, Universe, Intents, After, Rules, Explanation, Diagnostics, Lineage).
* **Run Persistence:** Deferred.
* **Strict Idempotency:** Header is required; durable key/hash store is deferred.
* **Canonical Valuation:** Ensure consistent valuation sizing across base and instrument currencies (The "Currency Truth Model").
* **Rule Engine v1:** Evaluate `CASH_BAND` (Soft), `SINGLE_POSITION_MAX` (Hard), and `MIN_TRADE_SIZE` (Soft/Configurable).
* **Shelf Semantics:** Strictly enforce `APPROVED`, `RESTRICTED`, `SELL_ONLY`, `SUSPENDED`, and `BANNED`.
* **Intent Dependencies:** Explicitly link `SECURITY_TRADE` buys to the `FX_SPOT` trades that fund them.

### 2.2 Enterprise Goals
* Standardize RFC 7807 HTTP error mapping (`422` for domain errors, `409` for idempotency conflicts).
* Mandate W3C Trace Context (`X-Correlation-Id`) in all logs, metrics, and API responses.
* Emit Prometheus metrics for pipeline stage latencies and DQ exclusion counts.

### 2.3 Non-Goals
* OMS execution routing or FIX connectivity.
* Recursive, multi-pass optimization solvers.
* Tax-lot (HIFO/LIFO) level optimization.

---

## 3. Design Overview



The hardening process introduces wrapping layers around the pure functional core from RFC-0001:
1.  **Pre-Flight:** Idempotency Check & Request Hashing.
2.  **Core (Upgraded):** Universe builder respects new shelf semantics; Target builder enforces the Currency Truth Model.
3.  **Post-Flight:** After-State Simulator generates the post-trade portfolio; Rule Engine evaluates constraints; Persistence layer writes the audit bundle to the DB asynchronously.

---

## 4. API Contract Upgrade

### 4.1 Request Contract
**Endpoint:** `POST /rebalance/simulate`
**Headers:**
* `Idempotency-Key` (Required, UUID/String)
* `X-Correlation-Id` (Optional, generated if missing)

**Payload Additions:**
```json
"options": {
  "allow_restricted": false,
  "suppress_dust_trades": true,
  "dust_trade_threshold": { "amount": 2000, "currency": "SGD" },
  "fx_buffer_pct": 0.01,
  "block_on_missing_prices": true
}

```

### 4.2 Response Contract (The Audit Bundle)

```json
{
  "rebalance_run_id": "rr_20260213_abc123",
  "correlation_id": "c_8f7e6d5c",
  "status": "PENDING_REVIEW",
  "before": {
    "total_value": { "amount": 1200000, "currency": "SGD" },
    "allocation": [
      { "bucket": "EQUITY", "weight": 0.45 },
      { "bucket": "CASH", "weight": 0.55 }
    ],
    "cash_balances": [
      { "currency": "SGD", "available": 660000, "settled": 660000, "pending": 0 }
    ]
  },
  "universe": {
    "universe_id": "uni_rr_0001",
    "eligible_for_buy": ["ins_us_eq_etf"],
    "eligible_for_sell": ["ins_us_eq_etf", "ins_legacy_fund"],
    "excluded": [
      { "instrument_id": "ins_banned", "reason_code": "SHELF_STATUS_BANNED" }
    ],
    "coverage": { "price_coverage_pct": 1.0, "fx_coverage_pct": 1.0 }
  },
  "target": {
    "target_id": "tp_rr_0001",
    "strategy": { "model_portfolio_id": "model_growth", "version": 1 },
    "targets": [
      { "instrument_id": "ins_us_eq_etf", "target_weight": 0.80, "target_value": { "amount": 960000, "currency": "SGD" } }
    ]
  },
  "intents": [
    {
      "intent_id": "oi_fx_0001",
      "type": "FX_SPOT",
      "pair": "USD/SGD",
      "side": "BUY_BASE_SELL_QUOTE",
      "buy_amount": { "amount": 40200, "currency": "USD" },
      "sell_amount": { "amount": 54270, "currency": "SGD" },
      "dependencies": [],
      "rationale": { "code": "FUNDING", "message": "Fund USD-denominated buys" }
    },
    {
      "intent_id": "oi_sec_0002",
      "type": "SECURITY_TRADE",
      "instrument_id": "ins_us_eq_etf",
      "side": "BUY",
      "quantity": 50,
      "notional": { "amount": 25000, "currency": "USD" },
      "dependencies": ["oi_fx_0001"],
      "rationale": { "code": "DRIFT_REBALANCE", "message": "Increase equity sleeve toward model target" }
    }
  ],
  "after_simulated": {
    "total_value": { "amount": 1200000, "currency": "SGD" },
    "allocation": [
      { "bucket": "EQUITY", "weight": 0.80 },
      { "bucket": "CASH", "weight": 0.20 }
    ],
    "cash_balances": [
      { "currency": "SGD", "available": 240000, "settled": 240000, "pending": 0 }
    ]
  },
  "rule_results": [
    {
      "rule_id": "CASH_BAND",
      "severity": "SOFT",
      "status": "FAIL",
      "measured": 0.20,
      "threshold": { "min": 0.01, "max": 0.05 },
      "reason_code": "THRESHOLD_BREACH",
      "remediation_hint": "Client retains excess cash intentionally; requires advisor override."
    }
  ],
  "explanation": {
    "summary": "Rebalance triggered to deploy excess cash into US Equities.",
    "trigger": { "type": "CASH_DRIFT" }
  },
  "diagnostics": {
    "warnings": [],
    "suppressed_intents": [],
    "data_quality": { "price_missing": [], "price_stale": [], "fx_missing": [] }
  },
  "lineage": {
    "portfolio_snapshot_id": "ps_123",
    "market_data_snapshot_id": "md_456",
    "effective_policy_version_id": "ep_789",
    "request_hash": "sha256:a1b2c3d4..."
  }
}

```

---

## 5. Persistence & Idempotency

### 5.1 Idempotency Logic

Current implementation:
1. `Idempotency-Key` header is required by API schema.
2. Header value is passed as `request_hash` into `run_simulation`.
3. Persistence-backed key/hash replay logic is deferred.

### 5.2 Schema Design (PostgreSQL, Deferred)

**Table: `rebalance_runs**`

* `rebalance_run_id` (VARCHAR PK)
* `correlation_id` (VARCHAR)
* `status` (VARCHAR)
* `request_hash` (VARCHAR)
* `response_payload` (JSONB)
* `created_at` (TIMESTAMPTZ)

**Table: `idempotency_keys**`

* `idempotency_key` (VARCHAR PK)
* `request_hash` (VARCHAR)
* `rebalance_run_id` (VARCHAR FK)
* `expires_at` (TIMESTAMPTZ)

---

## 6. Valuation & Currency Truth Model

To prevent floating-point drift and multi-currency netting errors, the engine must adopt a single "Currency of Truth."

### 6.1 The Base Currency Axiom

* **All** portfolio valuation, target sizing, rule evaluations, and excess weight redistributions must occur mathematically in the **Portfolio Base Currency**.
* Conversion to Instrument Currency happens *only* at the final Trade Translation step to determine `quantity`.

### 6.2 Valuation Hierarchy

For any given position:

1. If `market_value` (in base currency) is provided in the snapshot → **USE IT** (Trust the upstream ledger).
2. If `market_value` is missing, but `quantity`, `price`, and `fx_rate` are available → **COMPUTE IT**:
`Value_Base = Quantity * Price_Instr * FX_Rate(Instr_to_Base)`
3. If `price` or `fx_rate` is missing → **DATA QUALITY FAILURE** (Block run or exclude asset based on `block_on_missing_prices` config).

### 6.3 Mathematical Invariants (For Golden Tests)

* `Total_Value_Base == Sum(Position_Value_Base) + Sum(Cash_Value_Base)`
* `Sum(Target_Weights) == 1.0`
* For every intent: `Notional_Base ≈ Quantity * Price_Instr * FX_Rate`

---

## 7. After-State Simulation Module

The simulator calculates the `after_simulated` state by applying `OrderIntents` to the `before` state.

**Execution Rules (MVP Assuming Immediate Settlement):**

* **SECURITY BUY:** Decrease cash (in instrument currency) by `Notional`. Increase position `Quantity`.
* **SECURITY SELL:** Increase cash (in instrument currency) by `Notional`. Decrease position `Quantity`. *(Rule: Block if Quantity < 0, shorting out of scope)*.
* **FX SPOT BUY:** Decrease Base Cash by `Sell_Amount`. Increase Foreign Cash by `Buy_Amount`.

*Note: In the simulated after-state, the mathematical `Total_Value_Base` should remain nearly identical to the `before` state, minus the configurable FX Buffer spread.*

---

## 8. Product Shelf Semantics & Intent Dependencies

### 8.1 Shelf Status Enforcement Matrix

| Status | Buy Eligible? | Sell Eligible? | Engine Action if Violated |
| --- | --- | --- | --- |
| `APPROVED` | Yes | Yes | Proceed normally. |
| `RESTRICTED` | Config-dependent | Yes | Exclude from targets if `allow_restricted=false`. |
| `SELL_ONLY` | **No** | Yes | Set Target to 0%. Generate SELL intent if held. |
| `SUSPENDED` | No | No | Exclude entirely. Freeze current holdings. |
| `BANNED` | No | Yes | Set Target to 0%. Generate SELL intent. |
| *(Missing)* | No | No | BLOCK RUN (`SHELF_ENTRY_MISSING`). |

### 8.2 Dependency Graphing

To assist downstream OMS orchestrators, intents must explicitly declare relationships:

* If a `SECURITY_TRADE` (Buy USD Apple) relies on an `FX_SPOT` (Buy USD / Sell SGD), the Security Intent must list the FX Intent ID in its `dependencies` array.

---

## 9. Rule Engine v1 (Post-Trade Compliance)

Constraints are evaluated against the `after_simulated` portfolio.

### 9.1 Evaluation Logic

1. **SINGLE_POSITION_MAX (Severity: HARD)**
* Evaluates: `Max(Position_Value_Base / Total_Value_Base)`
* If Breach: Status = `FAIL`. Run Status forced to `BLOCKED`.


2. **CASH_BAND (Severity: SOFT)**
* Evaluates: `Total_Cash_Base / Total_Value_Base`
* If Breach: Status = `FAIL`. Run Status escalated to `PENDING_REVIEW`.


3. **MIN_TRADE_SIZE (Severity: SOFT)**
* Evaluates: Intent Notional vs Shelf `min_notional`.
* Action: Suppresses intent. Logs to `diagnostics.suppressed_intents`.



### 9.2 Run Status Escalation

* Start with `READY`.
* If any Soft rule fails -> `PENDING_REVIEW`.
* If any Hard rule or Data Quality check fails -> `BLOCKED`.

---

## 10. Error Model (RFC 7807) & Observability

### 10.1 Problem Details Payload

Current implementation uses HTTP 200 with `status=BLOCKED` for domain failures on valid requests. HTTP 422 remains for request validation failures.

```json
{
  "type": "[https://errors.api.bank.com/dpm/constraint-infeasible](https://errors.api.bank.com/dpm/constraint-infeasible)",
  "title": "Constraint Infeasible",
  "status": 422,
  "error_code": "CONSTRAINT_INFEASIBLE",
  "detail": "Redistributing excess weight from Apple (AAPL) caused Microsoft (MSFT) to breach the 50% max limit.",
  "instance": "/rebalance/simulate",
  "correlation_id": "c_8f7e6d5c",
  "meta": {
    "rule_id": "SINGLE_POSITION_MAX",
    "instrument_id": "ins_msft"
  }
}

```

### 10.2 Observability Requirements

* **Structured Logging:** Every log emitted during the request lifecycle MUST include `correlation_id` and `rebalance_run_id`.
* **Metrics:** Prometheus counters for `dpm_rebalance_runs_total{status="READY|BLOCKED|PENDING_REVIEW"}` and `dpm_dq_failures_total{type="MISSING_PRICE|STALE_PRICE"}`.

---

## 11. Acceptance Criteria (Definition of Done)

1. **API Contract:** Endpoint successfully returns the expanded JSON bundle (Before, After, Lineage, Rules).
2. **Idempotency:** Identical payloads with the same key return cached 200s. Divergent payloads with the same key return 409s.
3. **Valuation Correctness:** Golden tests prove mathematical parity between derived and explicit base-currency valuations.
4. **After-State Validation:** Sum of simulated asset weights and cash weights strictly equals 1.0.
5. **Compliance Routing:** Hard failures successfully block the run; Soft failures trigger `PENDING_REVIEW`.
6. **Shelf Filtering:** `SELL_ONLY` assets correctly block buys but permit liquidation sells.
7. **Error Handling:** Infeasible mathematical distributions properly throw RFC 7807 422 errors, not 500s.
8. **Test Coverage:** Contract tests and Golden Scenarios expanded and maintaining 100% CI coverage.
