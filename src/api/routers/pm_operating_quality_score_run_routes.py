from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import (
    get_outcome_review_repository,
    get_pm_quality_policy_repository,
    get_pm_quality_score_run_repository,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewRequest,
    DpmPmOperatingQualityScorePreviewResponse,
    DpmPmOperatingQualityScoreRunListResponse,
)
from src.api.routers.pm_operating_quality_route_parameters import PmQualityCorrelationIdHeader
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc
        return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)


def register_pm_quality_score_run_read_routes(router: APIRouter) -> None:
    @router.get(
        "/score-runs",
        response_model=DpmPmOperatingQualityScoreRunListResponse,
        status_code=status.HTTP_200_OK,
        summary="List persisted PM operating quality score runs",
        description=(
            "What: Return a bounded page of persisted PM operating quality score runs.\n"
            "When: Use for PM operating-quality governance review and supportability diagnostics.\n"
            "How: Filter by PM, book, policy, as-of date, or bounded state. The response returns "
            "stored score-run evidence only and does not recompute scores."
        ),
    )
    def list_pm_operating_quality_score_runs_endpoint(
        pm_id: Annotated[str | None, Query(description="Filter by portfolio manager id.")] = None,
        book_id: Annotated[str | None, Query(description="Filter by PM book id.")] = None,
        policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
        as_of_date: Annotated[
            str | None,
            Query(description="Filter by business as-of date."),
        ] = None,
        state: Annotated[str | None, Query(description="Filter by score-run state.")] = None,
        limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
        offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
        repository: DpmPmQualityScoreRunRepository = Depends(get_pm_quality_score_run_repository),
    ) -> DpmPmOperatingQualityScoreRunListResponse:
        score_runs = repository.list_score_runs(
            pm_id=pm_id,
            book_id=book_id,
            policy_id=policy_id,
            as_of_date=as_of_date,
            state=state,
            limit=limit,
            offset=offset,
        )
        return DpmPmOperatingQualityScoreRunListResponse(
            score_runs=score_runs,
            count=len(score_runs),
            limit=limit,
            offset=offset,
        )

    @router.get(
        "/score-runs/{score_run_id}",
        response_model=DpmPmOperatingQualityScorePreviewResponse,
        status_code=status.HTTP_200_OK,
        summary="Get persisted PM operating quality score run",
        description=(
            "What: Return one persisted PM operating quality score run by stable id.\n"
            "When: Use for audit, supportability review, and downstream evidence retrieval.\n"
            "How: The endpoint returns immutable stored score-run evidence and does not recompute "
            "source facts or policy output."
        ),
    )
    def get_pm_operating_quality_score_run_endpoint(
        score_run_id: str,
        repository: DpmPmQualityScoreRunRepository = Depends(get_pm_quality_score_run_repository),
    ) -> DpmPmOperatingQualityScorePreviewResponse:
        score_run = repository.get_score_run(score_run_id=score_run_id)
        if score_run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PM_QUALITY_SCORE_RUN_NOT_FOUND:{score_run_id}",
            )
        return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)
