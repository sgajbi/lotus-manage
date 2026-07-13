from __future__ import annotations

from fastapi import HTTPException

from src.api.routers.wave_campaign_definition_read_http import get_campaign_definition_or_404
from src.api.routers.wave_campaign_workflow_telemetry import (
    campaign_workflow_http_exception,
    record_campaign_workflow_readiness,
    record_campaign_workflow_unexpected_error,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_launch_package,
)


def get_campaign_definition_launch_package_response(
    *,
    tenant_id: str,
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str,
    actor_id: str,
    correlation_id: str | None,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionLaunchPackage:
    surface = "launch_package"
    try:
        definition = get_campaign_definition_or_404(
            repository=repository,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
        )
        package = build_bulk_review_campaign_definition_launch_package(
            definition=definition,
            requested_as_of_date=requested_as_of_date,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )
    except HTTPException as exc:
        raise campaign_workflow_http_exception(surface=surface, exc=exc) from exc
    except Exception:
        record_campaign_workflow_unexpected_error(surface=surface)
        raise
    record_campaign_workflow_readiness(
        surface=surface,
        blocked=package.launch_state == "BLOCKED",
    )
    return package
