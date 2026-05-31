from __future__ import annotations

from typing import Literal, Optional

from fastapi import Depends, HTTPException, Query, status

from src.api.dependencies import get_mandate_repository
from src.api.routers.monitoring import router
from src.api.routers.monitoring_models import (
    DpmMonitoringExceptionPage,
    DpmMonitoringExceptionResolveRequest,
)
from src.api.services.mandate_service import (
    DpmMandateNotFoundError,
    list_monitoring_exceptions,
    resolve_monitoring_exception,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMonitoringException


@router.get(
    "/exceptions",
    response_model=DpmMonitoringExceptionPage,
    summary="Search discretionary mandate monitoring exceptions",
    description=(
        "Use this endpoint for PM, supervision, and operations queues that need active or resolved "
        "mandate monitoring exceptions by mandate, portfolio, or state."
    ),
    responses={200: {"description": "Bounded monitoring exception page."}},
)
async def read_exceptions(
    mandate_id: Optional[str] = Query(default=None, description="Optional mandate id filter."),
    portfolio_id: Optional[str] = Query(default=None, description="Optional portfolio id filter."),
    state: Optional[Literal["ACTIVE", "RESOLVED"]] = Query(
        default=None,
        description="Optional exception state filter.",
        examples=["ACTIVE"],
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum exceptions to return."),
    cursor: Optional[str] = Query(default=None, description="Cursor from a previous page."),
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMonitoringExceptionPage:
    items, next_cursor = list_monitoring_exceptions(
        repository=repository,
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        state=state,
        limit=limit,
        cursor=cursor,
    )
    return DpmMonitoringExceptionPage(items=items, next_cursor=next_cursor)


@router.post(
    "/exceptions/{exception_id}/resolve",
    response_model=DpmMonitoringException,
    summary="Resolve a discretionary mandate monitoring exception",
    description=(
        "Use this endpoint when a PM, supervisor, or operator has reviewed an exception and needs "
        "to close it with an auditable resolution reason."
    ),
    responses={
        200: {"description": "Resolved monitoring exception."},
        404: {"description": "Monitoring exception id was not found."},
    },
)
async def resolve_exception(
    exception_id: str,
    request: DpmMonitoringExceptionResolveRequest,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMonitoringException:
    try:
        return resolve_monitoring_exception(
            repository=repository,
            exception_id=exception_id,
            resolution_reason=request.resolution_reason,
        )
    except DpmMandateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
