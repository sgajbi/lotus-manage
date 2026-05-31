from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query, status

from src.api.dependencies import get_mandate_repository
from src.api.routers.mandate_models import MANDATE_RESPONSE_EXAMPLE
from src.api.routers.mandates import router
from src.api.services.mandate_service import (
    DpmMandateDiff,
    DpmMandateDiffUnavailableError,
    DpmMandateNotFoundError,
    diff_mandate_versions,
    get_latest_mandate,
    get_latest_mandate_by_portfolio,
    list_mandate_versions,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMandateDigitalTwin


def _not_found(exc: DpmMandateNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/by-portfolio/{portfolio_id}",
    response_model=DpmMandateDigitalTwin,
    summary="Get latest discretionary mandate for a portfolio",
    description=(
        "Use this endpoint when a DPM command center or operations surface needs the latest "
        "lotus-manage mandate digital twin for a core-governed portfolio. The response is "
        "read-only state previously refreshed from lotus-core source products."
    ),
    responses={
        200: {
            "description": "Latest discretionary mandate digital twin for the portfolio.",
            "content": {"application/json": {"example": MANDATE_RESPONSE_EXAMPLE}},
        },
        404: {"description": "No mandate digital twin has been refreshed for this portfolio."},
    },
)
async def read_mandate_by_portfolio(
    portfolio_id: str,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMandateDigitalTwin:
    try:
        return get_latest_mandate_by_portfolio(repository=repository, portfolio_id=portfolio_id)
    except DpmMandateNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/{mandate_id}",
    response_model=DpmMandateDigitalTwin,
    summary="Get latest discretionary mandate",
    description=(
        "Use this endpoint to read the latest persisted mandate digital twin by mandate id. "
        "Call `POST /api/v1/mandates/{mandate_id}/refresh-from-core` first when lotus-manage "
        "must source fresh mandate state from lotus-core."
    ),
    responses={
        200: {
            "description": "Latest discretionary mandate digital twin.",
            "content": {"application/json": {"example": MANDATE_RESPONSE_EXAMPLE}},
        },
        404: {"description": "No mandate digital twin exists for this mandate id."},
    },
)
async def read_mandate(
    mandate_id: str,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMandateDigitalTwin:
    try:
        return get_latest_mandate(repository=repository, mandate_id=mandate_id)
    except DpmMandateNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/{mandate_id}/versions",
    response_model=list[DpmMandateDigitalTwin],
    summary="List discretionary mandate versions",
    description=(
        "Use this endpoint for audit, operations, and portfolio-manager review of mandate "
        "version history. Versions are returned newest first and are sourced from the "
        "lotus-manage mandate repository."
    ),
    responses={
        200: {
            "description": "Mandate digital-twin versions, newest first.",
            "content": {"application/json": {"example": [MANDATE_RESPONSE_EXAMPLE]}},
        },
        404: {"description": "No versions exist for this mandate id."},
    },
)
async def read_mandate_versions(
    mandate_id: str,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> list[DpmMandateDigitalTwin]:
    try:
        return list_mandate_versions(repository=repository, mandate_id=mandate_id)
    except DpmMandateNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/{mandate_id}/diff",
    response_model=DpmMandateDiff,
    summary="Diff discretionary mandate versions",
    description=(
        "Use this endpoint when portfolio managers, supervision, or operations need to explain "
        "what changed between two mandate versions. If versions are omitted, lotus-manage "
        "compares the latest two persisted versions."
    ),
    responses={
        200: {
            "description": "Deterministic mandate version diff.",
            "content": {
                "application/json": {
                    "example": {
                        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                        "compared_at": "2026-05-03T08:30:00Z",
                        "from_version": "2",
                        "to_version": "3",
                        "changed_fields": [
                            {
                                "field_path": "constraints.turnover_budget",
                                "previous_value": "0.1000000000",
                                "current_value": "0.1500000000",
                                "materiality": "HIGH",
                            }
                        ],
                    }
                }
            },
        },
        404: {"description": "No mandate digital twin exists for this mandate id."},
        409: {"description": "Two comparable mandate versions were not available."},
    },
)
async def read_mandate_diff(
    mandate_id: str,
    from_version: Optional[str] = Query(
        default=None,
        description="Optional older version to compare. Must be supplied with `to_version`.",
        examples=["2"],
    ),
    to_version: Optional[str] = Query(
        default=None,
        description="Optional newer version to compare. Must be supplied with `from_version`.",
        examples=["3"],
    ),
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMandateDiff:
    try:
        return diff_mandate_versions(
            repository=repository,
            mandate_id=mandate_id,
            from_version=from_version,
            to_version=to_version,
        )
    except DpmMandateNotFoundError as exc:
        raise _not_found(exc) from exc
    except DpmMandateDiffUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
