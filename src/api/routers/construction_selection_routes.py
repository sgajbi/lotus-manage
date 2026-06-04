from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, Path, status

from src.api.dependencies import get_construction_repository
from src.api.routers.construction import router
from src.api.routers.construction_http import construction_http_exception
from src.api.routers.construction_models import ConstructionAlternativeSelectionRequest
from src.api.services import construction_service
from src.core.construction.models import ConstructionAlternativeSelection
from src.core.construction.repository import (
    ConstructionAlternativeNotFoundError,
    ConstructionAlternativeSetNotFoundError,
    ConstructionRepository,
)

_CONSTRUCTION_SELECTION_ROUTE_ERRORS = (
    ConstructionAlternativeNotFoundError,
    ConstructionAlternativeSetNotFoundError,
)


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
    except _CONSTRUCTION_SELECTION_ROUTE_ERRORS as exc:
        raise construction_http_exception(exc) from exc
