from __future__ import annotations

from datetime import date

from fastapi import Depends, Query

from src.api.dependencies import get_mandate_repository
from src.api.routers.mandate_http import (
    mandate_source_incomplete_http_exception,
    read_mandate_with_not_found_http_mapping,
)
from src.api.routers.mandates import router
from src.api.services.mandate_service import (
    DpmMandateSourceIncompleteError,
    recalculate_mandate_health,
)
from src.api.services.mandate_temporal_reads import get_mandate_health
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMandateHealthInput, DpmMandateHealthSnapshot


@router.get(
    "/{mandate_id}/health",
    response_model=DpmMandateHealthSnapshot,
    summary="Get discretionary mandate health snapshot",
    description=(
        "Use this endpoint when a PM, operator, or historical review needs a persisted health "
        "state for a mandate. When as_of_date is supplied, Manage returns the latest snapshot "
        "whose source-owned business date is on or before the request and preserves the actual "
        "snapshot date. When omitted, the endpoint remains a latest-state read."
    ),
    responses={
        200: {"description": "Resolved mandate health snapshot."},
        404: {"description": "No health snapshot exists for this mandate id."},
    },
)
async def read_mandate_health(
    mandate_id: str,
    as_of_date: date | None = Query(
        default=None,
        description=(
            "Optional business date used to resolve the latest persisted health snapshot on or "
            "before that date. The response keeps the snapshot's actual as_of_date."
        ),
        examples=["2026-04-10"],
    ),
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMandateHealthSnapshot:
    return read_mandate_with_not_found_http_mapping(
        lambda: get_mandate_health(
            repository=repository,
            mandate_id=mandate_id,
            as_of_date=as_of_date,
        )
    )


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
        raise mandate_source_incomplete_http_exception(exc) from exc
