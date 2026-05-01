from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Path, Response, status
from pydantic import Field

from src.api.dependencies import get_db_session
from src.api.request_models import RebalanceRequest
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import rebalance_simulation_service as service
from src.api.simulation_examples import (
    ANALYZE_ASYNC_409_EXAMPLE,
    ANALYZE_ASYNC_ACCEPTED_EXAMPLE,
    ANALYZE_RESPONSE_EXAMPLE,
    SIMULATE_409_EXAMPLE,
    SIMULATE_BLOCKED_EXAMPLE,
    SIMULATE_PENDING_EXAMPLE,
    SIMULATE_READY_EXAMPLE,
)
from src.core.rebalance_runs import (
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
    tags=["lotus-manage Simulation"],
    summary="Simulate a Portfolio Rebalance",
    description=(
        "Use this route when a caller needs one deterministic discretionary mandate rebalance "
        "simulation from a complete inline portfolio, market-data, model, shelf, and options "
        "bundle. Do not use it for advisor-led proposal workflows; those belong in "
        "`lotus-advise`. Do not use it as a portfolio source-data read; source snapshots must "
        "remain governed by upstream portfolio-data authority.\\n\\n"
        "Required header: `Idempotency-Key`. Optional headers: `X-Correlation-Id`, "
        "`X-Policy-Pack-Id`, `X-Tenant-Policy-Pack-Id`, and `X-Tenant-Id`.\\n\\n"
        "For valid payloads, domain outcomes are returned in the response body `status` field: "
        "`READY`, `PENDING_REVIEW`, or `BLOCKED`. Reusing an idempotency key with a different "
        "canonical request hash returns `409`."
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
            description="Required idempotency token for request deduplication at client boundary.",
            examples=["demo-idem-001"],
        ),
    ],
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional trace/correlation identifier propagated to logs.",
            examples=["corr-1234-abcd"],
        ),
    ] = None,
    x_policy_pack_id: Annotated[
        Optional[str],
        Header(
            description=(
                "Optional policy-pack identifier for request-scoped policy selection. "
                "When selected and found in catalog, configured policy fields can override "
                "engine options for this request."
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
) -> RebalanceResult:
    return service.simulate_rebalance(
        request=request,
        idempotency_key=idempotency_key,
        correlation_id=x_correlation_id,
        policy_pack_id=x_policy_pack_id,
        tenant_default_policy_pack_id=x_tenant_policy_pack_id,
        tenant_id=x_tenant_id,
    )


@router.post(
    "/rebalance/analyze",
    response_model=BatchRebalanceResult,
    status_code=status.HTTP_200_OK,
    tags=["lotus-manage What-If Analysis"],
    summary="Analyze Multiple Rebalance Scenarios",
    description=(
        "Runs multiple named what-if scenarios using shared snapshots and returns the full batch "
        "result in one response.\\n\\n"
        "Use this synchronous route when the caller needs immediate results for up to 20 "
        "scenarios in one request. Use `POST /api/v1/rebalance/analyze/async` when the caller needs "
        "polling-based orchestration or `ACCEPT_ONLY` execution.\\n\\n"
        "Each scenario validates `options` independently, executes in sorted scenario-key order, "
        "and contributes to `results`, `comparison_metrics`, `failed_scenarios`, and batch-level "
        "`warnings`."
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
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description=(
                "Optional batch correlation identifier. Successful scenario results append the "
                "scenario name to this value as `{correlation_id}:{scenario_name}`."
            ),
            examples=["corr-batch-sync-1"],
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
) -> BatchRebalanceResult:
    return service.execute_batch_analysis(
        request=request,
        correlation_id=x_correlation_id,
        request_policy_pack_id=x_policy_pack_id,
        tenant_default_policy_pack_id=x_tenant_policy_pack_id,
        tenant_id=x_tenant_id,
    )


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
        BatchRebalanceRequest,
        Field(description="Shared snapshots plus scenario map of option overrides."),
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
    accepted = service.submit_and_optionally_execute_async_analysis(
        request=request,
        correlation_id=x_correlation_id,
        policy_pack_id=x_policy_pack_id,
        tenant_default_policy_pack_id=x_tenant_policy_pack_id,
        tenant_id=x_tenant_id,
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
