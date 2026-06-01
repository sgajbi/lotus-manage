from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_pm_quality_score_run_repository
from src.api.routers.pm_operating_quality_http import pm_quality_not_found_http_exception
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewResponse,
    DpmPmOperatingQualityScoreRunListResponse,
)
from src.core.pm_quality import DpmPmQualityScoreRunRepository


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
            raise pm_quality_not_found_http_exception(
                code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
                identifier=score_run_id,
            )
        return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)
