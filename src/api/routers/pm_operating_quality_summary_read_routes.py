from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_pm_quality_summary_invocation_application_service
from src.api.routers.pm_operating_quality_http import pm_quality_service_http_exception
from src.api.routers.pm_operating_quality_models import (
    DpmPmQualitySummaryInvocationListResponse,
    DpmPmQualitySummaryInvocationResponse,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)
from src.core.pm_quality import (
    PmQualitySummaryInvocationState,
)

router = APIRouter()


@router.get(
    "/summary-invocations",
    response_model=DpmPmQualitySummaryInvocationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted PM operating quality support-summary invocation history",
    description=(
        "What: Return a bounded page of persisted PM operating-quality support-summary "
        "invocation history.\n"
        "When: Use for audit, supportability diagnostics, and review-gated AI workflow evidence "
        "retrieval.\n"
        "How: Filter by score run, review action, policy, as-of date, or invocation state. The "
        "response returns stored workflow and artifact identity only and does not expose generated "
        "summary text, raw review rationale, score values, rankings, client-contact, trade, order, "
        "or OMS execution claims."
    ),
)
def list_pm_quality_summary_invocations_endpoint(
    score_run_id: Annotated[str | None, Query(description="Filter by score-run id.")] = None,
    review_action_id: Annotated[
        str | None,
        Query(description="Filter by review-action id."),
    ] = None,
    policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
    as_of_date: Annotated[str | None, Query(description="Filter by business as-of date.")] = None,
    invocation_state: Annotated[
        PmQualitySummaryInvocationState | None,
        Query(description="Filter by bounded summary-invocation state."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_summary_invocation_application_service
    ),
) -> DpmPmQualitySummaryInvocationListResponse:
    invocations = application_service.list_summary_invocations(
        score_run_id=score_run_id,
        review_action_id=review_action_id,
        policy_id=policy_id,
        as_of_date=as_of_date,
        invocation_state=invocation_state,
        limit=limit,
        offset=offset,
    )
    return DpmPmQualitySummaryInvocationListResponse(
        summary_invocations=invocations,
        count=len(invocations),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/summary-invocations/{summary_invocation_id}",
    response_model=DpmPmQualitySummaryInvocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get persisted PM operating quality support-summary invocation history",
    description=(
        "What: Return one persisted PM operating-quality support-summary invocation history row "
        "by stable id.\n"
        "When: Use for audit, supportability diagnostics, and review-gated workflow evidence "
        "retrieval.\n"
        "How: The endpoint returns immutable stored invocation evidence and does not recompute or "
        "mutate the score run, review action, or downstream summary artifact."
    ),
)
def get_pm_quality_summary_invocation_endpoint(
    summary_invocation_id: str,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_summary_invocation_application_service
    ),
) -> DpmPmQualitySummaryInvocationResponse:
    try:
        invocation = application_service.get_summary_invocation(
            summary_invocation_id=summary_invocation_id
        )
    except DpmPmOperatingQualityServiceError as exc:
        raise pm_quality_service_http_exception(exc) from exc
    return DpmPmQualitySummaryInvocationResponse(summary_invocation=invocation)
