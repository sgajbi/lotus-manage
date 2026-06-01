from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_audit_read_http import (
    list_campaign_definition_launch_history_response,
    list_campaign_definition_lifecycle_events_response,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignEvidenceLimitQuery,
    CampaignEvidenceOffsetQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    DpmBulkReviewCampaignDefinitionRepository,
)
from src.core.waves.campaign_definition_events import (
    DpmBulkReviewCampaignDefinitionLifecycleEventPage,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/lifecycle-events",
    response_model=DpmBulkReviewCampaignDefinitionLifecycleEventPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign definition lifecycle events",
    description=(
        "Projects bounded lifecycle events for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. Events are derived from the immutable definition "
        "record and show create, retire, and supersede posture without discovering the global "
        "portfolio universe, recalculating campaign membership, running maker-checker workflow, "
        "or claiming OMS execution."
    ),
)
def list_bulk_review_campaign_definition_lifecycle_events(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLifecycleEventPage:
    return list_campaign_definition_lifecycle_events_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        repository=repository,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-history",
    response_model=DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign definition launch history",
    description=(
        "Returns a bounded append-only launch audit page for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The records identify durable waves launched from "
        "the definition and preserve actor, requested as-of date, correlation, and idempotency "
        "evidence. They do not imply maker-checker workflow, trade approval, order generation, "
        "routing, fills, settlement, or OMS execution."
    ),
)
def list_bulk_review_campaign_definition_launch_history(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLaunchHistoryPage:
    return list_campaign_definition_launch_history_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        limit=limit,
        offset=offset,
        repository=repository,
    )
