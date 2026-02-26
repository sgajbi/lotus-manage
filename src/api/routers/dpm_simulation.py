from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Path, Response, status
from pydantic import Field

from src.api.dependencies import get_db_session
from src.api.request_models import RebalanceRequest
from src.api.routers.dpm_runs import get_dpm_run_support_service
from src.api.services import dpm_simulation_service as service
from src.api.simulation_examples import (
    ANALYZE_ASYNC_ACCEPTED_EXAMPLE,
    ANALYZE_RESPONSE_EXAMPLE,
    SIMULATE_409_EXAMPLE,
    SIMULATE_BLOCKED_EXAMPLE,
    SIMULATE_PENDING_EXAMPLE,
    SIMULATE_READY_EXAMPLE,
)
from src.core.dpm_runs import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationStatusResponse,
    DpmRunSupportService,
)
from src.core.models import BatchRebalanceRequest, BatchRebalanceResult, RebalanceResult

router = APIRouter()


@router.post(
    "/rebalance/simulate",
    response_model=RebalanceResult,
    status_code=status.HTTP_200_OK,
    tags=["DPM Simulation"],
    summary="Simulate a Portfolio Rebalance",
    description=(
        "Runs one deterministic rebalance simulation.\\n\\n"
        "Required header: `Idempotency-Key`.\\n"
        "Optional header: `X-Correlation-Id`.\\n\\n"
        "For valid payloads, domain outcomes are returned in the response body status field."
    ),
    responses={
        200: {
            "description": "Simulation completed with domain status in payload.",
            "content": {
                "application/json": {
                    "examples": {
                        "ready": SIMULATE_READY_EXAMPLE,
                        "pending_review": SIMULATE_PENDING_EXAMPLE,
                        "blocked": SIMULATE_BLOCKED_EXAMPLE,
                    }
                }
            },
        },
        422: {
            "description": "Validation error (invalid payload or missing required headers).",
        },
        409: {
            "description": "Idempotency key reused with different canonical request hash.",
            "content": {"application/json": {"examples": {"conflict": SIMULATE_409_EXAMPLE}}},
        },
    },
)
def simulate_rebalance(
    request: RebalanceRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency token for request deduplication at client boundary.",
            examples=["demo-idem-001"],
        ),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional trace/correlation identifier propagated to logs.",
            examples=["corr-1234-abcd"],
        ),
    ] = None,
    policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Policy-Pack-Id",
            description=(
                "Optional policy-pack identifier for request-scoped policy selection. "
                "When selected and found in catalog, configured policy fields can override "
                "engine options for this request."
            ),
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    tenant_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Id",
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> RebalanceResult:
    return service.simulate_rebalance(
        request=request,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        policy_pack_id=policy_pack_id,
        tenant_id=tenant_id,
    )


@router.post(
    "/rebalance/analyze",
    response_model=BatchRebalanceResult,
    status_code=status.HTTP_200_OK,
    tags=["DPM What-If Analysis"],
    summary="Analyze Multiple Rebalance Scenarios",
    description=(
        "Runs multiple named what-if scenarios using shared snapshots.\\n\\n"
        "Each scenario validates `options` independently and executes in sorted scenario-key order."
    ),
    responses={
        200: {
            "description": "Batch analysis result.",
            "content": {
                "application/json": {"examples": {"batch_result": ANALYZE_RESPONSE_EXAMPLE}}
            },
        },
        422: {
            "description": "Validation error (invalid shared payload or scenario key format).",
        },
    },
)
def analyze_scenarios(
    request: Annotated[
        BatchRebalanceRequest,
        Field(description="Shared snapshots plus scenario map of option overrides."),
    ],
    correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-Id")] = None,
    policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Policy-Pack-Id",
            description=(
                "Optional policy-pack identifier for request-scoped policy selection. "
                "When selected and found in catalog, configured policy fields can override "
                "scenario engine options for this request."
            ),
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    tenant_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Id",
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> BatchRebalanceResult:
    return service.execute_batch_analysis(
        request=request,
        correlation_id=correlation_id,
        request_policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=None,
        tenant_id=tenant_id,
    )


@router.post(
    "/rebalance/analyze/async",
    response_model=DpmAsyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["DPM What-If Analysis"],
    summary="Analyze Multiple Rebalance Scenarios Asynchronously",
    description=(
        "Accepts named what-if scenarios for asynchronous execution.\\n\\n"
        "Execution mode is controlled by `DPM_ASYNC_EXECUTION_MODE` (`INLINE` or `ACCEPT_ONLY`).\\n"
        "Use `GET /rebalance/operations/{operation_id}` or "
        "`GET /rebalance/operations/by-correlation/{correlation_id}` for status/result retrieval."
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
        422: {"description": "Validation error (invalid shared payload or scenario key format)."},
    },
)
def analyze_scenarios_async(
    request: Annotated[
        BatchRebalanceRequest,
        Field(description="Shared snapshots plus scenario map of option overrides."),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation identifier for async tracking and lookup.",
            examples=["corr-batch-async-1"],
        ),
    ] = None,
    policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Policy-Pack-Id",
            description=(
                "Optional policy-pack identifier for request-scoped policy selection. "
                "When selected and found in catalog, configured policy fields can override "
                "scenario engine options for this request."
            ),
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    tenant_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Id",
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
    response: Response = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> DpmAsyncAcceptedResponse:
    accepted = service.submit_and_optionally_execute_async_analysis(
        request=request,
        correlation_id=correlation_id,
        policy_pack_id=policy_pack_id,
        tenant_id=tenant_id,
    )
    if response is not None:
        response.headers["X-Correlation-Id"] = accepted.correlation_id
    return accepted


@router.post(
    "/rebalance/operations/{operation_id}/execute",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["DPM Run Supportability"],
    summary="Execute Pending DPM Async Operation",
    description=(
        "Executes one pending asynchronous DPM analyze operation. "
        "Intended for orchestrated `ACCEPT_ONLY` mode flows."
    ),
    responses={
        200: {"description": "Operation execution completed; returns terminal status payload."},
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
