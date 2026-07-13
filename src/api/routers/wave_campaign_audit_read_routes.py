from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_wave_campaign_application_service
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_not_found_http_exception,
)
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_campaign_workflow_telemetry import (
    campaign_workflow_http_exception,
    record_campaign_workflow_success,
    record_campaign_workflow_unexpected_error,
)
from src.api.services.wave_campaign_application import (
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignEvidenceLimitQuery,
    CampaignEvidenceOffsetQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
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
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinitionLifecycleEventPage:
    try:
        return application_service.list_campaign_definition_lifecycle_events(
            tenant_id=trusted_context.tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
        )
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_definition_not_found_http_exception() from exc


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
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinitionLaunchHistoryPage:
    surface = "launch_history"
    try:
        page = application_service.list_campaign_definition_launch_history(
            tenant_id=trusted_context.tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            limit=limit,
            offset=offset,
        )
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_workflow_http_exception(
            surface=surface,
            exc=campaign_definition_not_found_http_exception(),
        ) from exc
    except Exception:
        record_campaign_workflow_unexpected_error(surface=surface)
        raise
    record_campaign_workflow_success(surface=surface)
    return page
