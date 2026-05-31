from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Path, status

from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.routers.rebalance_simulation import router
from src.api.routers.rebalance_simulation_http import rebalance_async_operation_http_exception
from src.api.services import rebalance_simulation_service as service
from src.core.rebalance_runs import (
    DpmAsyncOperationStatusResponse,
    DpmRunSupportService,
)


@router.post(
    "/rebalance/operations/{operation_id}/execute",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["lotus-manage Run Supportability"],
    summary="Execute Pending lotus-manage Async Operation",
    description=(
        "Executes one pending asynchronous lotus-manage scenario-analysis operation that was "
        "accepted through `POST /api/v1/rebalance/analyze/async` while "
        "`DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`. Use this endpoint for governed external "
        "orchestration where the caller first records an operation handle, then explicitly "
        "starts execution. Do not use it for already terminal operations; they are returned by "
        "`GET /api/v1/rebalance/operations/{operation_id}` and are rejected here with `409`."
    ),
    responses={
        200: {
            "description": (
                "Execution attempt completed and returned terminal operation status. "
                "The status may be `SUCCEEDED` with a batch result or `FAILED` with structured "
                "error details."
            ),
        },
        404: {"description": "Operation not found or manual execution disabled."},
        409: {"description": "Operation is not in executable pending state."},
    },
)
def execute_dpm_async_operation(
    operation_id: Annotated[
        str,
        Path(description="Asynchronous operation identifier.", examples=["dop_001"]),
    ],
    service_instance: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)],
) -> DpmAsyncOperationStatusResponse:
    try:
        return service.execute_dpm_async_operation(
            operation_id=operation_id,
            service=service_instance,
        )
    except service.DpmRebalanceAsyncOperationError as exc:
        raise rebalance_async_operation_http_exception(exc) from exc
