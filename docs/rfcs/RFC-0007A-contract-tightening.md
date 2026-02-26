# RFC-0007A: Contract Tightening - Canonical Endpoint, Discriminated Intents, Valuation Policy, Universe Locking

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-16 |
| **Target Release** | Completed |
| **Doc Location** | docs/rfcs/RFC-0007A-contract-tightening.md |

---

## 0. Executive Summary

This RFC tightens API and core semantics to remove ambiguity and align demos/tests with one contract.

1. Canonical endpoint is `POST /rebalance/simulate` in current implementation.
2. Intents are discriminated unions (`SECURITY_TRADE`, `FX_SPOT`).
3. Valuation mode is explicit via `options.valuation_mode` (`CALCULATED`, `TRUST_SNAPSHOT`).
4. Universe locking semantics are tightened, with one remaining gap for non-zero holdings handling.

### 0.1 Implementation Alignment (As of 2026-02-17)

Implemented:
1. Discriminated intents in response models (`src/core/models.py`).
2. `valuation_mode` in options (`src/core/models.py`).
3. Single active simulate route (`src/api/main.py`).

Pending:
1. None.

---

## 1. Problem Statement

Pre-persistence institutional risks are ambiguity and contract drift:
1. Route mismatch across docs, demos, and tests.
2. Nullable intent structures that are easy to misuse.
3. Implicit valuation assumptions.
4. Incomplete locking semantics for non-zero holdings.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Keep one canonical route: `/rebalance/simulate`.
2. Enforce discriminated intent schema.
3. Keep valuation mode explicit in options.
4. Align locking behavior with non-zero holdings policy.

### 2.2 Non-Goals
1. Persistence / DB idempotency (deferred).
2. OMS execution integration.

---

## 3. Canonical API

### 3.1 Endpoint

Canonical route: `POST /rebalance/simulate`.

### 3.2 Required Headers

1. `Idempotency-Key` (required).
2. `X-Correlation-Id` (optional).

### 3.3 Request Schema (Current)

```json
{
  "portfolio_snapshot": { "...": "..." },
  "market_data_snapshot": { "...": "..." },
  "model_portfolio": { "...": "..." },
  "shelf_entries": [{ "...": "..." }],
  "options": {
    "valuation_mode": "CALCULATED",
    "allow_restricted": false,
    "suppress_dust_trades": true,
    "min_trade_notional": { "amount": 2000, "currency": "SGD" },
    "cash_band_min_weight": 0.01,
    "cash_band_max_weight": 0.05,
    "single_position_max_weight": 0.10,
    "block_on_missing_prices": true,
    "block_on_missing_fx": true
  }
}
```

---

## 4. Discriminated Intent Model

### 4.1 SecurityTradeIntent

1. `intent_type = SECURITY_TRADE`.
2. `instrument_id` required.
3. `quantity` and/or `notional` used with `notional_base` for auditability.

### 4.2 FxSpotIntent

1. `intent_type = FX_SPOT`.
2. Pair and buy/sell currency fields required.
3. No `instrument_id`.

### 4.3 Validation

Pydantic discriminator validation enforces intent type shape.

---

## 5. Valuation Policy

### 5.1 Options

`options.valuation_mode`: `CALCULATED` (default) or `TRUST_SNAPSHOT`.

### 5.2 CALCULATED

1. Values computed from price/fx paths.
2. Supports reconciliation consistency.

### 5.3 TRUST_SNAPSHOT

1. Trust snapshot market values where present.
2. Can result in reconciliation mismatch; final status handling remains per current engine behavior.

---

## 6. Universe and Locking Semantics

### 6.1 Non-zero Holdings

Target policy is to apply locking for `pos.quantity != 0`.

Current implementation note:
1. `_build_universe` applies locking for held positions using `pos.quantity != 0`.

### 6.2 Negative Holdings

Negative holdings are blocked downstream by safety rule `NO_SHORTING` with reason `SELL_EXCEEDS_HOLDINGS`.

### 6.3 Shelf Status Behavior

1. `SELL_ONLY`: buy blocked, sell allowed.
2. `RESTRICTED`: buy blocked unless `allow_restricted=true`.
3. `SUSPENDED` / `BANNED`: excluded/locked behavior applied by universe logic.

---

## 7. Implementation Plan (Remaining)

1. Keep `/rebalance/simulate` as the stable canonical simulate endpoint across docs, tests, and API.
2. Keep exactly one canonical route (no `/v1` compatibility alias in this RFC scope).
3. Re-run contract and golden tests after locking updates.

---

## 8. Acceptance Criteria

1. Exactly one simulate endpoint exists and docs match it.
2. Intents remain discriminated unions in responses.
3. `valuation_mode` behavior is test-covered.
4. Locking applies to all non-zero holdings.
5. `ruff check` and `pytest` pass.
