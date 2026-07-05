from __future__ import annotations

from src.api.routers.wave_campaign_action_common import persisted_definition_or_404
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_evidence_value_http_exception,
)
from src.api.routers.wave_campaign_definition_read_http import get_campaign_definition_or_404
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_assignment_action_page,
    record_bulk_review_campaign_definition_assignment_action,
)


def record_campaign_definition_assignment_action_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = record_bulk_review_campaign_definition_assignment_action(
            definition=definition,
            action_type=request.action_type,
            action_ref=request.action_ref,
            recorded_by=request.recorded_by,
            action_reason=request.action_reason,
            assigned_actor_ids=request.assigned_actor_ids,
            escalation_tier=request.escalation_tier,
            sla_posture=request.sla_posture,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_assignment_action(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_evidence_value_http_exception(exc) from exc
    return persisted_definition_or_404(persisted)


def list_campaign_definition_assignment_actions_response(
    *,
    campaign_id: str,
    campaign_version: str,
    limit: int,
    offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_assignment_action_page(
        definition=definition,
        limit=limit,
        offset=offset,
    )
