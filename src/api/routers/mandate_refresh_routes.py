from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header

from src.api.dependencies import get_mandate_repository
from src.api.routers.mandate_http import (
    mandate_source_incomplete_http_exception,
    mandate_source_unavailable_http_exception,
)
from src.api.routers.mandate_models import (
    MANDATE_RESPONSE_EXAMPLE,
    DpmMandateRefreshFromCoreRequest,
    DpmMandateRefreshFromCoreResponse,
)
from src.api.routers.mandates import get_core_resolver_client, router
from src.api.services.core_resolver_service import CoreResolverClient
from src.api.services.mandate_service import (
    DpmMandateSourceIncompleteError,
    DpmMandateSourceUnavailableError,
    refresh_mandate_from_core,
)
from src.core.mandate_repository import DpmMandateRepository


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
    core_resolver: CoreResolverClient = Depends(get_core_resolver_client),
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
        raise mandate_source_unavailable_http_exception(exc) from exc
    except DpmMandateSourceIncompleteError as exc:
        raise mandate_source_incomplete_http_exception(exc) from exc
    return DpmMandateRefreshFromCoreResponse.from_result(result)
