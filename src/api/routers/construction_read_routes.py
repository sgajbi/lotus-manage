from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Path

from src.api.dependencies import get_construction_repository
from src.api.routers.construction import router
from src.api.routers.construction_models import CONSTRUCTION_ALTERNATIVE_SET_EXAMPLE
from src.api.services import construction_service
from src.core.construction.models import ConstructionAlternativeSet
from src.core.construction.repository import ConstructionRepository


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
