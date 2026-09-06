from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import Depends, Query

from src.api.dependencies import get_mandate_repository
from src.api.routers.mandate_http import (
    mandate_diff_unavailable_http_exception,
    read_mandate_with_not_found_http_mapping,
)
from src.api.routers.mandate_models import MANDATE_RESPONSE_EXAMPLE
from src.api.routers.mandates import router
from src.api.services.mandate_service import (
    DpmMandateDiff,
    DpmMandateDiffUnavailableError,
    diff_mandate_versions,
    get_latest_mandate,
    list_mandate_versions,
)
from src.api.services.mandate_temporal_reads import get_mandate_by_portfolio
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMandateDigitalTwin
from src.api.routers.mandate_tenant_query import MandateTenantId


@router.get(
    "/by-portfolio/{portfolio_id}",
    response_model=DpmMandateDigitalTwin,
    summary="Get discretionary mandate for a portfolio",
    description=(
        "Use this endpoint when a DPM command center or historical portfolio review needs the "
        "lotus-manage mandate digital twin that applied to a core-governed portfolio. When "
        "as_of_date is supplied, Manage returns the latest persisted twin whose source-owned "
        "business date is on or before the request and preserves that actual business date. "
        "When omitted, the endpoint remains a latest-state read."
    ),
    responses={
        200: {
            "description": "Resolved discretionary mandate digital twin for the portfolio.",
            "content": {"application/json": {"example": MANDATE_RESPONSE_EXAMPLE}},
        },
        404: {"description": "No mandate digital twin has been refreshed for this portfolio."},
    },
)
async def read_mandate_by_portfolio(
    portfolio_id: str,
    tenant_id: MandateTenantId,
    as_of_date: date | None = Query(
        default=None,
        description=(
            "Optional business date used to resolve the latest persisted mandate twin on or "
            "before that date. The response keeps the source twin's actual as_of_date."
        ),
        examples=["2026-04-10"],
    ),
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMandateDigitalTwin:
    return read_mandate_with_not_found_http_mapping(
        lambda: get_mandate_by_portfolio(
            repository=repository,
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            tenant_id=tenant_id,
        )
    )


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
    tenant_id: MandateTenantId,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMandateDigitalTwin:
    return read_mandate_with_not_found_http_mapping(
        lambda: get_latest_mandate(
            repository=repository, mandate_id=mandate_id, tenant_id=tenant_id
        )
    )


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
    tenant_id: MandateTenantId,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> list[DpmMandateDigitalTwin]:
    return read_mandate_with_not_found_http_mapping(
        lambda: list_mandate_versions(
            repository=repository, mandate_id=mandate_id, tenant_id=tenant_id
        )
    )


@router.get(
    "/{mandate_id}/diff",
    response_model=DpmMandateDiff,
    summary="Diff discretionary mandate versions",
    description=(
        "Use this endpoint when portfolio managers, supervision, or operations need to explain "
        "what changed between two mandate versions. If versions are omitted, lotus-manage "
        "compares the latest two distinct versions, using the most recent observation of each. "
        "Repeated observations of one version are not a change, so a history holding only a "
        "single distinct version is refused with 409 rather than diffed against itself. The "
        "response carries the business date of each compared observation."
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
                        "from_as_of_date": "2026-04-10",
                        "to_as_of_date": "2026-05-03",
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
    tenant_id: MandateTenantId,
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
        return read_mandate_with_not_found_http_mapping(
            lambda: diff_mandate_versions(
                repository=repository,
                mandate_id=mandate_id,
                from_version=from_version,
                to_version=to_version,
                tenant_id=tenant_id,
            )
        )
    except DpmMandateDiffUnavailableError as exc:
        raise mandate_diff_unavailable_http_exception(exc) from exc
