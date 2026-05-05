# RFC-0042 Slice 5 - Realized Source Adapters and Degraded Source Handling

| Field | Value |
| --- | --- |
| **RFC** | RFC-0042 Post-Trade Outcome Feedback Loop |
| **Slice** | Slice 5 - Realized Source Adapters and Degraded Source Handling |
| **Implementation Branch** | `feat/rfc0042-implementation` |
| **Date** | 2026-05-05 |
| **Status** | DONE |

---

## Implemented Scope

Slice 5 adds the source-owner realized evidence boundary:

1. `DpmOutcomeReviewWindow`, `DpmRealizedSourceSnapshot`, and `DpmRealizedOutcomeSnapshot` domain
   contracts.
2. `src/core/outcomes/realized_sources.py`, which converts explicit source-owner realized evidence
   into comparable `DpmOutcomeMetricValue` entries.
3. Degraded, blocked, missing, stale, unavailable, partial, malformed, conflicting, and not-supported
   source behavior.
4. Unit tests covering ready source evidence, missing execution evidence, missing risk/performance
   contracts, stale source degradation, conflicting source values, and malformed source blocking.

## Source-Owner Boundary

The adapter consumes explicit source-owner snapshots. It does not call source-owner services directly
in this slice and does not calculate source-owner truth locally.

| Source Owner | RFC-0042 First-Wave Posture |
| --- | --- |
| `lotus-core` | Can provide explicit realized snapshots for holdings drift, booked transaction cost, cash residual, tax, FX, and rule evidence when a certified source contract is supplied. Missing or malformed evidence blocks affected dimensions. |
| execution/OMS owner | No certified first-wave fill/order contract is assumed. Missing execution evidence emits `EXECUTION_EVIDENCE_BLOCKED`. |
| `lotus-risk` | Existing risk APIs exist, but no RFC-0042-certified review-window outcome contract is assumed by manage. Missing risk evidence emits `RISK_OUTCOME_NOT_SUPPORTED`. |
| `lotus-performance` | Existing performance APIs exist, but no RFC-0042-certified review-window outcome contract is assumed by manage. Missing performance evidence emits `PERFORMANCE_OUTCOME_NOT_SUPPORTED`. |

## Degraded-State Mapping

| Source Quality | RFC-0042 State |
| --- | --- |
| `COMPLETE` with a value | `READY` |
| `MISSING`, `MALFORMED`, `CONFLICTING` | `BLOCKED` |
| `STALE`, `UNAVAILABLE`, `PARTIAL` | `DEGRADED` |
| `NOT_SUPPORTED` | `NOT_SUPPORTED` |
| Missing `EXECUTION_QUALITY` source | `BLOCKED` with `EXECUTION_EVIDENCE_BLOCKED` |
| Missing `RISK_REDUCTION` source | `NOT_SUPPORTED` with `RISK_OUTCOME_NOT_SUPPORTED` |
| Missing `PERFORMANCE` source | `NOT_SUPPORTED` with `PERFORMANCE_OUTCOME_NOT_SUPPORTED` |

## Validation

Commands:

```powershell
python -m pytest tests\unit\core\test_realized_outcome_sources.py -q
python -m ruff check src\core\outcomes tests\unit\core\test_realized_outcome_sources.py
```

Observed result:

1. `6 passed`
2. `All checks passed!`

## Supported-Feature Decision

No supported feature is promoted by Slice 5. This slice proves source evidence translation and
degraded-state handling only. Runtime support still requires durable persistence, APIs, OpenAPI
certification, live evidence, documentation publication, and downstream realization where surfaced.
