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
4. A follow-on WTBD-006 performance adapter in `src/core/outcomes/performance_sources.py` that
   wraps `lotus-performance` workspace-summary TWR return output into RFC-0042 realized
   `PERFORMANCE` evidence without recalculating performance methodology locally.
5. Unit tests covering ready source evidence, missing execution evidence, missing risk/performance
   contracts, stale source degradation, conflicting source values, malformed source blocking,
   performance source wrapping, degraded performance-source posture, and malformed performance
   payload rejection.

## Source-Owner Boundary

The adapter consumes explicit source-owner snapshots. It does not call source-owner services directly
in this slice and does not calculate source-owner truth locally.

| Source Owner | RFC-0042 First-Wave Posture |
| --- | --- |
| `lotus-core` | Can provide explicit realized snapshots for holdings drift, booked transaction cost, cash residual, tax, FX, and rule evidence when a certified source contract is supplied. Missing or malformed evidence blocks affected dimensions. |
| execution/OMS owner | No certified first-wave fill/order contract is assumed. Missing execution evidence emits `EXECUTION_EVIDENCE_BLOCKED`. |
| `lotus-risk` | Existing risk APIs exist, but no RFC-0042-certified review-window outcome contract is assumed by manage. Missing risk evidence emits `RISK_OUTCOME_NOT_SUPPORTED`. |
| `lotus-performance` | First supported adapter consumes `WORKSPACE_SUMMARY_TWR_RETURN` evidence from the `lotus-performance` workspace-summary response. It performs only percentage-point to ratio unit conversion plus lineage wrapping. Missing evidence still emits `PERFORMANCE_OUTCOME_NOT_SUPPORTED`; unavailable evidence remains degraded as `PERFORMANCE_SOURCE_UNAVAILABLE`. Richer MWR, contribution, and attribution outcome adapters remain source-owner follow-on work. |

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
| `lotus-performance` workspace-summary TWR source | `READY` when the source response includes the selected period, basis, measure, calculation id, and numeric base return |
| Unavailable `lotus-performance` workspace-summary source | `DEGRADED` with `PERFORMANCE_SOURCE_UNAVAILABLE` plus the source-supplied reason code |

## Performance Adapter Contract

`realized_performance_source_from_workspace_summary` accepts a validated `lotus-performance`
workspace-summary response and emits a `DpmRealizedSourceSnapshot` for `PERFORMANCE`.

Implemented behavior:

1. source owner remains `lotus-performance`,
2. source type is `WORKSPACE_SUMMARY_TWR_RETURN`,
3. default period/basis/measure is `YTD` / `net` / `cumulative_return`,
4. values are converted from `lotus-performance` percentage-point units to RFC-0042 ratio units,
5. `calculation_id`, `calculation_hash`, selected period, selected basis, selected measure, and
   source reason codes are preserved as lineage/supportability evidence,
6. malformed source payloads raise `PerformanceOutcomeSourceError` and cannot silently produce a
   ready outcome value.

Out of scope for this adapter:

1. computing TWR locally,
2. deriving benchmark-relative performance,
3. calculating MWR, contribution, or attribution,
4. fabricating missing source freshness or observation timestamps.

## Validation

Commands:

```powershell
python -m pytest tests\unit\core\test_realized_outcome_sources.py -q
python -m pytest tests\unit\core\test_performance_realized_outcome_sources.py tests\unit\core\test_realized_outcome_sources.py -q
python -m ruff check src\core\outcomes tests\unit\core\test_realized_outcome_sources.py
```

Observed result:

1. `6 passed`
2. `17 passed`
3. `All checks passed!`

## Supported-Feature Decision

The WTBD-006 performance adapter promotes only an implementation-backed source-integration
capability inside manage: RFC-0042 can now mark `PERFORMANCE` ready when a certified
`lotus-performance` workspace-summary TWR response is supplied to the realized-source boundary.
It does not promote a full post-trade outcome-review product claim by itself. Runtime support still
requires durable persistence, APIs, OpenAPI certification, live evidence, documentation publication,
and downstream realization where surfaced.
