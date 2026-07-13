from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_pm_quality_score_run_application_service
from src.api.routers.pm_operating_quality_http import pm_quality_service_http_exception
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewResponse,
    DpmPmOperatingQualityScoreRunListResponse,
)
from src.api.routers.pm_operating_quality_temporal_filters import pm_quality_as_of_date_filter
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)


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
            "stored score-run evidence only, follows methodology "
            "docs/methodologies/pm-quality/scoring-and-fairness.md, and does not recompute scores."
        ),
    )
    def list_pm_operating_quality_score_runs_endpoint(
        pm_id: Annotated[str | None, Query(description="Filter by portfolio manager id.")] = None,
        book_id: Annotated[str | None, Query(description="Filter by PM book id.")] = None,
        policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
        as_of_date: Annotated[str | None, Depends(pm_quality_as_of_date_filter)] = None,
        state: Annotated[str | None, Query(description="Filter by score-run state.")] = None,
        limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
        offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
        application_service: DpmPmOperatingQualityApplicationService = Depends(
            get_pm_quality_score_run_application_service
        ),
    ) -> DpmPmOperatingQualityScoreRunListResponse:
        score_runs = application_service.list_score_runs(
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
            "source facts or policy output. Methodology: "
            "docs/methodologies/pm-quality/scoring-and-fairness.md."
        ),
    )
    def get_pm_operating_quality_score_run_endpoint(
        score_run_id: str,
        application_service: DpmPmOperatingQualityApplicationService = Depends(
            get_pm_quality_score_run_application_service
        ),
    ) -> DpmPmOperatingQualityScorePreviewResponse:
        try:
            score_run = application_service.get_score_run(score_run_id=score_run_id)
        except DpmPmOperatingQualityServiceError as exc:
            raise pm_quality_service_http_exception(exc) from exc
        return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)
