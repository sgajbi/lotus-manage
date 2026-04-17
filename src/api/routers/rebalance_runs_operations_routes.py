from typing import Annotated, Optional

from fastapi import HTTPException, Path, Query, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmAsyncOperationListResponse,
    DpmAsyncOperationStatusResponse,
    DpmLineageResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/operations",
    response_model=DpmAsyncOperationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List lotus-manage Async Operations",
    description=(
        "Returns asynchronous operation records with optional filters and cursor pagination. "
        "Use the canonical query parameter `status_filter` for operation status filtering; "
        "unsupported aliases are rejected."
    ),
    responses={
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


@shared.router.get(
    "/rebalance/operations/{operation_id}",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Async Operation",
    description="Returns asynchronous operation status and terminal result/error payload.",
)
def get_dpm_async_operation(
    operation_id: Annotated[
        str,
        Path(description="Asynchronous operation identifier.", examples=["dop_001"]),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmAsyncOperationStatusResponse:
    shared._assert_support_apis_enabled()
    shared._assert_async_operations_enabled()
    try:
        return service.get_async_operation(operation_id=operation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/operations/by-correlation/{correlation_id}",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Async Operation by Correlation Id",
    description="Returns asynchronous operation associated with correlation id.",
)
def get_dpm_async_operation_by_correlation(
    correlation_id: Annotated[
        str,
        Path(description="Correlation identifier associated with async operation."),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmAsyncOperationStatusResponse:
    shared._assert_support_apis_enabled()
    shared._assert_async_operations_enabled()
    try:
        return service.get_async_operation_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/lineage/{entity_id}",
    response_model=DpmLineageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Supportability Lineage by Entity Id",
    description=(
        "Returns supportability lineage edges for an entity id, including correlation, "
        "idempotency, run, and operation relations. Supported filters are `edge_type`, "
        "`created_from`, `created_to`, `limit`, and `cursor`; unsupported aliases are rejected."
    ),
    responses={
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
    },
)
def get_dpm_lineage(
    request: Request,
    entity_id: Annotated[
        str,
        Path(
            description=(
                "Supportability entity identifier such as correlation id, idempotency key, "
                "run id, or operation id."
            ),
            examples=["corr-1234-abcd"],
        ),
    ],
    edge_type: Annotated[
        Optional[str],
        Query(
            description="Optional lineage edge-type filter.",
            examples=["CORRELATION_TO_RUN"],
        ),
    ] = None,
    created_from: Annotated[
        Optional[shared.datetime],
        Query(
            description="Lineage edge creation lower bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        Optional[shared.datetime],
        Query(
            description="Lineage edge creation upper bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T23:59:59Z"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of lineage edges returned in one page.",
            examples=[50],
        ),
    ] = 50,
    cursor: Annotated[
        Optional[str],
        Query(
            description="Opaque lineage cursor returned by previous page.",
            examples=["2026-02-20T12:00:00+00:00|corr-1234|CORRELATION_TO_RUN|rr_abc12345"],
        ),
    ] = None,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmLineageResponse:
    shared._assert_support_apis_enabled()
    shared._assert_lineage_apis_enabled()
    shared._reject_unexpected_query_params(
        request,
        allowed_params={"edge_type", "created_from", "created_to", "limit", "cursor"},
    )
    return service.get_lineage_filtered(
        entity_id=entity_id,
        edge_type=edge_type,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        cursor=cursor,
    )
