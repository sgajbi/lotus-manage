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
    record_campaign_workflow_readiness,
    record_campaign_workflow_unexpected_error,
)
from src.api.services.wave_campaign_application import (
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignLaunchActorIdOptionalQuery,
    CampaignLaunchRequestedAsOfDateQuery,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness",
    response_model=DpmBulkReviewCampaignDefinitionPreviewReadiness,
    status_code=status.HTTP_200_OK,
    summary="Check bulk-review campaign definition preview readiness",
    description=(
        "Evaluates whether one persisted Manage-owned `BulkReviewCampaignDefinition:v1` can be "
        "used for new `BULK_REVIEW_CAMPAIGN` preview/create. The response is a bounded "
        "fail-closed supportability check over lifecycle status, as-of date, source-backed "
        "candidate eligibility, approval evidence, expiry, and optional actor entitlement. It "
        "does not create a wave, discover the global portfolio universe, recalculate membership, "
        "run maker-checker workflow, approve trades, or claim OMS execution."
    ),
)
def get_bulk_review_campaign_definition_preview_readiness(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    requested_as_of_date: CampaignLaunchRequestedAsOfDateQuery,
    actor_id: CampaignLaunchActorIdOptionalQuery = None,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinitionPreviewReadiness:
    surface = "preview_readiness"
    try:
        readiness = application_service.get_campaign_definition_preview_readiness(
            tenant_id=trusted_context.tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            requested_as_of_date=requested_as_of_date,
            actor_id=actor_id,
        )
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_workflow_http_exception(
            surface=surface,
            exc=campaign_definition_not_found_http_exception(),
        ) from exc
    except Exception:
        record_campaign_workflow_unexpected_error(surface=surface)
        raise
    record_campaign_workflow_readiness(
        surface=surface,
        blocked=readiness.supportability_state == "BLOCKED",
    )
    return readiness
