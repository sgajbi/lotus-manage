"""Pure scoring engine for configurable PM operating quality."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal, Mapping
from uuid import uuid5, NAMESPACE_URL

from src.core.outcomes import DpmOutcomeSourceRef, DpmPostTradeOutcomeReview
from src.core.pm_quality.models import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityFairnessSegmentResult,
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityGovernanceEvidence,
    DpmPmQualityEvidenceItem,
    DpmPmQualityIndicatorResult,
    DpmPmQualityLookbackWindowPolicy,
    DpmPmQualityPeerGroupPolicy,
    DpmPmQualityScopeEvidence,
    DpmPmQualityWeight,
    PmQualityFairnessSegmentType,
    PmQualityState,
)


class DpmPmQualityValidationError(Exception):
    """Raised when a PM quality score run cannot be evaluated safely."""


@dataclass(frozen=True)
class _PmQualitySignal:
    indicator: str
    score: Decimal
    state: str
    reason_codes: list[str]
    source_refs: list[DpmOutcomeSourceRef]
    as_of_date: str | None = None


@dataclass(frozen=True)
class DpmPmQualityFairnessSegmentInput:
    """Source-defined segment and its persisted score-run members."""

    segment_id: str
    segment_type: PmQualityFairnessSegmentType
    display_name: str
    score_runs: list[DpmPmOperatingQualityScoreRun]
    source_refs: list[DpmOutcomeSourceRef]


@dataclass(frozen=True)
class _PeerGroupScopeFields:
    peer_group_id: str | None
    display_name: str | None
    segment_type: PmQualityFairnessSegmentType | None
    minimum_peer_count: int | None


@dataclass(frozen=True)
class _LookbackScopeFields:
    window_id: str | None
    start_date: str | None
    end_date: str | None
    timezone: str | None


@dataclass(frozen=True)
class _FairnessPosture:
    state: PmQualityState
    observed_spread: Decimal | None
    reason_codes: list[str]


@dataclass(frozen=True)
class _GovernanceExpiryEvaluation:
    expires_on: str | None
    reason_codes: list[str]


@dataclass(frozen=True)
class _ActorEntitlementEvaluation:
    state: Literal["AUTHORIZED", "NOT_SUPPLIED"]
    reason_codes: list[str]


_PM_QUALITY_STATE_RANK: dict[str, int] = {
    "BLOCKED": 6,
    "BREACHED": 5,
    "DEGRADED": 4,
    "PENDING_REVIEW": 3,
    "READY": 2,
    "DISABLED": 1,
}

_NORMALIZED_WORST_STATE: dict[str, PmQualityState] = {
    "BLOCKED": "BLOCKED",
    "BREACHED": "BREACHED",
    "DEGRADED": "DEGRADED",
    "NOT_SUPPORTED": "DEGRADED",
    "PENDING_REVIEW": "PENDING_REVIEW",
    "READY": "READY",
    "DISABLED": "DISABLED",
}


def build_pm_operating_quality_score_run(
    *,
    pm_id: str,
    book_id: str | None,
    as_of_date: str,
    policy: DpmPmOperatingQualityPolicy,
    evidence_items: list[DpmPmQualityEvidenceItem],
    outcome_reviews: list[DpmPostTradeOutcomeReview],
    book_scope_evidence: DpmPmQualityBookScopeEvidence | None = None,
    scope_evidence: DpmPmQualityScopeEvidence | None = None,
    generated_by: str,
    correlation_id: str,
) -> DpmPmOperatingQualityScoreRun:
    """Build an explainable PM quality score run from source-backed evidence."""

    if policy.as_of_date != as_of_date:
        raise DpmPmQualityValidationError("PM_QUALITY_POLICY_AS_OF_DATE_MISMATCH")
    if scope_evidence is None:
        scope_evidence = _scope_evidence_from_policy(policy)
    generated_at = datetime.now(timezone.utc)
    if not policy.enabled:
        return _disabled_score_run(
            pm_id=pm_id,
            book_id=book_id,
            as_of_date=as_of_date,
            policy=policy,
            generated_at=generated_at,
            book_scope_evidence=book_scope_evidence,
            scope_evidence=scope_evidence,
            generated_by=generated_by,
            correlation_id=correlation_id,
        )

    governance_evidence = _governance_evidence(
        policy=policy,
        as_of_date=as_of_date,
        generated_by=generated_by,
    )
    signals = [
        *_signals_from_evidence(evidence_items),
        *_signals_from_outcome_reviews(outcome_reviews),
    ]
    _validate_lookback_window(policy=policy, signals=signals)
    results = [_indicator_result(weight, signals) for weight in policy.weights]
    if any(result.state == "BLOCKED" for result in results):
        score = None
        state: PmQualityState = "BLOCKED"
        reason_codes = sorted(
            {reason for result in results for reason in result.reason_codes}
            | {"PM_QUALITY_REQUIRED_EVIDENCE_MISSING"}
        )
    else:
        score = _weighted_score(results)
        state = _score_state(score=score, policy=policy, results=results)
        reason_codes = _score_reason_codes(state=state, results=results)

    return _score_run(
        pm_id=pm_id,
        book_id=book_id,
        as_of_date=as_of_date,
        policy=policy,
        state=state,
        score=score,
        indicator_results=results,
        book_scope_evidence=book_scope_evidence,
        scope_evidence=scope_evidence,
        governance_evidence=governance_evidence,
        reason_codes=reason_codes,
        generated_at=generated_at,
        generated_by=generated_by,
        correlation_id=correlation_id,
    )


def build_pm_operating_quality_fairness_analysis(
    *,
    policy_id: str,
    policy_version: str,
    as_of_date: str,
    segments: list[DpmPmQualityFairnessSegmentInput],
    minimum_segment_score_run_count: int,
    maximum_average_score_spread: Decimal,
    generated_by: str,
    correlation_id: str,
) -> DpmPmQualityFairnessAnalysis:
    """Build bounded cross-segment fairness posture from persisted PM-quality score runs."""

    _validate_fairness_analysis_inputs(
        segments=segments,
        minimum_segment_score_run_count=minimum_segment_score_run_count,
        maximum_average_score_spread=maximum_average_score_spread,
    )
    generated_at = datetime.now(timezone.utc)
    segment_results = [
        _fairness_segment_result(
            policy_id=policy_id,
            policy_version=policy_version,
            as_of_date=as_of_date,
            segment=segment,
            minimum_segment_score_run_count=minimum_segment_score_run_count,
        )
        for segment in segments
    ]
    posture = _fairness_analysis_posture(
        segment_results=segment_results,
        maximum_average_score_spread=maximum_average_score_spread,
    )

    return _fairness_analysis(
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=as_of_date,
        state=posture.state,
        segment_results=segment_results,
        minimum_segment_score_run_count=minimum_segment_score_run_count,
        maximum_average_score_spread=maximum_average_score_spread,
        observed_average_score_spread=posture.observed_spread,
        reason_codes=posture.reason_codes,
        generated_at=generated_at,
        generated_by=generated_by,
        correlation_id=correlation_id,
    )


def _validate_fairness_analysis_inputs(
    *,
    segments: list[DpmPmQualityFairnessSegmentInput],
    minimum_segment_score_run_count: int,
    maximum_average_score_spread: Decimal,
) -> None:
    if len(segments) < 2:
        raise DpmPmQualityValidationError("PM_QUALITY_FAIRNESS_SEGMENTS_REQUIRED")
    if minimum_segment_score_run_count < 1:
        raise DpmPmQualityValidationError("PM_QUALITY_FAIRNESS_MINIMUM_COUNT_INVALID")
    if maximum_average_score_spread < 0 or maximum_average_score_spread > 100:
        raise DpmPmQualityValidationError("PM_QUALITY_FAIRNESS_SPREAD_THRESHOLD_INVALID")


def _fairness_analysis_posture(
    *,
    segment_results: list[DpmPmQualityFairnessSegmentResult],
    maximum_average_score_spread: Decimal,
) -> _FairnessPosture:
    blocked_results = [result for result in segment_results if result.state == "BLOCKED"]
    if blocked_results:
        return _blocked_fairness_posture(blocked_results)

    ready_averages = _ready_segment_average_scores(segment_results)
    if len(ready_averages) < 2:
        return _FairnessPosture(
            state="BLOCKED",
            observed_spread=None,
            reason_codes=["PM_QUALITY_FAIRNESS_COMPARABLE_SEGMENTS_REQUIRED"],
        )

    observed_spread = _observed_average_score_spread(ready_averages)
    if observed_spread > maximum_average_score_spread:
        return _FairnessPosture(
            state="PENDING_REVIEW",
            observed_spread=observed_spread,
            reason_codes=["PM_QUALITY_FAIRNESS_SPREAD_REVIEW_REQUIRED"],
        )
    return _FairnessPosture(
        state="READY",
        observed_spread=observed_spread,
        reason_codes=["PM_QUALITY_FAIRNESS_WITHIN_GOVERNED_SPREAD"],
    )


def _blocked_fairness_posture(
    blocked_results: list[DpmPmQualityFairnessSegmentResult],
) -> _FairnessPosture:
    return _FairnessPosture(
        state="BLOCKED",
        observed_spread=None,
        reason_codes=sorted(
            {reason for result in blocked_results for reason in result.reason_codes}
            | {"PM_QUALITY_FAIRNESS_SEGMENT_BLOCKED"}
        ),
    )


def _ready_segment_average_scores(
    segment_results: list[DpmPmQualityFairnessSegmentResult],
) -> list[Decimal]:
    return [
        result.average_score
        for result in segment_results
        if result.state == "READY" and result.average_score is not None
    ]


def _observed_average_score_spread(ready_averages: list[Decimal]) -> Decimal:
    return (max(ready_averages) - min(ready_averages)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _disabled_score_run(
    *,
    pm_id: str,
    book_id: str | None,
    as_of_date: str,
    policy: DpmPmOperatingQualityPolicy,
    generated_at: datetime,
    book_scope_evidence: DpmPmQualityBookScopeEvidence | None,
    scope_evidence: DpmPmQualityScopeEvidence | None,
    generated_by: str,
    correlation_id: str,
) -> DpmPmOperatingQualityScoreRun:
    return _score_run(
        pm_id=pm_id,
        book_id=book_id,
        as_of_date=as_of_date,
        policy=policy,
        state="DISABLED",
        score=None,
        indicator_results=[],
        book_scope_evidence=book_scope_evidence,
        scope_evidence=scope_evidence,
        governance_evidence=None,
        reason_codes=["PM_QUALITY_POLICY_DISABLED"],
        generated_at=generated_at,
        generated_by=generated_by,
        correlation_id=correlation_id,
    )


def _signals_from_evidence(
    evidence_items: list[DpmPmQualityEvidenceItem],
) -> list[_PmQualitySignal]:
    signals: list[_PmQualitySignal] = []
    for item in evidence_items:
        source_refs = item.source_refs or [
            DpmOutcomeSourceRef(
                source_system=item.source_system,
                source_type=item.source_type,
                source_id=item.source_id,
            )
        ]
        signals.append(
            _PmQualitySignal(
                indicator=item.indicator,
                score=item.score if item.score is not None else _state_score(item.evidence_state),
                state=item.evidence_state,
                reason_codes=item.reason_codes or [f"{item.indicator}_SOURCE_SIGNAL"],
                source_refs=source_refs,
                as_of_date=_signal_as_of_date(source_refs),
            )
        )
    return signals


def _signals_from_outcome_reviews(
    outcome_reviews: list[DpmPostTradeOutcomeReview],
) -> list[_PmQualitySignal]:
    signals: list[_PmQualitySignal] = []
    for review in outcome_reviews:
        review_ref = DpmOutcomeSourceRef(
            source_system="lotus-manage",
            source_type="PostTradeOutcomeReview",
            source_id=review.outcome_review_id,
            source_version=review.outcome_review_version,
            content_hash=review.content_hash,
        )
        dimension_scores = [_state_score(result.state) for result in review.dimension_results]
        if dimension_scores:
            signals.append(
                _PmQualitySignal(
                    indicator="OUTCOME_DISCIPLINE",
                    score=_mean(dimension_scores),
                    state=review.state,
                    reason_codes=sorted(
                        {result.reason_code for result in review.dimension_results}
                    ),
                    source_refs=[review_ref],
                    as_of_date=review.review_window.as_of_date,
                )
            )
        signals.append(
            _PmQualitySignal(
                indicator="SOURCE_QUALITY",
                score=_state_score(review.supportability.state),
                state=review.supportability.state,
                reason_codes=review.supportability.reason_codes
                or ["OUTCOME_REVIEW_SOURCE_POSTURE"],
                source_refs=[review_ref, *review.source_lineage],
                as_of_date=review.review_window.as_of_date,
            )
        )
        if review.report_input_ref or review.ai_evidence_ref:
            refs = [
                ref for ref in [review.report_input_ref, review.ai_evidence_ref] if ref is not None
            ]
            signals.append(
                _PmQualitySignal(
                    indicator="EVIDENCE_COMPLETENESS",
                    score=Decimal("100"),
                    state="READY",
                    reason_codes=["OUTCOME_REVIEW_HANDOFF_EVIDENCE_AVAILABLE"],
                    source_refs=[review_ref, *refs],
                    as_of_date=review.review_window.as_of_date,
                )
            )
    return signals


def _validate_lookback_window(
    *,
    policy: DpmPmOperatingQualityPolicy,
    signals: list[_PmQualitySignal],
) -> None:
    window_dates = _lookback_window_dates(policy.lookback_window_policy)
    if window_dates is None:
        return
    start_date, end_date = window_dates
    dated_signals = [signal for signal in signals if signal.as_of_date is not None]
    if not dated_signals:
        raise DpmPmQualityValidationError("PM_QUALITY_LOOKBACK_WINDOW_EVIDENCE_DATE_REQUIRED")
    for signal in dated_signals:
        signal_date = _signal_as_of_business_date(signal)
        if not _date_in_inclusive_window(signal_date, start_date, end_date):
            raise DpmPmQualityValidationError("PM_QUALITY_EVIDENCE_OUTSIDE_LOOKBACK_WINDOW")


def _lookback_window_dates(
    lookback: DpmPmQualityLookbackWindowPolicy | None,
) -> tuple[date, date] | None:
    if lookback is None:
        return None
    try:
        return (
            date.fromisoformat(lookback.start_date),
            date.fromisoformat(lookback.end_date),
        )
    except ValueError as exc:
        raise DpmPmQualityValidationError("PM_QUALITY_LOOKBACK_WINDOW_DATE_INVALID") from exc


def _signal_as_of_business_date(signal: _PmQualitySignal) -> date:
    try:
        return date.fromisoformat(str(signal.as_of_date))
    except ValueError as exc:
        raise DpmPmQualityValidationError("PM_QUALITY_EVIDENCE_AS_OF_DATE_INVALID") from exc


def _date_in_inclusive_window(
    observed_date: date,
    start_date: date,
    end_date: date,
) -> bool:
    return start_date <= observed_date <= end_date


def _signal_as_of_date(source_refs: list[DpmOutcomeSourceRef]) -> str | None:
    for ref in source_refs:
        if ref.source_version:
            try:
                return date.fromisoformat(ref.source_version).isoformat()
            except ValueError:
                continue
    return None


def _scope_evidence_from_policy(
    policy: DpmPmOperatingQualityPolicy,
) -> DpmPmQualityScopeEvidence | None:
    peer_group = policy.peer_group_policy
    lookback = policy.lookback_window_policy
    if peer_group is None and lookback is None:
        return None
    peer_group_fields = _peer_group_scope_fields(peer_group)
    lookback_fields = _lookback_scope_fields(lookback)
    return DpmPmQualityScopeEvidence(
        peer_group_id=peer_group_fields.peer_group_id,
        peer_group_display_name=peer_group_fields.display_name,
        peer_group_segment_type=peer_group_fields.segment_type,
        minimum_peer_count=peer_group_fields.minimum_peer_count,
        lookback_window_id=lookback_fields.window_id,
        lookback_start_date=lookback_fields.start_date,
        lookback_end_date=lookback_fields.end_date,
        timezone=lookback_fields.timezone,
        reason_codes=_scope_reason_codes(peer_group=peer_group, lookback=lookback),
        source_refs=_scope_source_refs(peer_group=peer_group, lookback=lookback),
    )


def _peer_group_scope_fields(
    peer_group: DpmPmQualityPeerGroupPolicy | None,
) -> _PeerGroupScopeFields:
    if peer_group is None:
        return _PeerGroupScopeFields(
            peer_group_id=None,
            display_name=None,
            segment_type=None,
            minimum_peer_count=None,
        )
    return _PeerGroupScopeFields(
        peer_group_id=peer_group.peer_group_id,
        display_name=peer_group.display_name,
        segment_type=peer_group.segment_type,
        minimum_peer_count=peer_group.minimum_peer_count,
    )


def _lookback_scope_fields(
    lookback: DpmPmQualityLookbackWindowPolicy | None,
) -> _LookbackScopeFields:
    if lookback is None:
        return _LookbackScopeFields(
            window_id=None,
            start_date=None,
            end_date=None,
            timezone=None,
        )
    return _LookbackScopeFields(
        window_id=lookback.window_id,
        start_date=lookback.start_date,
        end_date=lookback.end_date,
        timezone=lookback.timezone,
    )


def _scope_reason_codes(
    *,
    peer_group: DpmPmQualityPeerGroupPolicy | None,
    lookback: DpmPmQualityLookbackWindowPolicy | None,
) -> list[str]:
    reason_codes: list[str] = []
    if peer_group is not None:
        reason_codes.append("PM_QUALITY_PEER_GROUP_MATERIALIZED")
    if lookback is not None:
        reason_codes.append("PM_QUALITY_LOOKBACK_WINDOW_MATERIALIZED")
    return reason_codes


def _scope_source_refs(
    *,
    peer_group: DpmPmQualityPeerGroupPolicy | None,
    lookback: DpmPmQualityLookbackWindowPolicy | None,
) -> list[DpmOutcomeSourceRef]:
    source_refs: list[DpmOutcomeSourceRef] = []
    if peer_group is not None:
        source_refs.extend(peer_group.source_refs)
    if lookback is not None:
        source_refs.extend(lookback.source_refs)
    return source_refs


def _indicator_result(
    weight: DpmPmQualityWeight,
    signals: list[_PmQualitySignal],
) -> DpmPmQualityIndicatorResult:
    indicator_signals = [signal for signal in signals if signal.indicator == weight.indicator]
    if len(indicator_signals) < weight.minimum_evidence_count:
        return DpmPmQualityIndicatorResult(
            indicator=weight.indicator,
            score=None,
            weight=weight.weight,
            state="BLOCKED",
            evidence_count=len(indicator_signals),
            reason_codes=[f"{weight.indicator}_REQUIRED_EVIDENCE_MISSING"],
            source_refs=[],
        )

    scores = [signal.score for signal in indicator_signals]
    score = _mean(scores)
    states = [signal.state for signal in indicator_signals]
    state = _worst_state(states)
    reason_codes = sorted(
        {reason for signal in indicator_signals for reason in signal.reason_codes}
    )
    refs = _dedupe_refs([ref for signal in indicator_signals for ref in signal.source_refs])
    return DpmPmQualityIndicatorResult(
        indicator=weight.indicator,
        score=score,
        weight=weight.weight,
        state=state,
        evidence_count=len(indicator_signals),
        reason_codes=reason_codes or [f"{weight.indicator}_EVALUATED"],
        source_refs=refs,
    )


def _weighted_score(results: list[DpmPmQualityIndicatorResult]) -> Decimal:
    scorable = [result for result in results if result.score is not None]
    total_weight = sum((result.weight for result in scorable), Decimal("0"))
    if total_weight <= 0:
        raise DpmPmQualityValidationError("PM_QUALITY_NO_SCORABLE_INDICATORS")
    weighted = sum((result.score or Decimal("0")) * result.weight for result in scorable)
    return (weighted / total_weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _score_state(
    *,
    score: Decimal,
    policy: DpmPmOperatingQualityPolicy,
    results: list[DpmPmQualityIndicatorResult],
) -> PmQualityState:
    if any(result.state == "BREACHED" for result in results):
        return "BREACHED"
    if any(result.state == "DEGRADED" for result in results):
        return "DEGRADED"
    if score >= policy.ready_threshold:
        return "READY"
    if score >= policy.watch_threshold:
        return "PENDING_REVIEW"
    return "BREACHED"


def _score_reason_codes(
    *,
    state: PmQualityState,
    results: list[DpmPmQualityIndicatorResult],
) -> list[str]:
    base = {
        "READY": "PM_QUALITY_WITHIN_POLICY",
        "PENDING_REVIEW": "PM_QUALITY_REQUIRES_REVIEW",
        "DEGRADED": "PM_QUALITY_DEGRADED_SOURCE_POSTURE",
        "BREACHED": "PM_QUALITY_BELOW_POLICY_THRESHOLD",
        "BLOCKED": "PM_QUALITY_REQUIRED_EVIDENCE_MISSING",
        "DISABLED": "PM_QUALITY_POLICY_DISABLED",
    }[state]
    reasons = {base}
    for result in results:
        if result.state != "READY":
            reasons.update(result.reason_codes)
    return sorted(reasons)


def _fairness_segment_result(
    *,
    policy_id: str,
    policy_version: str,
    as_of_date: str,
    segment: DpmPmQualityFairnessSegmentInput,
    minimum_segment_score_run_count: int,
) -> DpmPmQualityFairnessSegmentResult:
    refs = [
        DpmOutcomeSourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualityScoreRun",
            source_id=score_run.score_run_id,
            source_version=score_run.product_version,
            content_hash=score_run.content_hash,
        )
        for score_run in segment.score_runs
    ]
    mismatch_reasons = _score_run_scope_mismatch_reasons(
        score_runs=segment.score_runs,
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=as_of_date,
    )
    scorable_scores = [
        score_run.score
        for score_run in segment.score_runs
        if score_run.score is not None
        and score_run.state in {"READY", "PENDING_REVIEW", "DEGRADED", "BREACHED"}
    ]
    if mismatch_reasons:
        return DpmPmQualityFairnessSegmentResult(
            segment_id=segment.segment_id,
            segment_type=segment.segment_type,
            display_name=segment.display_name,
            state="BLOCKED",
            score_run_count=len(segment.score_runs),
            average_score=None,
            minimum_score=None,
            maximum_score=None,
            reason_codes=mismatch_reasons,
            score_run_refs=refs,
            source_refs=segment.source_refs,
        )
    if len(scorable_scores) < minimum_segment_score_run_count:
        return DpmPmQualityFairnessSegmentResult(
            segment_id=segment.segment_id,
            segment_type=segment.segment_type,
            display_name=segment.display_name,
            state="BLOCKED",
            score_run_count=len(segment.score_runs),
            average_score=None,
            minimum_score=None,
            maximum_score=None,
            reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_MINIMUM_COUNT_NOT_MET"],
            score_run_refs=refs,
            source_refs=segment.source_refs,
        )

    return DpmPmQualityFairnessSegmentResult(
        segment_id=segment.segment_id,
        segment_type=segment.segment_type,
        display_name=segment.display_name,
        state="READY",
        score_run_count=len(scorable_scores),
        average_score=_mean(scorable_scores),
        minimum_score=min(scorable_scores),
        maximum_score=max(scorable_scores),
        reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_EVALUATED"],
        score_run_refs=refs,
        source_refs=segment.source_refs,
    )


def _score_run_scope_mismatch_reasons(
    *,
    score_runs: list[DpmPmOperatingQualityScoreRun],
    policy_id: str,
    policy_version: str,
    as_of_date: str,
) -> list[str]:
    reasons: set[str] = set()
    for score_run in score_runs:
        if _score_run_policy_mismatched(
            score_run=score_run,
            policy_id=policy_id,
            policy_version=policy_version,
        ):
            reasons.add("PM_QUALITY_FAIRNESS_POLICY_MISMATCH")
        if _score_run_as_of_date_mismatched(score_run=score_run, as_of_date=as_of_date):
            reasons.add("PM_QUALITY_FAIRNESS_AS_OF_DATE_MISMATCH")
        if _score_run_not_scorable(score_run):
            reasons.add("PM_QUALITY_FAIRNESS_SCORE_RUN_NOT_SCORABLE")
    return sorted(reasons)


def _score_run_policy_mismatched(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    policy_id: str,
    policy_version: str,
) -> bool:
    return score_run.policy_id != policy_id or score_run.policy_version != policy_version


def _score_run_as_of_date_mismatched(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    as_of_date: str,
) -> bool:
    return score_run.as_of_date != as_of_date


def _score_run_not_scorable(score_run: DpmPmOperatingQualityScoreRun) -> bool:
    return score_run.state in {"DISABLED", "BLOCKED"} or score_run.score is None


def _score_run(
    *,
    pm_id: str,
    book_id: str | None,
    as_of_date: str,
    policy: DpmPmOperatingQualityPolicy,
    state: PmQualityState,
    score: Decimal | None,
    indicator_results: list[DpmPmQualityIndicatorResult],
    book_scope_evidence: DpmPmQualityBookScopeEvidence | None,
    scope_evidence: DpmPmQualityScopeEvidence | None,
    governance_evidence: DpmPmQualityGovernanceEvidence | None,
    reason_codes: list[str],
    generated_at: datetime,
    generated_by: str,
    correlation_id: str,
) -> DpmPmOperatingQualityScoreRun:
    source_refs = _score_run_source_refs(
        indicator_results=indicator_results,
        book_scope_evidence=book_scope_evidence,
        scope_evidence=scope_evidence,
        governance_evidence=governance_evidence,
    )
    hash_payload = _score_run_hash_payload(
        pm_id=pm_id,
        book_id=book_id,
        as_of_date=as_of_date,
        policy=policy,
        state=state,
        score=score,
        indicator_results=indicator_results,
        book_scope_evidence=book_scope_evidence,
        scope_evidence=scope_evidence,
        governance_evidence=governance_evidence,
        reason_codes=reason_codes,
        source_refs=source_refs,
    )
    content_hash = _content_hash(hash_payload)
    return DpmPmOperatingQualityScoreRun(
        score_run_id=f"pmq_{uuid5(NAMESPACE_URL, content_hash).hex[:16]}",
        pm_id=pm_id,
        book_id=book_id,
        as_of_date=as_of_date,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        state=state,
        score=score,
        indicator_results=indicator_results,
        book_scope_evidence=book_scope_evidence,
        governance_evidence=governance_evidence,
        scope_evidence=scope_evidence,
        reason_codes=reason_codes,
        source_refs=source_refs,
        content_hash=content_hash,
        generated_at=generated_at,
        generated_by=generated_by,
        correlation_id=correlation_id,
    )


def _score_run_source_refs(
    *,
    indicator_results: list[DpmPmQualityIndicatorResult],
    book_scope_evidence: DpmPmQualityBookScopeEvidence | None,
    scope_evidence: DpmPmQualityScopeEvidence | None,
    governance_evidence: DpmPmQualityGovernanceEvidence | None,
) -> list[DpmOutcomeSourceRef]:
    scope_refs = book_scope_evidence.source_refs if book_scope_evidence is not None else []
    pm_scope_refs = scope_evidence.source_refs if scope_evidence is not None else []
    governance_refs = governance_evidence.source_refs if governance_evidence is not None else []
    return _dedupe_refs(
        [ref for result in indicator_results for ref in result.source_refs]
        + scope_refs
        + pm_scope_refs
        + governance_refs
    )


def _score_run_hash_payload(
    *,
    pm_id: str,
    book_id: str | None,
    as_of_date: str,
    policy: DpmPmOperatingQualityPolicy,
    state: PmQualityState,
    score: Decimal | None,
    indicator_results: list[DpmPmQualityIndicatorResult],
    book_scope_evidence: DpmPmQualityBookScopeEvidence | None,
    scope_evidence: DpmPmQualityScopeEvidence | None,
    governance_evidence: DpmPmQualityGovernanceEvidence | None,
    reason_codes: list[str],
    source_refs: list[DpmOutcomeSourceRef],
) -> dict[str, Any]:
    return {
        "pm_id": pm_id,
        "book_id": book_id,
        "as_of_date": as_of_date,
        "policy": policy.model_dump(mode="json"),
        "state": state,
        "score": str(score) if score is not None else None,
        "indicator_results": [result.model_dump(mode="json") for result in indicator_results],
        "book_scope_evidence": _optional_model_dump(book_scope_evidence),
        "scope_evidence": _optional_model_dump(scope_evidence),
        "governance_evidence": _optional_model_dump(governance_evidence),
        "reason_codes": reason_codes,
        "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
    }


def _optional_model_dump(model: Any | None) -> dict[str, Any] | None:
    return model.model_dump(mode="json") if model is not None else None


def _fairness_analysis(
    *,
    policy_id: str,
    policy_version: str,
    as_of_date: str,
    state: PmQualityState,
    segment_results: list[DpmPmQualityFairnessSegmentResult],
    minimum_segment_score_run_count: int,
    maximum_average_score_spread: Decimal,
    observed_average_score_spread: Decimal | None,
    reason_codes: list[str],
    generated_at: datetime,
    generated_by: str,
    correlation_id: str,
) -> DpmPmQualityFairnessAnalysis:
    source_refs = _dedupe_refs(
        [ref for result in segment_results for ref in result.score_run_refs]
        + [ref for result in segment_results for ref in result.source_refs]
    )
    hash_payload = {
        "policy_id": policy_id,
        "policy_version": policy_version,
        "as_of_date": as_of_date,
        "state": state,
        "segment_results": [result.model_dump(mode="json") for result in segment_results],
        "minimum_segment_score_run_count": minimum_segment_score_run_count,
        "maximum_average_score_spread": str(maximum_average_score_spread),
        "observed_average_score_spread": (
            str(observed_average_score_spread)
            if observed_average_score_spread is not None
            else None
        ),
        "reason_codes": reason_codes,
        "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
    }
    content_hash = _content_hash(hash_payload)
    return DpmPmQualityFairnessAnalysis(
        fairness_analysis_id=f"pmq_fair_{uuid5(NAMESPACE_URL, content_hash).hex[:16]}",
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=as_of_date,
        state=state,
        segment_results=segment_results,
        minimum_segment_score_run_count=minimum_segment_score_run_count,
        maximum_average_score_spread=maximum_average_score_spread,
        observed_average_score_spread=observed_average_score_spread,
        reason_codes=reason_codes,
        source_refs=source_refs,
        content_hash=content_hash,
        generated_at=generated_at,
        generated_by=generated_by,
        correlation_id=correlation_id,
    )


def _governance_evidence(
    *,
    policy: DpmPmOperatingQualityPolicy,
    as_of_date: str,
    generated_by: str,
) -> DpmPmQualityGovernanceEvidence:
    governance = policy.governance_approval
    if governance is None:
        raise DpmPmQualityValidationError("PM_QUALITY_GOVERNANCE_APPROVAL_REQUIRED")

    reason_codes = ["PM_QUALITY_GOVERNANCE_APPROVED", "PM_QUALITY_FAIRNESS_REVIEWED"]
    expiry = _governance_expiry_evaluation(
        expires_on=governance.expires_on,
        as_of_date=as_of_date,
    )
    entitlement = _actor_entitlement_evaluation(
        entitled_actor_ids=governance.entitled_actor_ids,
        generated_by=generated_by,
    )
    reason_codes.extend(expiry.reason_codes)
    reason_codes.extend(entitlement.reason_codes)

    return DpmPmQualityGovernanceEvidence(
        approval_ref=governance.approval_ref,
        approved_by=governance.approved_by,
        approved_at=governance.approved_at,
        fairness_review_ref=governance.fairness_review_ref,
        fairness_reviewed_by=governance.fairness_reviewed_by,
        fairness_reviewed_at=governance.fairness_reviewed_at,
        expires_on=expiry.expires_on,
        actor_entitlement_state=entitlement.state,
        reason_codes=reason_codes,
        source_refs=governance.source_refs,
    )


def _governance_expiry_evaluation(
    *,
    expires_on: str | None,
    as_of_date: str,
) -> _GovernanceExpiryEvaluation:
    if expires_on is None:
        return _GovernanceExpiryEvaluation(expires_on=None, reason_codes=[])
    try:
        expiry_date = date.fromisoformat(expires_on)
        run_as_of = date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise DpmPmQualityValidationError("PM_QUALITY_GOVERNANCE_EXPIRY_DATE_INVALID") from exc
    if expiry_date < run_as_of:
        raise DpmPmQualityValidationError("PM_QUALITY_GOVERNANCE_EXPIRED")
    return _GovernanceExpiryEvaluation(
        expires_on=expires_on,
        reason_codes=["PM_QUALITY_GOVERNANCE_ACTIVE"],
    )


def _actor_entitlement_evaluation(
    *,
    entitled_actor_ids: list[str],
    generated_by: str,
) -> _ActorEntitlementEvaluation:
    entitled = {actor_id.strip() for actor_id in entitled_actor_ids if actor_id.strip()}
    if not entitled:
        return _ActorEntitlementEvaluation(state="NOT_SUPPLIED", reason_codes=[])
    if generated_by not in entitled:
        raise DpmPmQualityValidationError("PM_QUALITY_ACTOR_NOT_ENTITLED")
    return _ActorEntitlementEvaluation(
        state="AUTHORIZED",
        reason_codes=["PM_QUALITY_ACTOR_AUTHORIZED"],
    )


def _state_score(state: str) -> Decimal:
    return {
        "READY": Decimal("100"),
        "PENDING_REVIEW": Decimal("70"),
        "DEGRADED": Decimal("60"),
        "BREACHED": Decimal("35"),
        "BLOCKED": Decimal("0"),
        "NOT_SUPPORTED": Decimal("50"),
        "DISABLED": Decimal("0"),
    }.get(state, Decimal("0"))


def _worst_state(states: list[str]) -> PmQualityState:
    worst = max(states, key=lambda state: _PM_QUALITY_STATE_RANK.get(state, 0))
    return _NORMALIZED_WORST_STATE.get(worst, "DEGRADED")


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return (sum(values, Decimal("0")) / Decimal(len(values))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _dedupe_refs(refs: list[DpmOutcomeSourceRef]) -> list[DpmOutcomeSourceRef]:
    by_key: dict[tuple[str, str, str], DpmOutcomeSourceRef] = {}
    for ref in refs:
        by_key[(ref.source_system, ref.source_type, ref.source_id)] = ref
    return [by_key[key] for key in sorted(by_key)]


def _content_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
