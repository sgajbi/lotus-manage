from typing import Annotated

from fastapi import Path, status

from src.api.routers import rebalance_runs as shared
from src.api.routers.rebalance_runs_http import read_run_with_not_found_http_mapping
from src.core.rebalance_runs import (
    DpmAsyncOperationStatusResponse,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/operations/{operation_id}",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Async Operation",
    description=(
        "Returns one asynchronous operation status record by operation id. Use this endpoint after "
        "`POST /api/v1/rebalance/analyze/async`, after `GET /api/v1/rebalance/operations`, or from operator "
        "support tooling when the exact operation handle is known. Terminal `SUCCEEDED` operations "
        "include the batch analysis result payload; terminal `FAILED` operations include structured "
        "error details. Use `GET /api/v1/rebalance/operations/by-correlation/{correlation_id}` when the "
        "caller has only a correlation id."
    ),
    responses={
        200: {
            "description": (
                "Operation status, executability flag, timestamps, and terminal result or error."
            ),
        },
        404: {"description": "Operation not found or async operations disabled."},
    },
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
    return read_run_with_not_found_http_mapping(
        lambda: service.get_async_operation(operation_id=operation_id)
    )


@shared.router.get(
    "/rebalance/operations/by-correlation/{correlation_id}",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Async Operation by Correlation Id",
    description=(
        "Returns one asynchronous operation status record by correlation id. Use this endpoint when "
        "the caller submitted `X-Correlation-Id` to `POST /api/v1/rebalance/analyze/async` and does not "
        "have the generated operation id. Terminal `SUCCEEDED` operations include the batch "
        "analysis result payload; terminal `FAILED` operations include structured error details. "
        "Use `GET /api/v1/rebalance/operations/{operation_id}` when the operation id is already known."
    ),
    responses={
        200: {
            "description": (
                "Operation status, executability flag, timestamps, and terminal result or error."
            ),
        },
        404: {
            "description": "Operation not found for correlation id or async operations disabled."
        },
    },
)
def get_dpm_async_operation_by_correlation(
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier associated with async operation.",
            examples=["corr-dpm-async-001"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmAsyncOperationStatusResponse:
    shared._assert_support_apis_enabled()
    shared._assert_async_operations_enabled()
    return read_run_with_not_found_http_mapping(
        lambda: service.get_async_operation_by_correlation(correlation_id=correlation_id)
    )
