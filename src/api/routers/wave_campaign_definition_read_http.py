from __future__ import annotations

from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_not_found_http_exception,
)
from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignDefinitionPage
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionRepository,
)


def get_campaign_definition_or_404(
    *,
    repository: DpmBulkReviewCampaignDefinitionRepository,
    tenant_id: str,
    campaign_id: str,
    campaign_version: str,
) -> DpmBulkReviewCampaignDefinition:
    definition = repository.get_definition(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise campaign_definition_not_found_http_exception()
    return definition


def get_campaign_definition_response(
    *,
    tenant_id: str,
    campaign_id: str,
    campaign_version: str,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    return get_campaign_definition_or_404(
        repository=repository,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )


def list_campaign_definitions_response(
    *,
    tenant_id: str,
    campaign_id: str | None,
    campaign_status: str | None,
    as_of_date: str | None,
    limit: int,
    offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionPage:
    items = repository.list_definitions(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        status=campaign_status,
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
