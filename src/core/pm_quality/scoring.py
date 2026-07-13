"""Pure scoring engine for configurable PM operating quality."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal
from uuid import uuid5, NAMESPACE_URL

from src.core.outcomes import DpmOutcomeSourceRef, DpmPostTradeOutcomeReview
from src.core.pm_quality.fairness_analysis import (
    DpmPmQualityFairnessSegmentInput as DpmPmQualityFairnessSegmentInput,
    build_pm_operating_quality_fairness_analysis as build_pm_operating_quality_fairness_analysis,
)
from src.core.pm_quality.models import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
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
from src.core.pm_quality.scoring_common import (
    DpmPmQualityValidationError as DpmPmQualityValidationError,
    _content_hash,
    _dedupe_refs,
    _mean,
    _optional_model_dump,
)


@dataclass(frozen=True)
class _PmQualitySignal:
    indicator: str
    score: Decimal
    state: str
    reason_codes: list[str]
    source_refs: list[DpmOutcomeSourceRef]
    as_of_date: str | None = None


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
class _GovernanceExpiryEvaluation:
    expires_on: str | None
    reason_codes: list[str]


@dataclass(frozen=True)
class _ActorEntitlementEvaluation:
    state: Literal["AUTHORIZED", "NOT_SUPPLIED"]
    reason_codes: list[str]


@dataclass(frozen=True)
class _ScoreRunEvaluation:
    state: PmQualityState
    score: Decimal | None
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
    evaluation = _score_run_evaluation(policy=policy, results=results)

    return _score_run(
        pm_id=pm_id,
        book_id=book_id,
        as_of_date=as_of_date,
        policy=policy,
        state=evaluation.state,
        score=evaluation.score,
        indicator_results=results,
        book_scope_evidence=book_scope_evidence,
        scope_evidence=scope_evidence,
        governance_evidence=governance_evidence,
        reason_codes=evaluation.reason_codes,
        generated_at=generated_at,
        generated_by=generated_by,
        correlation_id=correlation_id,
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
        review_ref = _outcome_review_ref(review)
        outcome_signal = _outcome_discipline_signal(review=review, review_ref=review_ref)
        if outcome_signal is not None:
            signals.append(outcome_signal)
        signals.append(_outcome_source_quality_signal(review=review, review_ref=review_ref))
        handoff_signal = _outcome_handoff_evidence_signal(review=review, review_ref=review_ref)
        if handoff_signal is not None:
            signals.append(handoff_signal)
    return signals


def _outcome_review_ref(review: DpmPostTradeOutcomeReview) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type="PostTradeOutcomeReview",
        source_id=review.outcome_review_id,
        source_version=review.outcome_review_version,
        content_hash=review.content_hash,
    )


def _outcome_discipline_signal(
    *,
    review: DpmPostTradeOutcomeReview,
    review_ref: DpmOutcomeSourceRef,
) -> _PmQualitySignal | None:
    dimension_scores = [_state_score(result.state) for result in review.dimension_results]
    if not dimension_scores:
        return None
    return _PmQualitySignal(
        indicator="OUTCOME_DISCIPLINE",
        score=_mean(dimension_scores),
        state=review.state,
        reason_codes=sorted({result.reason_code for result in review.dimension_results}),
        source_refs=[review_ref],
        as_of_date=review.review_window.as_of_date,
    )


def _outcome_source_quality_signal(
    *,
    review: DpmPostTradeOutcomeReview,
    review_ref: DpmOutcomeSourceRef,
) -> _PmQualitySignal:
    return _PmQualitySignal(
        indicator="SOURCE_QUALITY",
        score=_state_score(review.supportability.state),
        state=review.supportability.state,
        reason_codes=review.supportability.reason_codes or ["OUTCOME_REVIEW_SOURCE_POSTURE"],
        source_refs=[review_ref, *review.source_lineage],
        as_of_date=review.review_window.as_of_date,
    )


def _outcome_handoff_evidence_signal(
    *,
    review: DpmPostTradeOutcomeReview,
    review_ref: DpmOutcomeSourceRef,
) -> _PmQualitySignal | None:
    refs = _outcome_handoff_refs(review)
    if not refs:
        return None
    return _PmQualitySignal(
        indicator="EVIDENCE_COMPLETENESS",
        score=Decimal("100"),
        state="READY",
        reason_codes=["OUTCOME_REVIEW_HANDOFF_EVIDENCE_AVAILABLE"],
        source_refs=[review_ref, *refs],
        as_of_date=review.review_window.as_of_date,
    )


def _outcome_handoff_refs(
    review: DpmPostTradeOutcomeReview,
) -> list[DpmOutcomeSourceRef]:
    return [ref for ref in [review.report_input_ref, review.ai_evidence_ref] if ref is not None]


def _validate_lookback_window(
    *,
    policy: DpmPmOperatingQualityPolicy,
    signals: list[_PmQualitySignal],
) -> None:
    window_dates = _lookback_window_dates(policy.lookback_window_policy)
    if window_dates is None:
        return
    start_date, end_date = window_dates
    if not signals:
        raise DpmPmQualityValidationError("PM_QUALITY_LOOKBACK_WINDOW_EVIDENCE_DATE_REQUIRED")
    for signal in signals:
        if signal.as_of_date is None:
            raise DpmPmQualityValidationError("PM_QUALITY_LOOKBACK_WINDOW_EVIDENCE_DATE_REQUIRED")
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
            return ref.source_version
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
    indicator_signals = _indicator_signals(weight=weight, signals=signals)
    if len(indicator_signals) < weight.minimum_evidence_count:
        return _blocked_indicator_result(weight=weight, evidence_count=len(indicator_signals))

    return DpmPmQualityIndicatorResult(
        indicator=weight.indicator,
        score=_mean([signal.score for signal in indicator_signals]),
        weight=weight.weight,
        state=_worst_state([signal.state for signal in indicator_signals]),
        evidence_count=len(indicator_signals),
        reason_codes=_indicator_reason_codes(weight=weight, signals=indicator_signals),
        source_refs=_indicator_source_refs(indicator_signals),
    )


def _indicator_signals(
    *,
    weight: DpmPmQualityWeight,
    signals: list[_PmQualitySignal],
) -> list[_PmQualitySignal]:
    return [signal for signal in signals if signal.indicator == weight.indicator]


def _blocked_indicator_result(
    *,
    weight: DpmPmQualityWeight,
    evidence_count: int,
) -> DpmPmQualityIndicatorResult:
    return DpmPmQualityIndicatorResult(
        indicator=weight.indicator,
        score=None,
        weight=weight.weight,
        state="BLOCKED",
        evidence_count=evidence_count,
        reason_codes=[f"{weight.indicator}_REQUIRED_EVIDENCE_MISSING"],
        source_refs=[],
    )


def _indicator_reason_codes(
    *,
    weight: DpmPmQualityWeight,
    signals: list[_PmQualitySignal],
) -> list[str]:
    reason_codes = sorted({reason for signal in signals for reason in signal.reason_codes})
    return reason_codes or [f"{weight.indicator}_EVALUATED"]


def _indicator_source_refs(
    signals: list[_PmQualitySignal],
) -> list[DpmOutcomeSourceRef]:
    return _dedupe_refs([ref for signal in signals for ref in signal.source_refs])


def _weighted_score(results: list[DpmPmQualityIndicatorResult]) -> Decimal:
    scorable = _scorable_indicator_results(results)
    total_weight = _indicator_total_weight(scorable)
    if total_weight <= 0:
        raise DpmPmQualityValidationError("PM_QUALITY_NO_SCORABLE_INDICATORS")
    return _rounded_weighted_indicator_score(
        weighted_score=_weighted_indicator_score(scorable),
        total_weight=total_weight,
    )


def _scorable_indicator_results(
    results: list[DpmPmQualityIndicatorResult],
) -> list[DpmPmQualityIndicatorResult]:
    return [result for result in results if result.score is not None]


def _indicator_total_weight(results: list[DpmPmQualityIndicatorResult]) -> Decimal:
    return sum((result.weight for result in results), Decimal("0"))


def _weighted_indicator_score(results: list[DpmPmQualityIndicatorResult]) -> Decimal:
    return sum(
        ((result.score or Decimal("0")) * result.weight for result in results),
        Decimal("0"),
    )


def _rounded_weighted_indicator_score(
    *,
    weighted_score: Decimal,
    total_weight: Decimal,
) -> Decimal:
    return (weighted_score / total_weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _score_run_evaluation(
    *,
    policy: DpmPmOperatingQualityPolicy,
    results: list[DpmPmQualityIndicatorResult],
) -> _ScoreRunEvaluation:
    if _score_run_has_blocked_indicator(results):
        return _ScoreRunEvaluation(
            state="BLOCKED",
            score=None,
            reason_codes=_blocked_score_run_reason_codes(results),
        )
    score = _weighted_score(results)
    state = _score_state(score=score, policy=policy, results=results)
    return _ScoreRunEvaluation(
        state=state,
        score=score,
        reason_codes=_score_reason_codes(state=state, results=results),
    )


def _score_run_has_blocked_indicator(
    results: list[DpmPmQualityIndicatorResult],
) -> bool:
    return any(result.state == "BLOCKED" for result in results)


def _blocked_score_run_reason_codes(
    results: list[DpmPmQualityIndicatorResult],
) -> list[str]:
    return sorted(
        {reason for result in results for reason in result.reason_codes}
        | {"PM_QUALITY_REQUIRED_EVIDENCE_MISSING"}
    )


def _score_state(
    *,
    score: Decimal,
    policy: DpmPmOperatingQualityPolicy,
    results: list[DpmPmQualityIndicatorResult],
) -> PmQualityState:
    if _has_indicator_state(results=results, state="BREACHED"):
        return "BREACHED"
    if _has_indicator_state(results=results, state="DEGRADED"):
        return "DEGRADED"
    if score >= policy.ready_threshold:
        return "READY"
    if score >= policy.watch_threshold:
        return "PENDING_REVIEW"
    return "BREACHED"


def _has_indicator_state(
    *,
    results: list[DpmPmQualityIndicatorResult],
    state: PmQualityState,
) -> bool:
    return any(result.state == state for result in results)


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
