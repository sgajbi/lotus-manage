from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_definition_read_http import (
    get_campaign_definition_response,
    list_campaign_definitions_response,
)
from src.api.routers.wave_campaign_definition_lifecycle_http import (
    retire_campaign_definition_response,
    supersede_campaign_definition_response,
)
from src.api.routers.wave_campaign_definition_write_http import (
    put_campaign_definition_response,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionPage,
    DpmBulkReviewCampaignDefinitionRequest,
    DpmBulkReviewCampaignDefinitionRetirementRequest,
    DpmBulkReviewCampaignDefinitionSupersessionRequest,
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
    DpmBulkReviewCampaignDefinitionRepository,
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
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return put_campaign_definition_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


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
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionPage:
    return list_campaign_definitions_response(
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
        repository=repository,
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/retire",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Retire bulk-review campaign definition",
    description=(
        "Retires a persisted Manage-owned `BulkReviewCampaignDefinition:v1` so it remains "
        "auditable but can no longer be used for new `BULK_REVIEW_CAMPAIGN` preview/create "
        "requests. This lifecycle action does not change the source-backed candidate set, "
        "discover a global portfolio universe, run maker-checker workflow, or claim OMS execution."
    ),
)
def retire_bulk_review_campaign_definition(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionRetirementRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return retire_campaign_definition_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Supersede bulk-review campaign definition",
    description=(
        "Supersedes a persisted Manage-owned `BulkReviewCampaignDefinition:v1` with an already "
        "persisted ACTIVE replacement version for the same campaign id. Superseded definitions "
        "remain auditable but cannot be used for new `BULK_REVIEW_CAMPAIGN` preview/create "
        "requests. This lifecycle action does not discover the global portfolio universe, "
        "recalculate source facts, run maker-checker workflow, or claim OMS execution."
    ),
)
def supersede_bulk_review_campaign_definition(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionSupersessionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return supersede_campaign_definition_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
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
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return get_campaign_definition_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        repository=repository,
    )
