from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, Response, status
from pydantic import Field

from src.api.dependencies import get_db_session
from src.api.request_models import BatchExecutionRequestEnvelope
from src.api.routers.rebalance_simulation import router
from src.api.routers.rebalance_simulation_http import (
    rebalance_async_operation_http_exception,
    rebalance_envelope_http_exception,
)
from src.api.services import rebalance_simulation_service as service
from src.api.simulation_examples import (
    ANALYZE_ASYNC_409_EXAMPLE,
    ANALYZE_ASYNC_ACCEPTED_EXAMPLE,
)
from src.core.rebalance_runs import DpmAsyncAcceptedResponse


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
    try:
        batch_request, source_context = service.resolve_batch_request_envelope(
            envelope=request,
            correlation_id=x_correlation_id,
        )
    except service.DpmRebalanceEnvelopeError as exc:
        raise rebalance_envelope_http_exception(exc) from exc
    try:
        accepted = service.submit_and_optionally_execute_async_analysis(
            request=batch_request,
            correlation_id=x_correlation_id,
            policy_pack_id=x_policy_pack_id,
            tenant_default_policy_pack_id=x_tenant_policy_pack_id,
            tenant_id=x_tenant_id,
            source_context=source_context,
        )
    except service.DpmRebalanceAsyncOperationError as exc:
        raise rebalance_async_operation_http_exception(exc) from exc
    response.headers["X-Correlation-Id"] = accepted.correlation_id
    return accepted
