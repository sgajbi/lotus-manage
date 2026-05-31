from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from src.api.dependencies import (
    get_construction_repository,
    get_db_session,
    get_risk_authority_client,
)
from src.api.routers.construction_models import (
    CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE,
    ConstructionAlternativeSelectionRequest,
    ConstructionAlternativeSetGenerateRequest,
)
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import construction_service
from src.api.services.rebalance_simulation_service import resolve_rebalance_request_envelope
from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import ConstructionRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.infrastructure.risk_authority import LotusRiskAuthorityClient


router = APIRouter(
    prefix="/construction/alternative-sets",
    tags=["lotus-manage Construction Alternatives"],
)


@router.post(
    "/generate",
    response_model=ConstructionAlternativeSet,
    status_code=status.HTTP_200_OK,
    summary="Generate portfolio construction alternatives",
    description=(
        "Generates an auditable set of discretionary portfolio construction alternatives for a "
        "single mandate context. Use this endpoint when a PM, command center, or governed workflow "
        "needs a no-action baseline plus comparable rebalance alternatives before selecting a "
        "preferred implementation path. Required header: `Idempotency-Key`."
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
    request: ConstructionAlternativeSetGenerateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            description="Required idempotency token for alternative-set replay.",
            examples=["construction-idem-001"],
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
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    db: Annotated[None, Depends(get_db_session)] = None,
) -> ConstructionAlternativeSet:
    rebalance_request, source_context = resolve_rebalance_request_envelope(
        envelope=request.to_execution_envelope(),
        correlation_id=x_correlation_id,
    )
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
        )
    except Exception as exc:
        raise construction_service.to_api_http_exception(exc) from exc


@router.get(
    "/{alternative_set_id}",
    response_model=ConstructionAlternativeSet,
    summary="Get a construction alternative set",
    description=(
        "Returns a previously generated construction alternative set by identifier. Use this "
        "read model for audit, replay, command-center comparison, and downstream presentation "
        "without recomputing portfolio construction results."
    ),
    responses={
        200: {
            "description": "Construction alternative set.",
            "content": {"application/json": {"example": CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE}},
        },
        404: {"description": "Alternative set was not found."},
    },
)
def read_alternative_set(
    alternative_set_id: Annotated[
        str,
        Path(description="Construction alternative set identifier.", examples=["cas_001"]),
    ],
    repository: ConstructionRepository = Depends(get_construction_repository),
) -> ConstructionAlternativeSet:
    try:
        return construction_service.get_construction_alternative_set(
            repository=repository,
            alternative_set_id=alternative_set_id,
        )
    except Exception as exc:
        raise construction_service.to_api_http_exception(exc) from exc


@router.post(
    "/{alternative_set_id}/selections",
    response_model=ConstructionAlternativeSelection,
    status_code=status.HTTP_200_OK,
    summary="Select a construction alternative",
    description=(
        "Records the selected construction alternative for an alternative set. Use this endpoint "
        "after a PM, supervisor, or orchestration workflow chooses the preferred rebalance path. "
        "The selection is persisted as an auditable decision, not executed as an order."
    ),
    responses={
        200: {"description": "Selection recorded."},
        404: {"description": "Alternative set or alternative id was not found."},
    },
)
def select_alternative(
    alternative_set_id: Annotated[
        str,
        Path(description="Construction alternative set identifier.", examples=["cas_001"]),
    ],
    request: ConstructionAlternativeSelectionRequest,
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional trace/correlation identifier for the selection decision.",
            examples=["corr-selection-001"],
        ),
    ] = None,
    repository: ConstructionRepository = Depends(get_construction_repository),
) -> ConstructionAlternativeSelection:
    try:
        return construction_service.select_construction_alternative(
            repository=repository,
            alternative_set_id=alternative_set_id,
            alternative_id=request.alternative_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id,
        )
    except Exception as exc:
        http_exc = construction_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc
