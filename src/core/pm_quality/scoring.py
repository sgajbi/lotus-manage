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
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityGovernanceEvidence,
    DpmPmQualityEvidenceItem,
    DpmPmQualityIndicatorResult,
    DpmPmQualityWeight,
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


def build_pm_operating_quality_score_run(
    *,
    pm_id: str,
    book_id: str | None,
    as_of_date: str,
    policy: DpmPmOperatingQualityPolicy,
    evidence_items: list[DpmPmQualityEvidenceItem],
    outcome_reviews: list[DpmPostTradeOutcomeReview],
    book_scope_evidence: DpmPmQualityBookScopeEvidence | None = None,
    generated_by: str,
    correlation_id: str,
) -> DpmPmOperatingQualityScoreRun:
    """Build an explainable PM quality score run from source-backed evidence."""

    if policy.as_of_date != as_of_date:
        raise DpmPmQualityValidationError("PM_QUALITY_POLICY_AS_OF_DATE_MISMATCH")
    generated_at = datetime.now(timezone.utc)
    if not policy.enabled:
        return _disabled_score_run(
            pm_id=pm_id,
            book_id=book_id,
            as_of_date=as_of_date,
            policy=policy,
            generated_at=generated_at,
            book_scope_evidence=book_scope_evidence,
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
        governance_evidence=governance_evidence,
        reason_codes=reason_codes,
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
                )
            )
    return signals


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
    governance_evidence: DpmPmQualityGovernanceEvidence | None,
    reason_codes: list[str],
    generated_at: datetime,
    generated_by: str,
    correlation_id: str,
) -> DpmPmOperatingQualityScoreRun:
    scope_refs = book_scope_evidence.source_refs if book_scope_evidence is not None else []
    governance_refs = governance_evidence.source_refs if governance_evidence is not None else []
    source_refs = _dedupe_refs(
        [ref for result in indicator_results for ref in result.source_refs]
        + scope_refs
        + governance_refs
    )
    hash_payload = {
        "pm_id": pm_id,
        "book_id": book_id,
        "as_of_date": as_of_date,
        "policy": policy.model_dump(mode="json"),
        "state": state,
        "score": str(score) if score is not None else None,
        "indicator_results": [result.model_dump(mode="json") for result in indicator_results],
        "book_scope_evidence": (
            book_scope_evidence.model_dump(mode="json") if book_scope_evidence is not None else None
        ),
        "governance_evidence": (
            governance_evidence.model_dump(mode="json") if governance_evidence is not None else None
        ),
        "reason_codes": reason_codes,
        "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
    }
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
    if governance.expires_on is not None:
        try:
            expires_on = date.fromisoformat(governance.expires_on)
            run_as_of = date.fromisoformat(as_of_date)
        except ValueError as exc:
            raise DpmPmQualityValidationError("PM_QUALITY_GOVERNANCE_EXPIRY_DATE_INVALID") from exc
        if expires_on < run_as_of:
            raise DpmPmQualityValidationError("PM_QUALITY_GOVERNANCE_EXPIRED")
        reason_codes.append("PM_QUALITY_GOVERNANCE_ACTIVE")

    actor_entitlement_state: Literal["AUTHORIZED", "NOT_SUPPLIED"] = "NOT_SUPPLIED"
    entitled_actor_ids = {
        actor_id.strip() for actor_id in governance.entitled_actor_ids if actor_id.strip()
    }
    if entitled_actor_ids:
        if generated_by not in entitled_actor_ids:
            raise DpmPmQualityValidationError("PM_QUALITY_ACTOR_NOT_ENTITLED")
        actor_entitlement_state = "AUTHORIZED"
        reason_codes.append("PM_QUALITY_ACTOR_AUTHORIZED")

    return DpmPmQualityGovernanceEvidence(
        approval_ref=governance.approval_ref,
        approved_by=governance.approved_by,
        approved_at=governance.approved_at,
        fairness_review_ref=governance.fairness_review_ref,
        fairness_reviewed_by=governance.fairness_reviewed_by,
        fairness_reviewed_at=governance.fairness_reviewed_at,
        expires_on=governance.expires_on,
        actor_entitlement_state=actor_entitlement_state,
        reason_codes=reason_codes,
        source_refs=governance.source_refs,
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
    rank = {
        "BLOCKED": 6,
        "BREACHED": 5,
        "DEGRADED": 4,
        "PENDING_REVIEW": 3,
        "READY": 2,
        "DISABLED": 1,
    }
    worst = max(states, key=lambda state: rank.get(state, 0))
    if worst == "BLOCKED":
        return "BLOCKED"
    if worst == "BREACHED":
        return "BREACHED"
    if worst == "DEGRADED" or worst == "NOT_SUPPORTED":
        return "DEGRADED"
    if worst == "PENDING_REVIEW":
        return "PENDING_REVIEW"
    if worst == "READY":
        return "READY"
    if worst == "DISABLED":
        return "DISABLED"
    return "DEGRADED"


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
