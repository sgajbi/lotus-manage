import importlib
from typing import Annotated, Optional

from fastapi import Query, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmAsyncOperationListResponse,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/operations",
    response_model=DpmAsyncOperationListResponse,
    status_code=status.HTTP_200_OK,
    tags=["lotus-manage Run Supportability"],
    summary="List lotus-manage Async Operations",
    description=(
        "Returns asynchronous operation records for discretionary mandate supportability, "
        "operator triage, and downstream polling dashboards. Use this endpoint when a caller needs "
        "a bounded page of operations filtered by creation window, operation type, status, or "
        "correlation id. Use `GET /api/v1/rebalance/operations/{operation_id}` when the caller already "
        "has a single operation handle. Use the canonical query parameter `status_filter` for "
        "operation status filtering; unsupported aliases are rejected."
    ),
    responses={
        200: {
            "description": (
                "Filtered async operation page ordered by newest creation timestamp, then "
                "operation id, with an opaque `next_cursor` when another page exists."
            ),
        },
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
    },
)
def list_dpm_async_operations(
    request: Request,
    created_from: Annotated[
        Optional[shared.datetime],
        Query(
            description="Operation creation lower bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        Optional[shared.datetime],
        Query(
            description="Operation creation upper bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T23:59:59Z"],
        ),
    ] = None,
    operation_type: Annotated[
        Optional[str],
        Query(
            description="Optional asynchronous operation type filter.",
            examples=["ANALYZE_SCENARIOS"],
        ),
    ] = None,
    status_filter: Annotated[
        Optional[str],
        Query(
            description="Optional operation status filter.",
            examples=["SUCCEEDED"],
        ),
    ] = None,
    correlation_id: Annotated[
        Optional[str],
        Query(
            description="Optional correlation id filter.",
            examples=["corr-dpm-async-001"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of rows returned in one page.",
            examples=[50],
        ),
    ] = 50,
    cursor: Annotated[
        Optional[str],
        Query(
            description="Opaque cursor value returned by previous page.",
            examples=["dop_001"],
        ),
    ] = None,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmAsyncOperationListResponse:
    shared._assert_support_apis_enabled()
    shared._assert_async_operations_enabled()
    shared._reject_unexpected_query_params(
        request,
        allowed_params={
            "created_from",
            "created_to",
            "operation_type",
            "status_filter",
            "correlation_id",
            "limit",
            "cursor",
        },
    )
    return service.list_async_operations(
        created_from=created_from,
        created_to=created_to,
        operation_type=operation_type,
        status=status_filter,
        correlation_id=correlation_id,
        limit=limit,
        cursor=cursor,
    )


importlib.import_module("src.api.routers.rebalance_runs_async_operation_lookup_routes")
