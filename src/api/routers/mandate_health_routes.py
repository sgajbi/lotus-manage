from __future__ import annotations

from fastapi import Depends, HTTPException, status

from src.api.dependencies import get_mandate_repository
from src.api.routers.mandates import router
from src.api.services.mandate_service import (
    DpmMandateHealthNotFoundError,
    DpmMandateSourceIncompleteError,
    get_latest_mandate_health,
    recalculate_mandate_health,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMandateHealthInput, DpmMandateHealthSnapshot


@router.get(
    "/{mandate_id}/health",
    response_model=DpmMandateHealthSnapshot,
    summary="Get latest discretionary mandate health snapshot",
    description=(
        "Use this endpoint when a PM, operator, or command-center surface needs the latest "
        "persisted health state for a mandate, including dimension scores, top reasons, source "
        "readiness, and recommended action."
    ),
    responses={
        200: {"description": "Latest mandate health snapshot."},
        404: {"description": "No health snapshot exists for this mandate id."},
    },
)
async def read_mandate_health(
    mandate_id: str,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMandateHealthSnapshot:
    try:
        return get_latest_mandate_health(repository=repository, mandate_id=mandate_id)
    except DpmMandateHealthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{mandate_id}/health/recalculate",
    response_model=DpmMandateHealthSnapshot,
    summary="Recalculate discretionary mandate health",
    description=(
        "Use this endpoint to recalculate and persist mandate health from an explicit health "
        "input. This is primarily for certification, operations, and later command-center "
        "orchestration where the caller has already resolved the source-backed mandate twin and "
        "current monitoring measurements."
    ),
    responses={
        200: {"description": "Recalculated and persisted mandate health snapshot."},
        424: {"description": "Health input did not match the mandate id or was incomplete."},
    },
)
async def recalculate_health(
    mandate_id: str,
    request: DpmMandateHealthInput,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMandateHealthSnapshot:
    try:
        return recalculate_mandate_health(
            repository=repository,
            mandate_id=mandate_id,
            health_input=request,
        )
    except DpmMandateSourceIncompleteError as exc:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc)) from exc
