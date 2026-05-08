from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_mandate_repository
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.api.services.mandate_service import (
    DpmMandateNotFoundError,
    DpmMandateSourceIncompleteError,
    DpmMonitoringRunNotFoundError,
    get_command_center_summary,
    get_monitoring_run,
    list_monitoring_exceptions,
    list_monitoring_runs,
    mandate_ids_from_pm_book_membership,
    resolve_monitoring_exception,
    run_mandate_monitoring_once,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmCommandCenterSummary, DpmMonitoringException, DpmMonitoringRun
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError


class DpmMonitoringRunOnceRequest(BaseModel):
    mandate_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Explicit mandate ids to evaluate. Leave empty only when resolving a source-owned "
            "PM-book cohort from lotus-core."
        ),
        examples=[["MANDATE_PB_SG_GLOBAL_BAL_001"]],
    )
    as_of_date: date = Field(
        description="Business date used to evaluate mandate health.",
        examples=["2026-05-03"],
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Optional tenant context captured for audit and later Gateway orchestration.",
        examples=["default"],
    )
    portfolio_manager_id: Optional[str] = Field(
        default=None,
        description=(
            "Portfolio-manager selector captured for audit. When `mandate_ids` is empty, Manage "
            "uses this selector to resolve the cohort from lotus-core "
            "`PortfolioManagerBookMembership:v1`."
        ),
        examples=["PM_SG_DPM_001"],
    )
    book_id: Optional[str] = Field(
        default=None,
        description="Optional PM book id captured for command-center filtering.",
        examples=["BOOK_SG_BALANCED_DPM"],
    )
    booking_center_code: Optional[str] = Field(
        default=None,
        description="Optional booking-center filter forwarded to lotus-core PM-book membership.",
        examples=["Singapore"],
    )
    portfolio_types: list[str] = Field(
        default_factory=lambda: ["DISCRETIONARY"],
        description="Portfolio types eligible for source-owned PM-book monitoring.",
        examples=[["DISCRETIONARY"]],
    )
    requested_by: Optional[str] = Field(
        default=None,
        description="Actor or automation id requesting the monitoring run.",
        examples=["ops_sg_001"],
    )


class DpmMonitoringRunPage(BaseModel):
    items: list[DpmMonitoringRun] = Field(description="Monitoring runs in newest-first order.")
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor to request the next page, or null when no next page exists.",
        examples=["dmr_20260503_083000"],
    )


class DpmMonitoringExceptionPage(BaseModel):
    items: list[DpmMonitoringException] = Field(
        description="Monitoring exceptions in newest-first order."
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor to request the next page, or null when no next page exists.",
        examples=["me_20260503_pb_sg_global_bal_001_source_readiness"],
    )


class DpmMonitoringExceptionResolveRequest(BaseModel):
    resolution_reason: str = Field(
        description="Bounded business reason explaining why the exception was resolved.",
        examples=["PM_CONFIRMED_EXIT_REQUIRED"],
    )


router = APIRouter(prefix="/dpm", tags=["lotus-manage Monitoring"])


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


@router.post(
    "/monitoring/run-once",
    response_model=DpmMonitoringRun,
    summary="Run discretionary mandate monitoring once",
    description=(
        "Use this endpoint to evaluate a bounded set of existing mandate digital twins and persist "
        "a monitoring run, health snapshots, and derived exceptions. Callers may provide explicit "
        "mandate ids or omit them and provide a portfolio-manager selector so Manage resolves the "
        "PM-book cohort from lotus-core `PortfolioManagerBookMembership:v1`."
    ),
    responses={
        200: {"description": "Monitoring run completed and persisted."},
        404: {"description": "At least one requested mandate id was not found."},
    },
)
async def run_once(
    request: DpmMonitoringRunOnceRequest,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMonitoringRun:
    mandate_ids = list(request.mandate_ids)
    source_filters: dict[str, str] = {}
    if not mandate_ids:
        if not request.portfolio_manager_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "DPM_MONITORING_SELECTOR_REQUIRED",
                    "message": "Provide mandate_ids or portfolio_manager_id for PM-book discovery.",
                },
            )
        portfolio_types = [
            portfolio_type.strip().upper()
            for portfolio_type in request.portfolio_types
            if portfolio_type.strip()
        ]
        if not portfolio_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "DPM_MONITORING_PM_BOOK_PORTFOLIO_TYPES_REQUIRED",
                    "message": "PM-book monitoring requires at least one portfolio type.",
                },
            )
        try:
            membership = build_core_resolver_client().resolve_portfolio_manager_book_membership(
                portfolio_manager_id=request.portfolio_manager_id,
                as_of_date=request.as_of_date,
                tenant_id=request.tenant_id,
                booking_center_code=request.booking_center_code,
                portfolio_types=portfolio_types,
                include_inactive=False,
                correlation_id=None,
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
                    "message": "PM-book membership is not source-ready for monitoring.",
                },
            )
        if not membership.members:
            raise HTTPException(
                status_code=status.HTTP_424_FAILED_DEPENDENCY,
                detail={
                    "code": "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
                    "message": "PM-book membership returned no mandates to monitor.",
                },
            )
        try:
            mandate_ids = mandate_ids_from_pm_book_membership(
                repository=repository,
                membership=membership,
            )
        except DpmMandateSourceIncompleteError as exc:
            raise HTTPException(
                status_code=status.HTTP_424_FAILED_DEPENDENCY,
                detail={"code": str(exc) or "DPM_PM_BOOK_MANDATE_SNAPSHOT_MISSING"},
            ) from exc
        source_filters = {
            "source_product": membership.product_name,
            "source_product_version": membership.product_version,
            "source_supportability_state": membership.supportability.state,
        }
        if membership.snapshot_id:
            source_filters["source_snapshot_id"] = membership.snapshot_id
        if membership.source_batch_fingerprint:
            source_filters["source_content_hash"] = membership.source_batch_fingerprint

    try:
        return run_mandate_monitoring_once(
            repository=repository,
            mandate_ids=mandate_ids,
            as_of_date=request.as_of_date,
            filters={
                key: value
                for key, value in {
                    "tenant_id": request.tenant_id,
                    "portfolio_manager_id": request.portfolio_manager_id,
                    "book_id": request.book_id,
                    "booking_center_code": request.booking_center_code,
                    "requested_by": request.requested_by,
                    **source_filters,
                }.items()
                if value is not None
            },
        )
    except DpmMandateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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
    try:
        return get_monitoring_run(repository=repository, monitoring_run_id=monitoring_run_id)
    except DpmMonitoringRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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
