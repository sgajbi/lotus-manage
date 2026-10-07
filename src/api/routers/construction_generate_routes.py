from __future__ import annotations

from src.api.dependencies import get_rebalance_runtime

from src.core.rebalance.runtime_ports import RebalanceRuntime

from typing import Annotated, Optional

from fastapi import Depends, Header, status

from src.api.dependencies import (
    get_construction_repository,
    get_db_session,
    get_risk_authority_client,
    get_risk_authority_context,
)
from src.api.routers.construction import router
from src.api.routers.construction_models import (
    CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE,
    ConstructionAlternativeSetGenerateRequest,
)
from src.api.routers.construction_http import construction_http_exception
from src.api.routers.mandate_tenant_query import require_mandate_tenant
from src.api.routers.rebalance_simulation_http import rebalance_envelope_http_exception
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import construction_service
from src.api.services import rebalance_simulation_service
from src.core.integration_ports import RiskAuthorityClient
from src.core.construction.models import ConstructionAlternativeSet
from src.core.construction.repository import (
    ConstructionIdempotencyConflictError,
    ConstructionRepository,
)
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.risk_authority.context import RiskAuthorityContext


@router.post(
    "/generate",
    response_model=ConstructionAlternativeSet,
    status_code=status.HTTP_200_OK,
    summary="Generate portfolio construction alternatives",
    description=(
        "Generates an auditable set of discretionary portfolio construction alternatives for a "
        "single mandate context. Use this endpoint when a PM, command center, or governed workflow "
        "needs a no-action baseline plus comparable rebalance alternatives before selecting a "
        "preferred implementation path. Required header: `Idempotency-Key`. Protected Risk "
        "enrichment additionally requires admitted caller context and an explicit local/dev "
        "operation-capability policy; missing authority remains non-ready. This pilot is not "
        "verified production identity."
    ),
    responses={
        200: {
            "description": "Construction alternatives generated or replayed idempotently.",
            "content": {"application/json": {"example": CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE}},
        },
        409: {"description": "Idempotency key conflict for a different request hash."},
        424: {"description": "Stateful core source context was incomplete."},
        503: {"description": "Stateful core source resolver was unavailable."},
    },
)
def generate_alternative_set(
    runtime: Annotated[RebalanceRuntime, Depends(get_rebalance_runtime)],
    request: ConstructionAlternativeSetGenerateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            description="Required idempotency token for alternative-set replay.",
            examples=["construction-idem-001"],
        ),
    ],
    x_tenant_id: Annotated[
        str,
        Header(
            min_length=1,
            pattern=r"\S",
            description=(
                "Required caller-asserted tenant for construction run ownership; stateful "
                "requests must also match stateful_input.tenant_id. This is not production "
                "identity-provider proof."
            ),
            examples=["tenant_001"],
        ),
    ],
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional trace/correlation identifier propagated to source resolution.",
            examples=["corr-construction-001"],
        ),
    ] = None,
    repository: ConstructionRepository = Depends(get_construction_repository),
    risk_authority_client: RiskAuthorityClient | None = Depends(get_risk_authority_client),
    risk_authority_context: RiskAuthorityContext | None = Depends(get_risk_authority_context),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    _db: Annotated[None, Depends(get_db_session)] = None,
) -> ConstructionAlternativeSet:
    admitted_tenant_id = require_mandate_tenant(x_tenant_id)
    try:
        (
            rebalance_request,
            source_context,
        ) = rebalance_simulation_service.resolve_rebalance_request_envelope(
            runtime=runtime,
            envelope=request.to_execution_envelope(),
            correlation_id=x_correlation_id,
            admitted_tenant_id=admitted_tenant_id,
        )
    except rebalance_simulation_service.DpmRebalanceEnvelopeError as exc:
        raise rebalance_envelope_http_exception(exc) from exc
    try:
        return construction_service.generate_construction_alternative_set(
            request=rebalance_request,
            idempotency_key=idempotency_key,
            correlation_id=x_correlation_id,
            repository=repository,
            methods=request.methods,
            source_context=source_context,
            authority_context=request.authority_context,
            risk_authority_client=risk_authority_client,
            run_service=run_service,
            admitted_tenant_id=admitted_tenant_id,
            risk_authority_context=risk_authority_context,
        )
    except ConstructionIdempotencyConflictError as exc:
        raise construction_http_exception(exc) from exc
