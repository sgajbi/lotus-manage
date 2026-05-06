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
4. Follow-on WTBD-006 performance adapters in `src/core/outcomes/performance_sources.py` that
   wrap `lotus-performance` workspace-summary TWR, active return, MWR return, contribution, and
   attribution output into RFC-0042 realized `PERFORMANCE` evidence without recalculating
   performance methodology locally.
5. Follow-on WTBD-006 risk adapters in `src/core/outcomes/risk_sources.py` that wrap
   `lotus-risk` `RiskMetricsReport:v1`, drawdown response, concentration response, rolling
   metrics response, and historical attribution response output into RFC-0042 realized
   `RISK_REDUCTION` evidence without recalculating risk methodology locally.
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
| `lotus-risk` | Supported adapters consume `RiskMetricsReport:v1`, drawdown response, concentration response, rolling metrics response, and historical attribution response evidence from `lotus-risk`. They preserve request fingerprint, selected period where applicable, selected metric/measure/statistic/window, attribution type, grouping dimension, contributor group key where applicable, source supportability, benchmark/risk-free context, issuer coverage posture, attribution quality flags, stateful active-risk support metadata, and source reason codes. Missing evidence still emits `RISK_OUTCOME_NOT_SUPPORTED`; unavailable evidence remains degraded as `RISK_SOURCE_UNAVAILABLE`. |
| `lotus-performance` | Supported adapters consume `WORKSPACE_SUMMARY_TWR_RETURN`, `WORKSPACE_SUMMARY_ACTIVE_RETURN`, `WORKSPACE_SUMMARY_MWR_RETURN`, `PERFORMANCE_CONTRIBUTION`, and `PERFORMANCE_ATTRIBUTION` evidence from `lotus-performance`. They perform only percentage-point to ratio unit conversion plus lineage/supportability wrapping. Missing evidence still emits `PERFORMANCE_OUTCOME_NOT_SUPPORTED`; unavailable evidence remains degraded as `PERFORMANCE_SOURCE_UNAVAILABLE`. Broader benchmark-relative outcome analysis outside source-emitted attribution scalars remains source-owner follow-on work. |

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
| `lotus-risk` rolling metrics source | `READY` when the source response includes selected period, window length, rolling metric, statistic, request fingerprint, ready supportability, and numeric source-owned metric summary value |
| Degraded `lotus-risk` rolling metrics source | `DEGRADED` or `BLOCKED` according to source supportability and benchmark/risk-free context; manage preserves missing benchmark, missing risk-free, no-aligned-observation, stale, and permission-blocked posture |
| `lotus-risk` historical attribution source | `READY` when the source response includes selected period, attribution type, metric, grouping dimension, request fingerprint, ready supportability, and numeric source-owned set-level or explicitly selected contributor value |
| Degraded `lotus-risk` historical attribution source | `DEGRADED` when source quality flags are present or source supportability is stale/degraded; `BLOCKED` when the selected period carries a source error or source permission is blocked |
| `lotus-performance` workspace-summary TWR source | `READY` when the source response includes the selected period, basis, measure, calculation id, and numeric base return |
| `lotus-performance` contribution source | `READY` when the source response includes the selected period, selected contribution measure, calculation id, source supportability, and numeric source-owned contribution value |
| Degraded `lotus-performance` contribution source | `DEGRADED` or `BLOCKED` according to `calculation_supportability.state`; manage preserves source posture and does not promote errored or empty calculations to ready |
| `lotus-performance` attribution source | `READY` when the source response includes the selected period, selected reconciliation, level-total, or currency-attribution measure, calculation id, calculation hash, attribution model, linking method, benchmark context where available, source supportability, and numeric source-owned attribution value |
| Degraded `lotus-performance` attribution source | `DEGRADED` or `BLOCKED` according to `calculation_supportability.state`; manage preserves source posture and does not promote errored or empty attribution calculations to ready |
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

## Risk Rolling Metrics Adapter Contract

`realized_rolling_risk_source_from_rolling_response` accepts a validated `lotus-risk`
rolling metrics response and emits a `DpmRealizedSourceSnapshot` for `RISK_REDUCTION`.

Implemented behavior:

1. source owner remains `lotus-risk`,
2. source type is `ROLLING_RISK_METRICS_REPORT`,
3. default period/metric/statistic is `YTD` / `ROLLING_VOLATILITY` / `latest`,
4. selected source-owned rolling metric summary values are preserved in source decimal units,
5. `metadata.request_fingerprint`, selected period, selected window length, selected metric,
   selected statistic, source supportability state, supportability reason, benchmark context,
   risk-free context, latest observation date, input mode, and as-of date are preserved as
   lineage/supportability evidence,
6. missing benchmark or risk-free context degrades dependent metrics instead of producing a ready
   claim,
7. permission-blocked source responses become `BLOCKED` rather than degraded or ready claims,
8. malformed source payloads or missing ready metric values raise `RiskOutcomeSourceError` and
   cannot silently produce a ready outcome value.

Out of scope for this adapter:

1. calculating rolling volatility, Sharpe, beta, tracking error, information ratio, or max
   drawdown locally,
2. deriving rolling paths, warm-up windows, percentiles, benchmark alignment, or risk-free
   alignment locally,
3. fabricating missing request fingerprints, benchmark context, risk-free context, freshness, or
   observation timestamps.

## Risk Historical Attribution Adapter Contract

`realized_historical_attribution_source_from_attribution_response` accepts a validated
`lotus-risk` historical attribution response and emits a `DpmRealizedSourceSnapshot` for
`RISK_REDUCTION`.

Implemented behavior:

1. source owner remains `lotus-risk`,
2. source type is `HISTORICAL_RISK_ATTRIBUTION`,
3. default period / attribution type / metric / grouping / measure is
   `YTD` / `ACTIVE_RISK` / `TRACKING_ERROR` / `SECTOR` / `total_value`,
4. selected source-owned set-level values (`total_value`, `reconciled_sum`, `residual`) are
   preserved in source units,
5. selected contributor values are preserved only when the caller explicitly supplies
   `contributor_group_key`,
6. `metadata.request_fingerprint`, selected period, attribution type, metric, grouping dimension,
   selected measure, contributor group key where applicable, source supportability state,
   supportability reason, stateful active-risk support metadata, attribution quality-flag count,
   period error posture, input mode, period end date, and as-of date are preserved as
   lineage/supportability evidence,
7. source period errors become `BLOCKED`; source quality flags become `DEGRADED/PARTIAL`,
8. malformed source payloads, missing request fingerprints, missing ready values, or contributor
   measures without an explicit contributor group key raise `RiskOutcomeSourceError` and cannot
   silently produce a ready outcome value.

Out of scope for this adapter:

1. calculating covariance, marginal contribution, component contribution, percent contribution,
   total risk, active risk, tracking error, or residual locally,
2. summing contributors, choosing a top contributor, reconciling residuals, or deriving grouping
   semantics in manage,
3. maintaining a local stateful active-risk support matrix divergent from `lotus-risk` metadata,
4. fabricating missing request fingerprints, quality flags, support metadata, or observation dates.

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

## Performance Contribution Adapter Contract

`realized_contribution_source_from_contribution_response` accepts a validated `lotus-performance`
contribution response and emits a `DpmRealizedSourceSnapshot` for `PERFORMANCE`.

Implemented behavior:

1. source owner remains `lotus-performance`,
2. source type is `PERFORMANCE_CONTRIBUTION`,
3. default period/measure is `YTD` / `total_contribution`,
4. values are converted from `lotus-performance` percentage-point units to RFC-0042 ratio units,
5. `calculation_id`, `meta.calculation_hash`, selected period, selected contribution measure,
   `input_mode`, `calculation_supportability.state`, and `calculation_supportability.reason` are
   preserved as lineage/supportability evidence,
6. stale/degraded contribution output remains degraded, unsupported output remains not supported,
   and empty/error output blocks ready claims,
7. malformed source payloads or missing ready contribution values raise
   `PerformanceOutcomeSourceError` and cannot silently produce a ready outcome value.

Out of scope for this adapter:

1. computing contribution locally,
2. summing position, daily, hierarchy, local, or FX rows locally,
3. deriving performance attribution or benchmark-relative effects,
4. fabricating missing supportability, calculation hashes, or as-of dates.

## Performance Attribution Adapter Contract

`realized_attribution_source_from_attribution_response` accepts a validated `lotus-performance`
attribution response and emits a `DpmRealizedSourceSnapshot` for `PERFORMANCE`.

Implemented behavior:

1. source owner remains `lotus-performance`,
2. source type is `PERFORMANCE_ATTRIBUTION`,
3. default period/measure is `YTD` / `reconciliation_total_active_return`,
4. selected reconciliation, level-total, and currency-attribution values are converted from
   `lotus-performance` percentage-point units to RFC-0042 ratio units,
5. `calculation_id`, `meta.calculation_hash`, selected period, selected attribution measure,
   level dimension or currency selector, `input_mode`, attribution model, linking method,
   benchmark context, `calculation_supportability.state`, and `calculation_supportability.reason`
   are preserved as lineage/supportability evidence,
6. stale/degraded attribution output remains degraded, unsupported output remains not supported,
   and empty/error output blocks ready claims,
7. malformed source payloads or missing ready attribution values raise
   `PerformanceOutcomeSourceError` and cannot silently produce a ready outcome value.

Out of scope for this adapter:

1. computing attribution locally,
2. summing group rows or currency rows locally,
3. calculating active return, allocation, selection, interaction, residual, or currency effects,
4. choosing an attribution model or benchmark in manage,
5. fabricating missing benchmark context, supportability, calculation hashes, or as-of dates.

## Validation

Commands:

```powershell
python -m pytest tests\unit\core\test_realized_outcome_sources.py -q
python -m pytest tests\unit\core\test_performance_realized_outcome_sources.py tests\unit\core\test_realized_outcome_sources.py -q
python -m pytest tests\unit\core\test_performance_realized_outcome_sources.py -q
python -m pytest tests\unit\core\test_risk_realized_outcome_sources.py tests\unit\core\test_realized_outcome_sources.py -q
python -m pytest tests\unit\core\test_risk_realized_outcome_sources.py -q
python -m pytest tests\unit\core\test_core_realized_outcome_sources.py tests\unit\core\test_realized_outcome_sources.py -q
python -m ruff check src\core\outcomes tests\unit\core\test_realized_outcome_sources.py
```

Observed result:

1. `6 passed`
2. `17 passed`
3. `26 passed`
4. `20 passed`
5. `33 passed`
6. `18 passed`
7. `All checks passed!`

## Supported-Feature Decision

The WTBD-006 performance and risk adapters promote only implementation-backed source-integration
capabilities inside manage: RFC-0042 can now mark `PERFORMANCE` ready when a certified
`lotus-performance` workspace-summary TWR, active return, MWR, contribution, or attribution
response is supplied, and
`RISK_REDUCTION` ready when a certified `lotus-risk` `RiskMetricsReport:v1`, drawdown,
concentration, rolling metrics, or historical attribution response is supplied. Issuer-specific concentration evidence can
be degraded when the risk-owned issuer coverage posture is partial or unavailable. Rolling
benchmark-dependent and risk-free-dependent evidence can be degraded when source context is
unavailable or unaligned. Historical attribution evidence can be degraded when source quality flags
are present and blocked when the selected period carries a source-owned error. The WTBD-006 core cash adapter can
mark `CASH_RESIDUAL` ready when a certified `lotus-core` `HoldingsAsOf:v1` cash total is supplied.
They do not promote a full post-trade outcome-review product claim by themselves. Runtime support
still requires durable persistence, APIs, OpenAPI certification, live evidence, documentation
publication, and downstream realization where surfaced.
