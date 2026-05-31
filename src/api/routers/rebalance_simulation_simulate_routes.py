from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, status

from src.api.dependencies import get_db_session
from src.api.request_models import RebalanceExecutionRequestEnvelope
from src.api.routers.rebalance_simulation import router
from src.api.routers.rebalance_simulation_http import (
    rebalance_envelope_http_exception,
    rebalance_simulation_http_exception,
)
from src.api.services import rebalance_simulation_service as service
from src.api.simulation_examples import (
    SIMULATE_409_EXAMPLE,
    SIMULATE_BLOCKED_EXAMPLE,
    SIMULATE_PENDING_EXAMPLE,
    SIMULATE_READY_EXAMPLE,
)
from src.core.models import RebalanceResult


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
    request: RebalanceExecutionRequestEnvelope,
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
    try:
        rebalance_request, source_context = service.resolve_rebalance_request_envelope(
            envelope=request,
            correlation_id=x_correlation_id,
        )
    except service.DpmRebalanceEnvelopeError as exc:
        raise rebalance_envelope_http_exception(exc) from exc
    try:
        return service.simulate_rebalance(
            request=rebalance_request,
            idempotency_key=idempotency_key,
            correlation_id=x_correlation_id,
            policy_pack_id=x_policy_pack_id,
            tenant_default_policy_pack_id=x_tenant_policy_pack_id,
            tenant_id=x_tenant_id,
            source_context=source_context,
        )
    except service.DpmRebalanceSimulationError as exc:
        raise rebalance_simulation_http_exception(exc) from exc
