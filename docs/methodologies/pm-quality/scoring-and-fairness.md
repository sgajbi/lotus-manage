# PM Operating Quality Scoring and Fairness Methodology

Methodology version: `pm_quality_scoring_fairness.v3`

## Metric

This document defines the implemented `lotus-manage` methodology for:

- `PmOperatingQualityScoreRun:v1`
- `PmOperatingQualityFairnessAnalysis:v1`

The methodology is a governed support and supervisory-control method. It is not an HR,
compensation, conduct-enforcement, autonomous-ranking, client-contact, trade-approval, order-routing,
execution, OMS, risk-model, performance-attribution, tax, or source-owner methodology.

## Endpoint and Mode Coverage

Score-run preview and create use the same computation:

- `POST /api/v1/rebalance/pm-operating-quality/score-runs/preview`
- `POST /api/v1/rebalance/pm-operating-quality/score-runs`

Fairness-analysis preview and create use persisted score-run inputs:

- `POST /api/v1/rebalance/pm-operating-quality/fairness-analyses/preview`
- `POST /api/v1/rebalance/pm-operating-quality/fairness-analyses`

Read/list routes return persisted immutable evidence and do not recompute scores or fairness
posture.

Implementation mapping:

| Methodology area | Implementation function or field |
| --- | --- |
| Score-run construction | `src/core/pm_quality/scoring.py::build_pm_operating_quality_score_run` |
| Evidence item signal extraction | `_signals_from_evidence` |
| Outcome-review signal extraction | `_signals_from_outcome_reviews` |
| Indicator aggregation | `_indicator_result`, `_weighted_score` |
| Score state assignment | `_score_state`, `_score_reason_codes` |
| Lookback validation | `_validate_lookback_window`, `_signal_as_of_date` |
| Fairness analysis | `src/core/pm_quality/fairness_analysis.py::build_pm_operating_quality_fairness_analysis` |
| Segment averaging and spread | `_fairness_segment_evaluation`, `_observed_average_score_spread` |
| Response fields | `score`, `state`, `indicator_results`, `observed_average_score_spread`, `segment_results` |

## Inputs

Score-run inputs:

| Input | Contract field |
| --- | --- |
| Portfolio manager identity | `pm_id` |
| Optional book identity | `book_id` |
| Score business date | `as_of_date` |
| Bank policy | `DpmPmOperatingQualityPolicy` |
| Source evidence signals | `DpmPmQualityEvidenceItem[]` |
| Optional outcome reviews | `DpmPostTradeOutcomeReview[]` |
| Optional Core PM-book evidence | `book_scope_evidence` |
| Optional peer/lookback scope evidence | `scope_evidence` |
| Actor/service | `generated_by` |
| Correlation id | `correlation_id` |

Fairness-analysis inputs:

| Input | Contract field |
| --- | --- |
| Shared policy identity | `policy_id`, `policy_version` |
| Shared analysis business date | `as_of_date` |
| Source-defined segment inputs | `segments[]` |
| Minimum score runs per segment | `minimum_segment_score_run_count` |
| Maximum average-score spread | `maximum_average_score_spread` |
| Actor/service | `generated_by` |
| Correlation id | `correlation_id` |

## Upstream Data Sources

Manage consumes source-owned evidence; it does not recalculate upstream methodologies.

| Source family | How it is used |
| --- | --- |
| Caller-supplied PM-quality evidence items | Supplies indicator, state, optional score, reason codes, and source refs. |
| `DpmPostTradeOutcomeReview` | Derives outcome-discipline, source-quality, and evidence-completeness signals from persisted outcome-review state. |
| `lotus-core PortfolioManagerBookMembership:v1` | Optional PM-book membership materialization and source-ready scope evidence. |
| Bank policy/governance records | Supplies weights, thresholds, approved uses, bank approval, fairness-review evidence, peer group, and lookback rules. |
| Persisted `PmOperatingQualityScoreRun:v1` | Supplies fairness segment members; fairness analysis does not recompute the score runs. |

## Unit Conventions

- Scores are bounded decimal points on a `0..100` scale.
- Weights are relative positive decimal weights, not percentages that must sum to `100`.
- Thresholds are decimal score points on the same `0..100` scale.
- Date-only business fields are canonical ISO `YYYY-MM-DD` strings. They reject timestamps,
  compact dates, month labels, and arbitrary text before hashing or persistence.
- Approval, fairness-review, and generated-at instants are timezone-aware UTC timestamps.
  Offset-bearing inputs normalize to UTC before persisted evidence and content hashes are built.
- `DpmPmQualityLookbackWindowPolicy.timezone` records the approved business-calendar context; the
  implementation does not convert timestamps or infer business dates from month labels.

## Variable Dictionary

| Symbol | Field or implementation value | Meaning |
| --- | --- | --- |
| `i` | `DpmPmQualityWeight.indicator` | Configured indicator name. |
| `w_i` | `DpmPmQualityWeight.weight` | Relative weight for indicator `i`. |
| `m_i` | `DpmPmQualityWeight.minimum_evidence_count` | Minimum signal count required for indicator `i`. |
| `S_i` | `DpmPmQualityIndicatorResult.score` | Mean score for scorable signals in indicator `i`. |
| `N_i` | `DpmPmQualityIndicatorResult.evidence_count` | Signal count found for indicator `i`. |
| `Q` | `DpmPmOperatingQualityScoreRun.score` | Weighted score-run score. |
| `R` | `DpmPmOperatingQualityScoreRun.state` | Score-run state. |
| `T_ready` | `policy.ready_threshold` | Minimum score for `READY` when no indicator is breached or degraded. |
| `T_watch` | `policy.watch_threshold` | Minimum score for `PENDING_REVIEW` when no indicator is breached or degraded. |
| `A_s` | `DpmPmQualityFairnessSegmentResult.average_score` | Average score for ready score runs in segment `s`. |
| `C_s` | `DpmPmQualityFairnessSegmentResult.score_run_count` | Persisted score-run count in segment `s`. |
| `M` | `minimum_segment_score_run_count` | Minimum score-run count per segment. |
| `D` | `observed_average_score_spread` | Difference between maximum and minimum ready segment average scores. |
| `D_max` | `maximum_average_score_spread` | Governed maximum average-score spread before review is required. |

## Methodology and Formulas

State-to-score mapping for signals without explicit numeric score:

| Evidence state | State-derived score |
| --- | ---: |
| `READY` | `100` |
| `PENDING_REVIEW` | `70` |
| `DEGRADED` | `60` |
| `NOT_SUPPORTED` | `50` |
| `BREACHED` | `35` |
| `BLOCKED` | `0` |
| `DISABLED` | `0` |
| Unknown state | `0` |

Indicator score:

`S_i = mean(signal_score_1, signal_score_2, ..., signal_score_N)`

If `N_i < m_i`, indicator `i` is `BLOCKED` with `score = null`.

Weighted score:

`Q_raw = sum(S_i * w_i for scorable indicators) / sum(w_i for scorable indicators)`

`Q = round_half_up(Q_raw, 2 decimal places)`

Score-run state:

1. Any blocked indicator makes the score run `BLOCKED` and `score = null`.
2. Any `BREACHED` indicator makes the score run `BREACHED`.
3. Any `DEGRADED` indicator makes the score run `DEGRADED`.
4. Otherwise, `Q >= T_ready` makes the score run `READY`.
5. Otherwise, `Q >= T_watch` makes the score run `PENDING_REVIEW`.
6. Otherwise, the score run is `BREACHED`.

Fairness segment score:

`A_s = mean(score_run.score for score_run in segment s where score_run.score is not null)`

`minimum_score_s = min(scorable scores in segment s)`

`maximum_score_s = max(scorable scores in segment s)`

Score runs in states `READY`, `PENDING_REVIEW`, `DEGRADED`, and `BREACHED` are scorable for
fairness segment averages when `score` is not null. `DISABLED` and `BLOCKED` score runs are not
scorable. If `C_s < M` or no score in the segment is scorable, the segment is `BLOCKED`.
Fairness analysis uses caller/source-defined operating segments only; it does not infer protected
classes or create PM rankings.

Observed average-score spread:

`D = round_half_up(max(A_s for READY segments) - min(A_s for READY segments), 2 decimal places)`

Fairness-analysis state:

1. Any blocked segment makes the analysis `BLOCKED`.
2. Fewer than two ready segment averages makes the analysis `BLOCKED`.
3. `D > D_max` makes the analysis `PENDING_REVIEW`.
4. Otherwise the analysis is `READY`.

## Step-by-Step Computation

Score-run algorithm:

1. Verify `policy.as_of_date == as_of_date`.
2. If `policy.enabled` is false, return `DISABLED`, `score = null`, and no indicator results.
3. Validate governance approval, fairness-review evidence, expiry, actor entitlement, policy uses,
   unique indicators, and threshold order.
4. Convert evidence items into signals. Use explicit `score` when supplied; otherwise use the
   state-to-score mapping.
5. Convert outcome reviews into outcome-discipline, source-quality, and evidence-completeness
   signals when supplied.
6. If a lookback window is configured, read the first non-empty `source_ref.source_version` on each
   signal as the signal business date and require it to be inside the inclusive window.
7. For each configured indicator, collect matching signals and compute the mean signal score if the
   minimum evidence count is met.
8. Block the score run if any configured indicator is blocked.
9. Compute the weighted score over scorable indicators only and round with `ROUND_HALF_UP` to two
   decimals.
10. Assign state from indicator states and thresholds.
11. Build `source_refs`, `reason_codes`, canonical `content_hash`, and stable content-addressed
   `score_run_id`.

Fairness-analysis algorithm:

1. Require at least two source-defined segments.
2. Require `minimum_segment_score_run_count >= 1`.
3. Require `0 <= maximum_average_score_spread <= 100`.
4. For each segment, require all score runs to share the requested policy id, policy version, and
   as-of date.
5. For each segment, require the score-run count to meet `minimum_segment_score_run_count`.
6. Compute segment average, minimum, and maximum over score runs whose `score` is not null.
7. Block the analysis if any segment is blocked or fewer than two ready segment averages remain.
8. Compute observed spread and compare it with `maximum_average_score_spread`.
9. Build deduplicated source refs, reason codes, canonical `content_hash`, and stable
   content-addressed `fairness_analysis_id`.

## Validation and Failure Behavior

| Condition | Behavior or error |
| --- | --- |
| Malformed date-only PM-quality field | `INVALID_PM_QUALITY_BUSINESS_DATE:<field>` at API/domain validation boundary |
| Malformed PM-quality UTC timestamp | `INVALID_PM_QUALITY_UTC_TIMESTAMP:<field>` at API/domain validation boundary |
| Policy/date mismatch | `PM_QUALITY_POLICY_AS_OF_DATE_MISMATCH` |
| Enabled policy missing governance approval | `PM_QUALITY_GOVERNANCE_APPROVAL_REQUIRED` |
| Governance expiry date invalid after boundary bypass | `PM_QUALITY_GOVERNANCE_EXPIRY_DATE_INVALID` |
| Governance expired before run date | `PM_QUALITY_GOVERNANCE_EXPIRED` |
| Actor not entitled when allow-list is supplied | `PM_QUALITY_ACTOR_NOT_ENTITLED` |
| Lookback date invalid after boundary bypass | `PM_QUALITY_LOOKBACK_WINDOW_DATE_INVALID` |
| Lookback enabled but a signal has no business date | `PM_QUALITY_LOOKBACK_WINDOW_EVIDENCE_DATE_REQUIRED` |
| Signal business date is invalid | `PM_QUALITY_EVIDENCE_AS_OF_DATE_INVALID` |
| Signal business date outside inclusive window | `PM_QUALITY_EVIDENCE_OUTSIDE_LOOKBACK_WINDOW` |
| No scorable indicator after blocking | `PM_QUALITY_NO_SCORABLE_INDICATORS` |
| Fewer than two fairness segments | `PM_QUALITY_FAIRNESS_SEGMENTS_REQUIRED` |
| Invalid fairness minimum count | `PM_QUALITY_FAIRNESS_MINIMUM_COUNT_INVALID` |
| Invalid fairness spread threshold | `PM_QUALITY_FAIRNESS_SPREAD_THRESHOLD_INVALID` |
| Segment has too few score runs | Segment `BLOCKED` with `PM_QUALITY_FAIRNESS_SEGMENT_MINIMUM_NOT_MET` |
| Segment has no scorable score | Segment `BLOCKED` with `PM_QUALITY_FAIRNESS_SEGMENT_NO_SCORABLE_RUNS` |
| Segment score-run policy/as-of mismatch | `PM_QUALITY_FAIRNESS_SCORE_RUN_SCOPE_MISMATCH` |
| Any segment blocked | Analysis `BLOCKED` with `PM_QUALITY_FAIRNESS_SEGMENT_BLOCKED` |
| Fewer than two comparable ready segments | Analysis `BLOCKED` with `PM_QUALITY_FAIRNESS_COMPARABLE_SEGMENTS_REQUIRED` |

## Configuration Options

| Configuration | Field |
| --- | --- |
| Enable/disable scoring | `policy.enabled` |
| Indicator set and weights | `policy.weights[]` |
| Required evidence count | `policy.weights[].minimum_evidence_count` |
| Ready/watch thresholds | `policy.ready_threshold`, `policy.watch_threshold` |
| Allowed use posture | `policy.allowed_uses` |
| Governance approval and fairness review | `policy.governance_approval` |
| Actor allow-list | `policy.governance_approval.entitled_actor_ids` |
| Peer-group context | `policy.peer_group_policy` |
| Lookback window | `policy.lookback_window_policy` |
| Fairness segment minimum | `minimum_segment_score_run_count` |
| Fairness spread threshold | `maximum_average_score_spread` |

## Outputs

Score-run outputs:

- `score`: weighted score rounded to two decimals, or `null` for `DISABLED`/`BLOCKED`.
- `state`: `DISABLED`, `READY`, `PENDING_REVIEW`, `DEGRADED`, `BREACHED`, or `BLOCKED`.
- `indicator_results`: decomposed indicator score, state, count, reasons, weights, and refs.
- `scope_evidence`, `book_scope_evidence`, `governance_evidence`: source-backed context.
- `content_hash`: canonical hash covering policy, score, states, refs, and evidence context.

Fairness outputs:

- `segment_results`: per-segment count, average, minimum, maximum, state, reasons, and refs.
- `observed_average_score_spread`: rounded spread between ready segment averages, or `null`.
- `state`: `READY`, `PENDING_REVIEW`, or `BLOCKED`.
- `content_hash`: canonical hash covering segment results, thresholds, reasons, and refs.

## Worked Example

Score-run example policy:

| Indicator | Weight | Minimum count |
| --- | ---: | ---: |
| `OUTCOME_DISCIPLINE` | `60` | `1` |
| `SOURCE_QUALITY` | `40` | `1` |

Thresholds: `ready_threshold = 85`, `watch_threshold = 70`.

Signals:

| Indicator | Evidence state | Explicit score | Used score | Business date |
| --- | --- | ---: | ---: | --- |
| `OUTCOME_DISCIPLINE` | `READY` | `90` | `90` | `2026-05-10` |
| `OUTCOME_DISCIPLINE` | `PENDING_REVIEW` | null | `70` | `2026-05-11` |
| `SOURCE_QUALITY` | `READY` | `75` | `75` | `2026-05-11` |

Intermediate calculation:

| Indicator | Formula | Result |
| --- | --- | ---: |
| `OUTCOME_DISCIPLINE` | `(90 + 70) / 2` | `80.00` |
| `SOURCE_QUALITY` | `75 / 1` | `75.00` |
| Weighted numerator | `(80 * 60) + (75 * 40)` | `7800` |
| Total scorable weight | `60 + 40` | `100` |
| `score` | `round_half_up(7800 / 100, 2)` | `78.00` |

No indicator is blocked, breached, or degraded. `78.00 < 85` and `78.00 >= 70`, so
`state = PENDING_REVIEW` and `reason_codes` include `PM_QUALITY_REQUIRES_REVIEW`.

Fairness example:

| Segment | Score-run scores | Count | Average | Minimum | Maximum |
| --- | --- | ---: | ---: | ---: | ---: |
| `sg-core` | `88`, `84` | `2` | `86.00` | `84` | `88` |
| `hk-core` | `76`, `74` | `2` | `75.00` | `74` | `76` |

With `minimum_segment_score_run_count = 2` and `maximum_average_score_spread = 10`:

`observed_average_score_spread = round_half_up(86.00 - 75.00, 2) = 11.00`

Because `11.00 > 10`, `state = PENDING_REVIEW` and `reason_codes` include
`PM_QUALITY_FAIRNESS_SPREAD_REVIEW_REQUIRED`.

Methodology-change checklist:

1. Update this document before changing weights, state scores, aggregation, lookback semantics,
   fairness spread behavior, validation behavior, or content-hash inputs.
2. Update PM-quality domain tests and golden examples.
3. Review OpenAPI examples, endpoint certification, README, wiki, data-product declarations, and
   Gateway/Workbench downstream impact.
4. Re-run PM-quality API, domain, Postgres, observability, and documentation gates before merge.
