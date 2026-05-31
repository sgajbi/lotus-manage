from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_outcome_review_repository,
    get_pm_quality_policy_repository,
    get_pm_quality_score_run_repository,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewRequest,
    DpmPmOperatingQualityScorePreviewResponse,
)
from src.api.routers.pm_operating_quality_http import pm_quality_conflict_http_exception
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
from src.api.routers.pm_operating_quality_score_run_read_routes import (
    register_pm_quality_score_run_read_routes as register_pm_quality_score_run_read_routes,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityPolicyRepository,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualityScoreRunRepository,
)


ScoreRunBuilder = Callable[
    [
        DpmPmOperatingQualityScorePreviewRequest,
        str | None,
        DpmOutcomeReviewRepository,
        DpmPmQualityPolicyRepository,
    ],
    DpmPmOperatingQualityScoreRun,
]


def register_pm_quality_score_run_command_routes(
    router: APIRouter,
    build_score_run: ScoreRunBuilder,
) -> None:
    @router.post(
        "/score-runs/preview",
        response_model=DpmPmOperatingQualityScorePreviewResponse,
        status_code=status.HTTP_200_OK,
        summary="Preview PM operating quality score run",
        description=(
            "What: Build a deterministic, explainable PM operating quality score run from an "
            "explicit bank-owned policy, source-owned evidence signals, and optional persisted "
            "outcome reviews.\n"
            "When: Use for DPM supervisory control, operations support, or evidence review after "
            "the bank has enabled a governed scoring policy.\n"
            "How: Supply the policy, source-backed evidence, and optional outcome-review ids. "
            "Disabled policies return a DISABLED run with no score; missing required evidence "
            "blocks the run. Optionally supply pm_book_scope to attach source-owned lotus-core "
            "PM-book membership evidence; unavailable, incomplete, degraded, or empty membership "
            "fails closed. The endpoint does not create HR, compensation, conduct-enforcement, "
            "autonomous ranking, AI-generated, risk, performance, execution, or tax methodology."
        ),
    )
    def preview_pm_operating_quality_score_run_endpoint(
        request: DpmPmOperatingQualityScorePreviewRequest,
        x_correlation_id: PmQualityCorrelationIdHeader = None,
        outcome_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
        policy_repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
    ) -> DpmPmOperatingQualityScorePreviewResponse:
        score_run = build_score_run(
            request,
            x_correlation_id,
            outcome_repository,
            policy_repository,
        )
        return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)

    @router.post(
        "/score-runs",
        response_model=DpmPmOperatingQualityScorePreviewResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create persisted PM operating quality score run",
        description=(
            "What: Build and persist an immutable PM operating quality score run from an explicit "
            "bank-owned policy, source-owned evidence signals, and optional persisted outcome "
            "reviews.\n"
            "When: Use after a bank has approved PM operating quality scoring and needs auditable "
            "score-run lifecycle evidence.\n"
            "How: Supply the same evidence contract as preview. The persisted run is "
            "content-addressed and can be retrieved or listed for governance review. This endpoint "
            "does not administer policies, create HR or compensation decisions, perform conduct "
            "enforcement, autonomously rank PMs, or calculate source-owned "
            "risk/performance/tax facts."
        ),
    )
    def create_pm_operating_quality_score_run_endpoint(
        request: DpmPmOperatingQualityScorePreviewRequest,
        x_correlation_id: PmQualityCorrelationIdHeader = None,
        outcome_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
        policy_repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
        score_run_repository: DpmPmQualityScoreRunRepository = Depends(
            get_pm_quality_score_run_repository
        ),
    ) -> DpmPmOperatingQualityScorePreviewResponse:
        score_run = build_score_run(
            request,
            x_correlation_id,
            outcome_repository,
            policy_repository,
        )
        try:
            score_run_repository.save_score_run(score_run=score_run)
        except DpmPmQualityScoreRunConflictError as exc:
            raise pm_quality_conflict_http_exception(exc) from exc
        return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)
