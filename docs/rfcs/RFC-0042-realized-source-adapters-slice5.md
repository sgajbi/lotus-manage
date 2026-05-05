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
5. Follow-on WTBD-006 risk adapters in `src/core/outcomes/risk_sources.py` that wrap
   `lotus-risk` `RiskMetricsReport:v1`, drawdown response, and concentration response output into
   RFC-0042 realized `RISK_REDUCTION` evidence without recalculating risk methodology locally.
6. A follow-on WTBD-006 core cash adapter in `src/core/outcomes/core_sources.py` that wraps the
   `lotus-core` `HoldingsAsOf:v1` cash total into RFC-0042 realized `CASH_RESIDUAL` evidence
   without aggregating cash or tax/FX/transaction rows in manage.
7. Unit tests covering ready source evidence, missing execution evidence, missing risk/performance
   contracts, stale source degradation, conflicting source values, malformed source blocking,
   performance source wrapping, degraded performance-source posture, malformed performance payload
   rejection, risk source wrapping, risk supportability preservation, permission-blocked risk
   posture, malformed risk payload rejection, core cash source wrapping, degraded core cash posture,
   and invalid core cash source payload rejection.

## Source-Owner Boundary

The adapter consumes explicit source-owner snapshots. It does not call source-owner services directly
in this slice and does not calculate source-owner truth locally.

| Source Owner | RFC-0042 First-Wave Posture |
| --- | --- |
| `lotus-core` | First supported adapter consumes `HoldingsAsOf:v1` cash total evidence for `CASH_RESIDUAL`. It preserves source product metadata, as-of date, generated/evidence timestamp, data-quality posture, and source fingerprint. Missing or malformed evidence blocks affected dimensions. Tax, FX, transaction-cost, execution, and rule outcome adapters remain source-owner follow-on work until core exposes owned scalar totals or certified outcome contracts. |
| execution/OMS owner | No certified first-wave fill/order contract is assumed. Missing execution evidence emits `EXECUTION_EVIDENCE_BLOCKED`. |
| `lotus-risk` | Supported adapters consume `RiskMetricsReport:v1`, drawdown response, and concentration response evidence from `lotus-risk`. They preserve request fingerprint, selected period where applicable, selected metric/measure, source supportability, issuer coverage posture where applicable, and source reason codes. Missing evidence still emits `RISK_OUTCOME_NOT_SUPPORTED`; unavailable evidence remains degraded as `RISK_SOURCE_UNAVAILABLE`. Historical attribution and rolling-risk outcome adapters remain source-owner follow-on work. |
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
| `lotus-risk` risk metrics report source | `READY` when the source response includes the selected period, selected metric, request fingerprint, ready supportability, and numeric metric value |
| Degraded `lotus-risk` risk metrics report source | `DEGRADED` when source supportability is stale/degraded/empty/error while preserving source reason posture |
| Permission-blocked `lotus-risk` risk metrics report source | `BLOCKED` with source reason posture preserved and no ready value claim |
| Unavailable `lotus-risk` risk metrics report source | `DEGRADED` with `RISK_SOURCE_UNAVAILABLE` plus the source-supplied reason code |
| `lotus-risk` concentration response source | `READY` when the source response includes the selected HHI, top-position, issuer, or issuer-coverage measure, request fingerprint, ready supportability, and complete issuer coverage when an issuer measure is selected |
| Partial issuer-coverage `lotus-risk` concentration response source | `DEGRADED` for issuer-specific measures while preserving the source-owned concentration value and coverage posture |
| `lotus-performance` workspace-summary TWR source | `READY` when the source response includes the selected period, basis, measure, calculation id, and numeric base return |
| Unavailable `lotus-performance` workspace-summary source | `DEGRADED` with `PERFORMANCE_SOURCE_UNAVAILABLE` plus the source-supplied reason code |
| `lotus-core` HoldingsAsOf cash total source | `READY` when the source response includes product identity, portfolio id, as-of date, selected cash total, and complete/ready data quality |
| Degraded `lotus-core` HoldingsAsOf cash total source | `DEGRADED` when source data quality is incomplete, partial, stale, unavailable, or unknown |

## Core Cash Adapter Contract

`realized_cash_source_from_cash_balances_response` accepts a validated `lotus-core`
`HoldingsAsOf:v1` cash-balance response and emits a `DpmRealizedSourceSnapshot` for
`CASH_RESIDUAL`.

Implemented behavior:

1. source owner remains `lotus-core`,
2. source type is `HOLDINGS_AS_OF_CASH_BALANCE`,
3. default cash basis is the source-owned reporting-currency total,
4. optional portfolio-currency basis uses the source-owned portfolio-currency total,
5. `product_name`, `product_version`, `portfolio_id`, `as_of_date`, generated/evidence timestamp,
   data-quality status, source batch fingerprint, snapshot id, and correlation id are preserved as
   available,
6. malformed source payloads or unsupported basis requests raise `CoreOutcomeSourceError` and
   cannot silently produce a ready cash value.

Out of scope for this adapter:

1. aggregating cash-account rows locally,
2. deriving tax, FX, transaction-cost, liquidity, execution, or rule outcomes from transaction rows,
3. converting currencies locally,
4. fabricating source fingerprints, evidence timestamps, or data-quality posture.

## Risk Adapter Contract

`realized_risk_source_from_risk_metrics_report` accepts a validated `lotus-risk`
`RiskMetricsReport:v1` response and emits a `DpmRealizedSourceSnapshot` for `RISK_REDUCTION`.

Implemented behavior:

1. source owner remains `lotus-risk`,
2. source type is `RISK_METRICS_REPORT`,
3. default period/metric is `YTD` / `VOLATILITY`,
4. source metric values are preserved in source units without local risk recalculation,
5. `metadata.request_fingerprint`, selected period, selected metric, source supportability state,
   supportability reason, and as-of date are preserved as lineage/supportability evidence,
6. permission-blocked source responses become `BLOCKED` rather than degraded or ready claims,
7. malformed source payloads or missing ready metric values raise `RiskOutcomeSourceError` and
   cannot silently produce a ready outcome value.

Out of scope for this adapter:

1. calculating volatility, drawdown, VaR, Sharpe, Sortino, beta, tracking error, or information
   ratio locally,
2. deriving risk attribution or concentration outcome metrics,
3. transforming signed VaR into a positive loss convention,
4. fabricating missing source fingerprints, freshness, or observation timestamps.

## Risk Concentration Adapter Contract

`realized_concentration_source_from_concentration_response` accepts a validated `lotus-risk`
concentration response and emits a `DpmRealizedSourceSnapshot` for `RISK_REDUCTION`.

Implemented behavior:

1. source owner remains `lotus-risk`,
2. source type is `CONCENTRATION_RESPONSE`,
3. default measure is source-owned `hhi_current`,
4. selected HHI, top-position, top-N, issuer, and issuer-coverage values are preserved in source
   units without local concentration recalculation,
5. `metadata.request_fingerprint`, selected concentration measure, source supportability state,
   supportability reason, as-of date, input mode, and issuer coverage posture are preserved as
   lineage/supportability evidence,
6. issuer-specific measures degrade when issuer coverage is partial or unavailable instead of
   claiming complete readiness,
7. malformed source payloads or missing ready concentration values raise `RiskOutcomeSourceError`
   and cannot silently produce a ready outcome value.

Out of scope for this adapter:

1. calculating HHI, top-position concentration, issuer grouping, issuer coverage, or issuer
   enrichment locally,
2. deriving concentration attribution or rolling-risk context,
3. fabricating missing source fingerprints, issuer coverage status, or as-of dates.

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
python -m pytest tests\unit\core\test_risk_realized_outcome_sources.py tests\unit\core\test_realized_outcome_sources.py -q
python -m pytest tests\unit\core\test_risk_realized_outcome_sources.py -q
python -m pytest tests\unit\core\test_core_realized_outcome_sources.py tests\unit\core\test_realized_outcome_sources.py -q
python -m ruff check src\core\outcomes tests\unit\core\test_realized_outcome_sources.py
```

Observed result:

1. `6 passed`
2. `17 passed`
3. `20 passed`
4. `24 passed`
5. `18 passed`
6. `All checks passed!`

## Supported-Feature Decision

The WTBD-006 performance and risk adapters promote only implementation-backed source-integration
capabilities inside manage: RFC-0042 can now mark `PERFORMANCE` ready when a certified
`lotus-performance` workspace-summary TWR response is supplied, and `RISK_REDUCTION` ready when a
certified `lotus-risk` `RiskMetricsReport:v1`, drawdown, or concentration response is supplied.
Issuer-specific concentration evidence can be degraded when the risk-owned issuer coverage posture
is partial or unavailable. The WTBD-006 core cash adapter can mark `CASH_RESIDUAL` ready when a
certified `lotus-core` `HoldingsAsOf:v1` cash total is supplied. They do not promote a full
post-trade outcome-review product claim by themselves. Runtime support still requires durable
persistence, APIs, OpenAPI certification, live evidence, documentation publication, and downstream
realization where surfaced.
