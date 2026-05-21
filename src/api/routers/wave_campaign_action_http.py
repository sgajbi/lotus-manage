from __future__ import annotations

from src.api.routers.wave_campaign_definition_http import (
    campaign_definition_conflict_http_exception,
    campaign_definition_not_found_http_exception,
    campaign_definition_value_http_exception,
    get_campaign_definition_or_404,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
    DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
)
from src.core.waves import (
    CampaignAssignmentTaskStatus,
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_approval_decision_page,
    build_bulk_review_campaign_definition_assignment_action_page,
    build_bulk_review_campaign_definition_assignment_task_page,
    build_bulk_review_campaign_definition_maker_checker_control_page,
    open_bulk_review_campaign_definition_assignment_task,
    record_bulk_review_campaign_definition_approval_decision,
    record_bulk_review_campaign_definition_assignment_action,
    record_bulk_review_campaign_definition_maker_checker_control,
    transition_bulk_review_campaign_definition_assignment_task,
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
    return _persisted_definition_or_404(persisted)


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
        raise campaign_definition_value_http_exception(exc) from exc
    return _persisted_definition_or_404(persisted)


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
    return _persisted_definition_or_404(persisted)


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
    return _persisted_definition_or_404(persisted)


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


def record_campaign_definition_maker_checker_control_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = record_bulk_review_campaign_definition_maker_checker_control(
            definition=definition,
            control_action=request.control_action,
            control_ref=request.control_ref,
            recorded_by=request.recorded_by,
            submitter_actor_id=request.submitter_actor_id,
            reviewer_actor_id=request.reviewer_actor_id,
            required_reviewer_role=request.required_reviewer_role,
            control_outcome=request.control_outcome,
            control_reason=request.control_reason,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_maker_checker_control(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    return _persisted_definition_or_404(persisted)


def list_campaign_definition_maker_checker_controls_response(
    *,
    campaign_id: str,
    campaign_version: str,
    limit: int,
    offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControlPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_maker_checker_control_page(
        definition=definition,
        limit=limit,
        offset=offset,
    )


def _persisted_definition_or_404(
    persisted: DpmBulkReviewCampaignDefinition | None,
) -> DpmBulkReviewCampaignDefinition:
    if persisted is None:
        raise campaign_definition_not_found_http_exception()
    return persisted
