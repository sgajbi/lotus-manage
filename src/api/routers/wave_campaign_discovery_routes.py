from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_read_model_query import load_campaign_read_model_query
from src.api.routers.wave_route_parameters import (
    CampaignActiveOnQuery,
    CampaignDefinitionAsOfDateQuery,
    CampaignDefinitionFilterIdQuery,
    CampaignDefinitionStatusQuery,
    CampaignIncludeExpiredQuery,
    CampaignReadModelLimitQuery,
    CampaignReadModelOffsetQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionRepository,
    DpmBulkReviewCampaignDiscoveryPage,
    build_bulk_review_campaign_discovery_item,
)

router = APIRouter()


@router.get(
    "/campaign-discovery",
    response_model=DpmBulkReviewCampaignDiscoveryPage,
    status_code=status.HTTP_200_OK,
    summary="Discover persisted bulk-review campaigns",
    description=(
        "Discovers persisted Manage-owned `BulkReviewCampaignDefinition:v1` records as a bounded "
        "front-office operating read model. This endpoint summarizes campaign identity, governance "
        "posture, expiry posture, source-ref count, and source-backed candidate counts. It does not "
        "discover the global portfolio universe, calculate source facts, run maker-checker workflow, "
        "or claim OMS execution. Each item includes `BulkReviewCampaignUniversePosture:v1` so the "
        "persisted-definition-only discovery mode, persisted-candidate source scope, unsupported "
        "global portfolio-universe boundary, required future "
        "`GlobalPortfolioUniverseCampaignCandidateSet:v1` source product, blocked global "
        "candidate-discovery capabilities, promotion requirements, and deterministic posture hash "
        "are machine-readable."
    ),
)
def discover_bulk_review_campaigns(
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = "ACTIVE",
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    active_on: CampaignActiveOnQuery = None,
    include_expired: CampaignIncludeExpiredQuery = False,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDiscoveryPage:
    campaign_query = load_campaign_read_model_query(
        repository=repository,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=active_on,
        limit=limit,
        offset=offset,
    )
    items = [
        build_bulk_review_campaign_discovery_item(
            definition=definition,
            active_on=campaign_query.active_on,
        )
        for definition in campaign_query.definitions
    ]
    if campaign_query.active_on is not None and not include_expired:
        items = [item for item in items if item.expiry_state != "EXPIRED"]
    return DpmBulkReviewCampaignDiscoveryPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
    )
