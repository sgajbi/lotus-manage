from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, status
from pydantic import Field

from src.api.dependencies import get_db_session
from src.api.request_models import BatchExecutionRequestEnvelope
from src.api.routers.rebalance_simulation import router
from src.api.routers.rebalance_simulation_http import rebalance_envelope_http_exception
from src.api.services import rebalance_simulation_service as service
from src.api.simulation_examples import ANALYZE_RESPONSE_EXAMPLE
from src.core.models import BatchRebalanceResult


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
        BatchExecutionRequestEnvelope,
        Field(
            description="Stateless envelope containing shared snapshots plus scenario overrides."
        ),
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
    try:
        batch_request, source_context = service.resolve_batch_request_envelope(
            envelope=request,
            correlation_id=x_correlation_id,
        )
    except service.DpmRebalanceEnvelopeError as exc:
        raise rebalance_envelope_http_exception(exc) from exc
    return service.execute_batch_analysis(
        request=batch_request,
        correlation_id=x_correlation_id,
        request_policy_pack_id=x_policy_pack_id,
        tenant_default_policy_pack_id=x_tenant_policy_pack_id,
        tenant_id=x_tenant_id,
        source_context=source_context,
    )
