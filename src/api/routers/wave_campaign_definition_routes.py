from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_wave_campaign_application_service
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_not_found_http_exception,
    campaign_definition_value_http_exception,
)
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionPage,
    DpmBulkReviewCampaignDefinitionRequest,
)
from src.api.services.wave_campaign_application import (
    DpmCampaignDefinitionCreateCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionAsOfDateQuery,
    CampaignDefinitionFilterIdQuery,
    CampaignDefinitionIdPath,
    CampaignDefinitionStatusQuery,
    CampaignDefinitionVersionPath,
    CampaignReadModelLimitQuery,
    CampaignReadModelOffsetQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])
detail_router = APIRouter()


@router.put(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Persist bulk-review campaign definition",
    description=(
        "Persists an immutable Manage-owned `BulkReviewCampaignDefinition:v1` over a bounded, "
        "source-backed candidate portfolio set. This endpoint does not discover the global book, "
        "own source facts, run maker-checker workflow, expose downstream UI, or claim OMS "
        "execution."
    ),
)
def put_bulk_review_campaign_definition(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionRequest,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        return application_service.create_campaign_definition(
            command=DpmCampaignDefinitionCreateCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
                display_name=request.display_name,
                status=request.status,
                as_of_date=request.as_of_date,
                rationale=request.rationale,
                eligible_portfolio_types=request.eligible_portfolio_types,
                candidates=request.candidates,
                governance=request.governance,
                source_refs=request.source_refs,
                created_by=request.created_by,
                correlation_id=request.correlation_id,
            )
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc


@router.get(
    "/campaign-definitions",
    response_model=DpmBulkReviewCampaignDefinitionPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign definitions",
    description="Lists immutable Manage-owned bulk-review campaign definitions.",
)
def list_bulk_review_campaign_definitions(
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = None,
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinitionPage:
    items = application_service.list_campaign_definitions(
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return DpmBulkReviewCampaignDefinitionPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
    )


@detail_router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Get bulk-review campaign definition",
    description="Retrieves one immutable Manage-owned bulk-review campaign definition.",
)
def get_bulk_review_campaign_definition(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        return application_service.get_campaign_definition(
            tenant_id=trusted_context.tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
        )
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_definition_not_found_http_exception() from exc
