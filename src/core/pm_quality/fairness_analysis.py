"""PM operating-quality fairness-analysis construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import NAMESPACE_URL, uuid5

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityFairnessSegmentResult,
    PmQualityFairnessSegmentType,
    PmQualityState,
)
from src.core.pm_quality.scoring_common import (
    DpmPmQualityValidationError,
    _content_hash,
    _dedupe_refs,
    _mean,
    _optional_decimal_as_string,
)


@dataclass(frozen=True)
class DpmPmQualityFairnessSegmentInput:
    """Source-defined segment and its persisted score-run members."""

    segment_id: str
    segment_type: PmQualityFairnessSegmentType
    display_name: str
    score_runs: list[DpmPmOperatingQualityScoreRun]
    source_refs: list[DpmOutcomeSourceRef]


@dataclass(frozen=True)
class _FairnessPosture:
    state: PmQualityState
    observed_spread: Decimal | None
    reason_codes: list[str]


@dataclass(frozen=True)
class _FairnessSegmentEvaluation:
    state: PmQualityState
    score_run_count: int
    average_score: Decimal | None
    minimum_score: Decimal | None
    maximum_score: Decimal | None
    reason_codes: list[str]


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
    blocked_results = _blocked_fairness_segment_results(segment_results)
    if blocked_results:
        return _blocked_fairness_posture(blocked_results)

    ready_averages = _ready_segment_average_scores(segment_results)
    if not _has_comparable_fairness_segments(ready_averages):
        return _blocked_comparable_segments_posture()

    observed_spread = _observed_average_score_spread(ready_averages)
    return _fairness_spread_posture(
        observed_spread=observed_spread,
        maximum_average_score_spread=maximum_average_score_spread,
    )


def _blocked_fairness_segment_results(
    segment_results: list[DpmPmQualityFairnessSegmentResult],
) -> list[DpmPmQualityFairnessSegmentResult]:
    return [result for result in segment_results if result.state == "BLOCKED"]


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


def _has_comparable_fairness_segments(ready_averages: list[Decimal]) -> bool:
    return len(ready_averages) >= 2


def _blocked_comparable_segments_posture() -> _FairnessPosture:
    return _FairnessPosture(
        state="BLOCKED",
        observed_spread=None,
        reason_codes=["PM_QUALITY_FAIRNESS_COMPARABLE_SEGMENTS_REQUIRED"],
    )


def _observed_average_score_spread(ready_averages: list[Decimal]) -> Decimal:
    return (max(ready_averages) - min(ready_averages)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _fairness_spread_posture(
    *,
    observed_spread: Decimal,
    maximum_average_score_spread: Decimal,
) -> _FairnessPosture:
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


def _fairness_segment_result(
    *,
    policy_id: str,
    policy_version: str,
    as_of_date: str,
    segment: DpmPmQualityFairnessSegmentInput,
    minimum_segment_score_run_count: int,
) -> DpmPmQualityFairnessSegmentResult:
    score_run_refs = _fairness_segment_score_run_refs(segment)
    evaluation = _fairness_segment_evaluation(
        score_runs=segment.score_runs,
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=as_of_date,
        minimum_segment_score_run_count=minimum_segment_score_run_count,
    )
    return DpmPmQualityFairnessSegmentResult(
        segment_id=segment.segment_id,
        segment_type=segment.segment_type,
        display_name=segment.display_name,
        state=evaluation.state,
        score_run_count=evaluation.score_run_count,
        average_score=evaluation.average_score,
        minimum_score=evaluation.minimum_score,
        maximum_score=evaluation.maximum_score,
        reason_codes=evaluation.reason_codes,
        score_run_refs=score_run_refs,
        source_refs=segment.source_refs,
    )


def _fairness_segment_score_run_refs(
    segment: DpmPmQualityFairnessSegmentInput,
) -> list[DpmOutcomeSourceRef]:
    return [
        DpmOutcomeSourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualityScoreRun",
            source_id=score_run.score_run_id,
            source_version=score_run.product_version,
            content_hash=score_run.content_hash,
        )
        for score_run in segment.score_runs
    ]


def _fairness_segment_evaluation(
    *,
    score_runs: list[DpmPmOperatingQualityScoreRun],
    policy_id: str,
    policy_version: str,
    as_of_date: str,
    minimum_segment_score_run_count: int,
) -> _FairnessSegmentEvaluation:
    mismatch_reasons = _score_run_scope_mismatch_reasons(
        score_runs=score_runs,
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=as_of_date,
    )
    if mismatch_reasons:
        return _blocked_fairness_segment_evaluation(
            score_run_count=len(score_runs),
            reason_codes=mismatch_reasons,
        )

    scorable_scores = _fairness_segment_scorable_scores(score_runs)
    if len(scorable_scores) < minimum_segment_score_run_count:
        return _blocked_fairness_segment_evaluation(
            score_run_count=len(score_runs),
            reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_MINIMUM_COUNT_NOT_MET"],
        )
    return _ready_fairness_segment_evaluation(scorable_scores)


def _fairness_segment_scorable_scores(
    score_runs: list[DpmPmOperatingQualityScoreRun],
) -> list[Decimal]:
    return [
        score_run.score
        for score_run in score_runs
        if score_run.score is not None
        and score_run.state in {"READY", "PENDING_REVIEW", "DEGRADED", "BREACHED"}
    ]


def _blocked_fairness_segment_evaluation(
    *,
    score_run_count: int,
    reason_codes: list[str],
) -> _FairnessSegmentEvaluation:
    return _FairnessSegmentEvaluation(
        state="BLOCKED",
        score_run_count=score_run_count,
        average_score=None,
        minimum_score=None,
        maximum_score=None,
        reason_codes=reason_codes,
    )


def _ready_fairness_segment_evaluation(
    scorable_scores: list[Decimal],
) -> _FairnessSegmentEvaluation:
    return _FairnessSegmentEvaluation(
        state="READY",
        score_run_count=len(scorable_scores),
        average_score=_mean(scorable_scores),
        minimum_score=min(scorable_scores),
        maximum_score=max(scorable_scores),
        reason_codes=["PM_QUALITY_FAIRNESS_SEGMENT_EVALUATED"],
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
    source_refs = _fairness_analysis_source_refs(segment_results)
    content_hash = _content_hash(
        _fairness_analysis_hash_payload(
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
        )
    )
    return DpmPmQualityFairnessAnalysis(
        fairness_analysis_id=_fairness_analysis_id(content_hash),
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


def _fairness_analysis_source_refs(
    segment_results: list[DpmPmQualityFairnessSegmentResult],
) -> list[DpmOutcomeSourceRef]:
    return _dedupe_refs(
        [ref for result in segment_results for ref in result.score_run_refs]
        + [ref for result in segment_results for ref in result.source_refs]
    )


def _fairness_analysis_hash_payload(
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
    source_refs: list[DpmOutcomeSourceRef],
) -> dict[str, object]:
    return {
        "policy_id": policy_id,
        "policy_version": policy_version,
        "as_of_date": as_of_date,
        "state": state,
        "segment_results": [result.model_dump(mode="json") for result in segment_results],
        "minimum_segment_score_run_count": minimum_segment_score_run_count,
        "maximum_average_score_spread": str(maximum_average_score_spread),
        "observed_average_score_spread": _optional_decimal_as_string(observed_average_score_spread),
        "reason_codes": reason_codes,
        "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
    }


def _fairness_analysis_id(content_hash: str) -> str:
    return f"pmq_fair_{uuid5(NAMESPACE_URL, content_hash).hex[:16]}"
