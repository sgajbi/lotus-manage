from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.api.dependencies import get_mandate_repository
from src.api.routers.mandate_models import (
    MANDATE_RESPONSE_EXAMPLE,
    DpmMandateRefreshFromCoreRequest,
    DpmMandateRefreshFromCoreResponse,
)
from src.api.services.mandate_service import (
    DpmMandateDiff,
    DpmMandateDiffUnavailableError,
    DpmMandateHealthNotFoundError,
    DpmMandateNotFoundError,
    DpmMandateSourceIncompleteError,
    DpmMandateSourceUnavailableError,
    diff_mandate_versions,
    get_latest_mandate,
    get_latest_mandate_health,
    get_latest_mandate_by_portfolio,
    list_mandate_versions,
    recalculate_mandate_health,
    refresh_mandate_from_core,
)
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateHealthSnapshot,
)
from src.infrastructure.core_sourcing import DpmCoreResolverClient


router = APIRouter(prefix="/mandates", tags=["lotus-manage Mandates"])


def get_core_resolver_client() -> DpmCoreResolverClient:
    return build_core_resolver_client()


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


@router.post(
    "/{mandate_id}/refresh-from-core",
    response_model=DpmMandateRefreshFromCoreResponse,
    summary="Refresh discretionary mandate from lotus-core",
    description=(
        "Use this endpoint when lotus-manage must source the latest mandate binding and model "
        "targets from lotus-core, compile the mandate digital twin, generate a health snapshot, "
        "persist the result, and return explicit source-data gap codes. This is the canonical "
        "state acquisition command for RFC-0038."
    ),
    responses={
        200: {
            "description": "Mandate digital twin refreshed, persisted, and assessed.",
            "content": {
                "application/json": {
                    "example": {
                        "contract_version": "DpmMandateRefreshFromCoreResponse:v1",
                        "refreshed_at": "2026-05-03T08:30:00Z",
                        "mandate": MANDATE_RESPONSE_EXAMPLE,
                        "health_snapshot": {
                            "health_snapshot_id": "mh_20260503_pb_sg_global_bal_001",
                            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                            "as_of_date": "2026-05-03",
                            "calculated_at": "2026-05-03T08:30:00Z",
                            "health_score": 97,
                            "health_state": "PENDING_REVIEW",
                            "dimension_scores": [],
                            "top_reasons": [],
                            "recommended_action": "SIMULATE_REBALANCE",
                            "source_readiness_state": "READY",
                            "evidence_refs": ["DiscretionaryMandateBinding:v1"],
                        },
                        "monitoring_exceptions": [],
                        "field_gap_codes": ["MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED"],
                    }
                }
            },
        },
        424: {"description": "Core returned incomplete mandate source products."},
        503: {"description": "Core mandate source products were unavailable."},
    },
)
async def refresh_mandate(
    mandate_id: str,
    request: DpmMandateRefreshFromCoreRequest,
    x_correlation_id: Annotated[
        Optional[str],
        Header(
            description="Optional trace/correlation identifier propagated to lotus-core calls.",
            examples=["corr-rfc0038-refresh-001"],
        ),
    ] = None,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
    core_resolver: DpmCoreResolverClient = Depends(get_core_resolver_client),
) -> DpmMandateRefreshFromCoreResponse:
    try:
        result = refresh_mandate_from_core(
            repository=repository,
            core_resolver=core_resolver,
            portfolio_id=request.portfolio_id,
            mandate_id=mandate_id,
            as_of_date=request.as_of_date,
            tenant_id=request.tenant_id,
            booking_center_code=request.booking_center_code,
            model_portfolio_id=request.model_portfolio_id,
            reference_currency=request.reference_currency,
            include_market_data_coverage=request.include_market_data_coverage,
            correlation_id=x_correlation_id,
        )
    except DpmMandateSourceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except DpmMandateSourceIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=str(exc),
        ) from exc
    return DpmMandateRefreshFromCoreResponse.from_result(result)


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
