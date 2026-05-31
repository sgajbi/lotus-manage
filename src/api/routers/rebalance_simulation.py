import importlib
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Path, Response, status
from pydantic import Field

from src.api.dependencies import get_db_session
from src.api.request_models import BatchExecutionRequestEnvelope
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import rebalance_simulation_service as service
from src.api.simulation_examples import (
    ANALYZE_ASYNC_409_EXAMPLE,
    ANALYZE_ASYNC_ACCEPTED_EXAMPLE,
)
from src.core.rebalance_runs import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationStatusResponse,
    DpmRunSupportService,
)

router = APIRouter()


_simulate_routes = importlib.import_module("src.api.routers.rebalance_simulation_simulate_routes")
simulate_rebalance = _simulate_routes.simulate_rebalance
_analyze_routes = importlib.import_module("src.api.routers.rebalance_simulation_analyze_routes")
analyze_scenarios = _analyze_routes.analyze_scenarios


@router.post(
    "/rebalance/analyze/async",
    response_model=DpmAsyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["lotus-manage What-If Analysis"],
    summary="Analyze Multiple Rebalance Scenarios Asynchronously",
    description=(
        "Accepts named what-if scenarios for asynchronous execution and returns a polling handle "
        "instead of the full batch result.\\n\\n"
        "Use this route when the caller needs polling-based orchestration, deferred execution, "
        "or `DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`. Use `POST /api/v1/rebalance/analyze` when immediate "
        "batch results are required.\\n\\n"
        "Execution mode is controlled by `DPM_ASYNC_EXECUTION_MODE` (`INLINE` or `ACCEPT_ONLY`).\\n"
        "Use `GET /api/v1/rebalance/operations/{operation_id}` or "
        "`GET /api/v1/rebalance/operations/by-correlation/{correlation_id}` for status/result retrieval."
    ),
    responses={
        202: {
            "description": "Async batch accepted.",
            "headers": {
                "X-Correlation-Id": {
                    "description": (
                        "Resolved correlation id for this asynchronous operation "
                        "(client-provided or generated)."
                    ),
                    "schema": {
                        "type": "string",
                        "examples": ["corr-batch-async-1"],
                    },
                }
            },
            "content": {
                "application/json": {"examples": {"accepted": ANALYZE_ASYNC_ACCEPTED_EXAMPLE}}
            },
        },
        404: {"description": "Async operations disabled by configuration."},
        409: {
            "description": "Correlation id already belongs to an existing async operation.",
            "content": {
                "application/json": {
                    "examples": {"correlation_conflict": ANALYZE_ASYNC_409_EXAMPLE}
                }
            },
        },
        422: {"description": "Validation error (invalid shared payload or scenario key format)."},
    },
)
def analyze_scenarios_async(
    request: Annotated[
        BatchExecutionRequestEnvelope,
        Field(
            description="Stateless envelope containing shared snapshots plus scenario overrides."
        ),
    ],
    response: Response,
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional correlation identifier for async tracking and lookup.",
            examples=["corr-batch-async-1"],
        ),
    ] = None,
    x_policy_pack_id: Annotated[
        Optional[str],
        Header(
            description=(
                "Optional policy-pack identifier for request-scoped policy selection. "
                "When selected and found in catalog, configured policy fields can override "
                "scenario engine options for this request."
            ),
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    x_tenant_policy_pack_id: Annotated[
        Optional[str],
        Header(
            description=(
                "Optional explicit tenant-default policy-pack identifier. Used when no "
                "`X-Policy-Pack-Id` request override is supplied and policy packs are enabled."
            ),
            examples=["dpm_tenant_default_v1"],
        ),
    ] = None,
    x_tenant_id: Annotated[
        Optional[str],
        Header(
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> DpmAsyncAcceptedResponse:
    batch_request, source_context = service.resolve_batch_request_envelope(
        envelope=request,
        correlation_id=x_correlation_id,
    )
    accepted = service.submit_and_optionally_execute_async_analysis(
        request=batch_request,
        correlation_id=x_correlation_id,
        policy_pack_id=x_policy_pack_id,
        tenant_default_policy_pack_id=x_tenant_policy_pack_id,
        tenant_id=x_tenant_id,
        source_context=source_context,
    )
    response.headers["X-Correlation-Id"] = accepted.correlation_id
    return accepted


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
    return service.execute_dpm_async_operation(
        operation_id=operation_id,
        service=service_instance,
    )
