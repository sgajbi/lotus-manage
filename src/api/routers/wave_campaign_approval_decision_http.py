from __future__ import annotations

from src.api.routers.wave_campaign_action_common import persisted_definition_or_404
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_value_http_exception,
)
from src.api.routers.wave_campaign_definition_http import get_campaign_definition_or_404
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_approval_decision_page,
    record_bulk_review_campaign_definition_approval_decision,
)


def record_campaign_definition_approval_decision_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = record_bulk_review_campaign_definition_approval_decision(
            definition=definition,
            decision_type=request.decision_type,
            decision_ref=request.decision_ref,
            decided_by=request.decided_by,
            decision_reason=request.decision_reason,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_approval_decision(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    return persisted_definition_or_404(persisted)


def list_campaign_definition_approval_decisions_response(
    *,
    campaign_id: str,
    campaign_version: str,
    limit: int,
    offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionApprovalDecisionPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_approval_decision_page(
        definition=definition,
        limit=limit,
        offset=offset,
    )
