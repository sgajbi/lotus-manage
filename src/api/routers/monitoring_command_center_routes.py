from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import Depends, Query

from src.api.dependencies import get_mandate_repository
from src.api.routers.monitoring import router
from src.api.services.mandate_service import get_command_center_summary
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmCommandCenterSummary


@router.get(
    "/command-center",
    response_model=DpmCommandCenterSummary,
    summary="Get discretionary portfolio-management command-center summary",
    description=(
        "Use this endpoint for PM, supervision, operations, Gateway, and Workbench command-center "
        "surfaces that need a bounded book-level view of mandate health distribution, active "
        "attention buckets, recommended actions, and supportability. The response is sourced from "
        "persisted mandate monitoring runs and active exceptions; when PM-book discovery has not "
        "yet been supplied by core or Gateway, the supportability block explicitly reports partial "
        "or empty readiness rather than implying hidden completeness."
    ),
    responses={
        200: {"description": "Bounded DPM command-center summary."},
        422: {"description": "Invalid health-state or pagination filter."},
    },
)
async def read_command_center(
    portfolio_manager_id: Optional[str] = Query(
        default=None,
        description="Optional portfolio-manager id filter captured on monitoring runs.",
        examples=["PM_SG_DPM_001"],
    ),
    tenant_id: Optional[str] = Query(
        default=None,
        description="Optional tenant filter captured on monitoring runs.",
        examples=["default"],
    ),
    as_of_date: Optional[date] = Query(
        default=None,
        description="Optional business date represented by the monitoring run.",
        examples=["2026-05-03"],
    ),
    book_id: Optional[str] = Query(
        default=None,
        description="Optional PM book id captured on monitoring runs.",
        examples=["BOOK_SG_BALANCED_DPM"],
    ),
    health_state: Optional[Literal["READY", "PENDING_REVIEW", "BLOCKED"]] = Query(
        default=None,
        description="Optional health-state focus for the displayed distribution.",
        examples=["PENDING_REVIEW"],
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum active exceptions to consider for attention buckets.",
    ),
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmCommandCenterSummary:
    return get_command_center_summary(
        repository=repository,
        tenant_id=tenant_id,
        portfolio_manager_id=portfolio_manager_id,
        book_id=book_id,
        as_of_date=as_of_date,
        health_state=health_state,
        limit=limit,
    )
