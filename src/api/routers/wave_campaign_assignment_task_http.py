from __future__ import annotations

from src.api.routers.wave_campaign_action_common import persisted_definition_or_404
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_value_http_exception,
)
from src.api.routers.wave_campaign_definition_http import get_campaign_definition_or_404
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
)
from src.core.waves import (
    CampaignAssignmentTaskStatus,
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_assignment_task_page,
    open_bulk_review_campaign_definition_assignment_task,
    transition_bulk_review_campaign_definition_assignment_task,
)


def open_campaign_definition_assignment_task_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = open_bulk_review_campaign_definition_assignment_task(
            definition=definition,
            task_ref=request.task_ref,
            task_type=request.task_type,
            opened_by=request.opened_by,
            task_reason=request.task_reason,
            assigned_actor_ids=request.assigned_actor_ids,
            escalation_tier=request.escalation_tier,
            sla_posture=request.sla_posture,
            due_at=request.due_at,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_assignment_task(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    return persisted_definition_or_404(persisted)


def transition_campaign_definition_assignment_task_response(
    *,
    campaign_id: str,
    campaign_version: str,
    task_ref: str,
    request: DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = transition_bulk_review_campaign_definition_assignment_task(
            definition=definition,
            task_ref=task_ref,
            transition_type=request.transition_type,
            transition_ref=request.transition_ref,
            transitioned_by=request.transitioned_by,
            transition_reason=request.transition_reason,
            assigned_actor_ids=request.assigned_actor_ids,
            escalation_tier=request.escalation_tier,
            sla_posture=request.sla_posture,
            due_at=request.due_at,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_assignment_task(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    return persisted_definition_or_404(persisted)


def list_campaign_definition_assignment_tasks_response(
    *,
    campaign_id: str,
    campaign_version: str,
    status: CampaignAssignmentTaskStatus | None,
    limit: int,
    offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionAssignmentTaskPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_assignment_task_page(
        definition=definition,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
