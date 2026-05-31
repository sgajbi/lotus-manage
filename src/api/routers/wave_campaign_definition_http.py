from __future__ import annotations

from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_launch_blocked_http_exception as campaign_definition_launch_blocked_http_exception,
    campaign_definition_not_found_http_exception,
    campaign_definition_value_http_exception,
    invalid_campaign_discovery_date_http_exception as invalid_campaign_discovery_date_http_exception,
    parse_optional_campaign_discovery_date as parse_optional_campaign_discovery_date,
)
from src.api.routers.wave_campaign_definition_lifecycle_http import (
    retire_campaign_definition_response as retire_campaign_definition_response,
    supersede_campaign_definition_response as supersede_campaign_definition_response,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionPage,
    DpmBulkReviewCampaignDefinitionRequest,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionRepository,
)


def get_campaign_definition_or_404(
    *,
    repository: DpmBulkReviewCampaignDefinitionRepository,
    campaign_id: str,
    campaign_version: str,
) -> DpmBulkReviewCampaignDefinition:
    definition = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise campaign_definition_not_found_http_exception()
    return definition


def get_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    return get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )


def put_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    try:
        definition = DpmBulkReviewCampaignDefinition(
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
        repository.save_definition(definition=definition)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    return definition


def list_campaign_definitions_response(
    *,
    campaign_id: str | None,
    campaign_status: str | None,
    as_of_date: str | None,
    limit: int,
    offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionPage:
    items = repository.list_definitions(
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
