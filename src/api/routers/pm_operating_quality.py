from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.pm_operating_quality_builders import (
    book_scope_signal,
    build_review_action,
    build_score_run,
    resolve_pm_book_scope_evidence,
    resolve_policy,
)
from src.api.routers.pm_operating_quality_fairness_routes import router as fairness_router
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityPmBookScopeRequest,
    DpmPmOperatingQualityScorePreviewRequest,
    DpmPmQualityFairnessPreviewRequest,
    DpmPmQualityFairnessSegmentRequest,
    DpmPmQualityReviewActionRequest,
    DpmPmQualitySummaryInvocationRequest,
)
from src.api.routers.pm_operating_quality_policy_routes import router as policy_router
from src.api.routers.pm_operating_quality_review_action_routes import (
    register_pm_quality_review_action_routes,
)
from src.api.routers.pm_operating_quality_score_run_routes import (
    register_pm_quality_score_run_command_routes,
    register_pm_quality_score_run_read_routes,
)
from src.api.routers.pm_operating_quality_summary_routes import router as summary_router
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityEvidenceItem,
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityPolicyRepository,
    DpmPmQualityReviewAction,
    DpmPmQualityScoreRunRepository,
    build_pm_quality_review_action,
)


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
    return build_score_run(
        request=request,
        x_correlation_id=x_correlation_id,
        outcome_repository=outcome_repository,
        policy_repository=policy_repository,
        core_resolver_factory=build_core_resolver_client,
    )


def _build_review_action(
    *,
    request: DpmPmQualityReviewActionRequest,
    x_correlation_id: str | None,
    score_run_repository: DpmPmQualityScoreRunRepository,
    fairness_repository: DpmPmQualityFairnessAnalysisRepository,
) -> DpmPmQualityReviewAction:
    return build_review_action(
        request=request,
        x_correlation_id=x_correlation_id,
        score_run_repository=score_run_repository,
        fairness_repository=fairness_repository,
        review_action_builder=build_pm_quality_review_action,
    )


def _resolve_pm_book_scope_evidence(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    scope: DpmPmOperatingQualityPmBookScopeRequest,
    correlation_id: str,
) -> DpmPmQualityBookScopeEvidence:
    return resolve_pm_book_scope_evidence(
        request=request,
        scope=scope,
        correlation_id=correlation_id,
        core_resolver_factory=build_core_resolver_client,
    )


def _book_scope_signal(
    book_scope_evidence: DpmPmQualityBookScopeEvidence,
) -> DpmPmQualityEvidenceItem:
    return book_scope_signal(book_scope_evidence)


def _resolve_policy(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    repository: DpmPmQualityPolicyRepository,
) -> DpmPmOperatingQualityPolicy:
    return resolve_policy(request=request, repository=repository)
