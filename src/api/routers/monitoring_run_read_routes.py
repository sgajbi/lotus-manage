from __future__ import annotations

from typing import Literal, Optional

from fastapi import Depends, Query

from src.api.dependencies import get_mandate_repository
from src.api.routers.mandate_http import read_mandate_with_not_found_http_mapping
from src.api.routers.monitoring import router
from src.api.routers.monitoring_models import DpmMonitoringRunPage
from src.api.services.mandate_service import (
    get_monitoring_run,
    list_monitoring_runs,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMonitoringRun


@router.get(
    "/monitoring/runs",
    response_model=DpmMonitoringRunPage,
    summary="List discretionary mandate monitoring runs",
    description="Use this endpoint for bounded operator search over mandate monitoring runs.",
    responses={200: {"description": "Bounded monitoring run page."}},
)
async def read_monitoring_runs(
    status_filter: Optional[Literal["SUCCEEDED", "FAILED"]] = Query(
        default=None,
        description="Optional terminal status filter.",
        examples=["SUCCEEDED"],
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum runs to return."),
    cursor: Optional[str] = Query(default=None, description="Cursor from a previous page."),
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMonitoringRunPage:
    items, next_cursor = list_monitoring_runs(
        repository=repository,
        status=status_filter,
        limit=limit,
        cursor=cursor,
    )
    return DpmMonitoringRunPage(items=items, next_cursor=next_cursor)


@router.get(
    "/monitoring/runs/{monitoring_run_id}",
    response_model=DpmMonitoringRun,
    summary="Get one discretionary mandate monitoring run",
    description="Use this endpoint to inspect one persisted monitoring run by id.",
    responses={
        200: {"description": "Persisted monitoring run."},
        404: {"description": "Monitoring run id was not found."},
    },
)
async def read_monitoring_run(
    monitoring_run_id: str,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMonitoringRun:
    return read_mandate_with_not_found_http_mapping(
        lambda: get_monitoring_run(
            repository=repository,
            monitoring_run_id=monitoring_run_id,
        )
    )
