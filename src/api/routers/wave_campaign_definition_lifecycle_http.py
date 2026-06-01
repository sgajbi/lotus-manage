from __future__ import annotations

from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_lifecycle_http_exception,
    campaign_definition_not_found_http_exception,
    campaign_definition_value_http_exception,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionRetirementRequest,
    DpmBulkReviewCampaignDefinitionSupersessionRequest,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionRepository,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
    retire_bulk_review_campaign_definition,
    supersede_bulk_review_campaign_definition,
)


def retire_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionRetirementRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    try:
        retired = retire_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            retired_by=request.retired_by,
            retirement_reason=request.retirement_reason,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise campaign_definition_lifecycle_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if retired is None:
        raise campaign_definition_not_found_http_exception()
    return retired


def supersede_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionSupersessionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    try:
        superseded = supersede_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            replacement_version=request.superseded_by_campaign_version,
            superseded_by=request.superseded_by,
            supersession_reason=request.supersession_reason,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise campaign_definition_lifecycle_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if superseded is None:
        raise campaign_definition_not_found_http_exception()
    return superseded
