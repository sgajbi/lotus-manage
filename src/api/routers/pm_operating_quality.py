from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, status
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.api.routers.pm_operating_quality_fairness_routes import router as fairness_router
from src.api.routers.pm_operating_quality_policy_routes import router as policy_router
from src.api.routers.pm_operating_quality_score_run_routes import (
    register_pm_quality_score_run_command_routes,
    register_pm_quality_score_run_read_routes,
)
from src.api.routers.pm_operating_quality_review_action_routes import (
    register_pm_quality_review_action_routes,
)
from src.api.routers.pm_operating_quality_summary_routes import router as summary_router
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityPmBookScopeRequest,
    DpmPmOperatingQualityScorePreviewRequest,
    DpmPmQualityFairnessPreviewRequest,
    DpmPmQualityFairnessSegmentRequest,
    DpmPmQualityReviewActionRequest,
    DpmPmQualitySummaryInvocationRequest,
)
from src.core.outcomes import DpmOutcomeSourceRef
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityEvidenceItem,
    DpmPmQualityPolicyRepository,
    DpmPmQualityReviewAction,
    DpmPmQualityScoreRunRepository,
    DpmPmQualityValidationError,
    build_pm_operating_quality_score_run,
    build_pm_quality_review_action,
)
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError


__all__ = [
    "DpmPmQualityFairnessPreviewRequest",
    "DpmPmQualityFairnessSegmentRequest",
    "DpmPmQualityReviewActionRequest",
    "DpmPmQualitySummaryInvocationRequest",
]


router = APIRouter(
    prefix="/rebalance/pm-operating-quality",
    tags=["lotus-manage PM Operating Quality"],
)


def _build_score_run_for_route(
    request: DpmPmOperatingQualityScorePreviewRequest,
    x_correlation_id: str | None,
    outcome_repository: DpmOutcomeReviewRepository,
    policy_repository: DpmPmQualityPolicyRepository,
) -> DpmPmOperatingQualityScoreRun:
    return _build_score_run(
        request=request,
        x_correlation_id=x_correlation_id,
        outcome_repository=outcome_repository,
        policy_repository=policy_repository,
    )


register_pm_quality_score_run_command_routes(router, _build_score_run_for_route)


router.include_router(fairness_router)


def _build_review_action_for_route(
    request: DpmPmQualityReviewActionRequest,
    x_correlation_id: str | None,
    score_run_repository: DpmPmQualityScoreRunRepository,
    fairness_repository: DpmPmQualityFairnessAnalysisRepository,
) -> DpmPmQualityReviewAction:
    return _build_review_action(
        request=request,
        x_correlation_id=x_correlation_id,
        score_run_repository=score_run_repository,
        fairness_repository=fairness_repository,
    )


register_pm_quality_review_action_routes(router, _build_review_action_for_route)


router.include_router(summary_router)


router.include_router(policy_router)


register_pm_quality_score_run_read_routes(router)


def _build_score_run(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    x_correlation_id: str | None,
    outcome_repository: DpmOutcomeReviewRepository,
    policy_repository: DpmPmQualityPolicyRepository,
) -> DpmPmOperatingQualityScoreRun:
    policy = _resolve_policy(request=request, repository=policy_repository)
    evidence_items = list(request.evidence_items)
    book_scope_evidence = None
    if request.pm_book_scope is not None:
        book_scope_evidence = _resolve_pm_book_scope_evidence(
            request=request,
            scope=request.pm_book_scope,
            correlation_id=x_correlation_id or request.actor_id,
        )
        evidence_items.append(_book_scope_signal(book_scope_evidence))
    outcome_reviews = []
    for outcome_review_id in request.outcome_review_ids:
        review = outcome_repository.get_outcome_review(outcome_review_id=outcome_review_id)
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OUTCOME_REVIEW_NOT_FOUND:{outcome_review_id}",
            )
        outcome_reviews.append(review)
    try:
        score_run = build_pm_operating_quality_score_run(
            pm_id=request.pm_id,
            book_id=request.book_id,
            as_of_date=request.as_of_date,
            policy=policy,
            evidence_items=evidence_items,
            outcome_reviews=outcome_reviews,
            book_scope_evidence=book_scope_evidence,
            generated_by=request.actor_id,
            correlation_id=x_correlation_id or request.actor_id,
        )
    except DpmPmQualityValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return score_run


def _build_review_action(
    *,
    request: DpmPmQualityReviewActionRequest,
    x_correlation_id: str | None,
    score_run_repository: DpmPmQualityScoreRunRepository,
    fairness_repository: DpmPmQualityFairnessAnalysisRepository,
) -> DpmPmQualityReviewAction:
    target: DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis | None
    if request.target_type == "SCORE_RUN":
        target = score_run_repository.get_score_run(score_run_id=request.target_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PM_QUALITY_SCORE_RUN_NOT_FOUND:{request.target_id}",
            )
    else:
        target = fairness_repository.get_fairness_analysis(fairness_analysis_id=request.target_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:{request.target_id}",
            )
    try:
        return build_pm_quality_review_action(
            target=target,
            target_type=request.target_type,
            action_type=request.action_type,
            review_action_ref=request.review_action_ref,
            review_reason=request.review_reason,
            actor_id=request.actor_id,
            source_refs=request.source_refs,
            remediation_due_date=request.remediation_due_date,
            correlation_id=x_correlation_id or request.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def _resolve_pm_book_scope_evidence(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    scope: DpmPmOperatingQualityPmBookScopeRequest,
    correlation_id: str,
) -> DpmPmQualityBookScopeEvidence:
    try:
        as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="INVALID_AS_OF_DATE",
        ) from exc
    try:
        membership = build_core_resolver_client().resolve_portfolio_manager_book_membership(
            portfolio_manager_id=request.pm_id,
            as_of_date=as_of_date,
            tenant_id=scope.tenant_id,
            booking_center_code=scope.booking_center_code,
            portfolio_types=scope.portfolio_types,
            include_inactive=scope.include_inactive,
            correlation_id=correlation_id,
        )
    except DpmCoreResolverUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE"},
        ) from exc
    except DpmCoreResolverError as exc:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE"},
        ) from exc

    if membership.supportability.state != "READY":
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": membership.supportability.reason,
                "message": "PM-book membership is not source-ready for PM operating quality.",
            },
        )
    if not membership.members:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
                "message": "PM-book membership returned no portfolios for PM operating quality.",
            },
        )

    source_id = (
        membership.snapshot_id
        or membership.source_batch_fingerprint
        or f"pm_book:{membership.portfolio_manager_id}:{membership.as_of_date.isoformat()}"
    )
    book_ref = DpmOutcomeSourceRef(
        source_system="lotus-core",
        source_type="PortfolioManagerBookMembership",
        source_id=source_id,
        source_version=membership.product_version,
        content_hash=membership.source_batch_fingerprint,
    )
    member_refs = [
        DpmOutcomeSourceRef(
            source_system="lotus-core",
            source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
            source_id=member.source_record_id or member.portfolio_id,
            source_version=membership.as_of_date.isoformat(),
        )
        for member in membership.members[:100]
    ]
    return DpmPmQualityBookScopeEvidence(
        source_id=source_id,
        product_version=membership.product_version,
        supportability_state=membership.supportability.state,
        returned_portfolio_count=len(membership.members),
        member_portfolio_ids=[member.portfolio_id for member in membership.members[:100]],
        filters_applied=membership.supportability.filters_applied,
        reason_codes=[
            "PM_BOOK_SCOPE_MATERIALIZED",
            membership.supportability.reason,
        ],
        source_refs=[book_ref, *member_refs],
    )


def _book_scope_signal(
    book_scope_evidence: DpmPmQualityBookScopeEvidence,
) -> DpmPmQualityEvidenceItem:
    return DpmPmQualityEvidenceItem(
        indicator="SOURCE_QUALITY",
        evidence_state="READY",
        score=None,
        source_system=book_scope_evidence.source_system,
        source_type=book_scope_evidence.source_type,
        source_id=book_scope_evidence.source_id,
        reason_codes=book_scope_evidence.reason_codes,
        source_refs=book_scope_evidence.source_refs,
    )


def _resolve_policy(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    repository: DpmPmQualityPolicyRepository,
) -> DpmPmOperatingQualityPolicy:
    if request.policy is not None:
        return request.policy
    if request.policy_id is None or request.policy_version is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PM_QUALITY_POLICY_REFERENCE_REQUIRED",
        )
    policy = repository.get_policy(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
    )
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_POLICY_NOT_FOUND:{request.policy_id}:{request.policy_version}",
        )
    return policy
