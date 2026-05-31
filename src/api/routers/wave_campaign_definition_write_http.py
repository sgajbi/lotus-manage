from __future__ import annotations

from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_value_http_exception,
)
from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignDefinitionRequest
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionRepository,
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
