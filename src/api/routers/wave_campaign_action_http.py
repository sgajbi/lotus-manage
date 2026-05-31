from __future__ import annotations

from src.api.routers.wave_campaign_action_common import persisted_definition_or_404
from src.api.routers.wave_campaign_approval_decision_http import (
    list_campaign_definition_approval_decisions_response as list_campaign_definition_approval_decisions_response,
    record_campaign_definition_approval_decision_response as record_campaign_definition_approval_decision_response,
)
from src.api.routers.wave_campaign_assignment_action_http import (
    list_campaign_definition_assignment_actions_response as list_campaign_definition_assignment_actions_response,
    record_campaign_definition_assignment_action_response as record_campaign_definition_assignment_action_response,
)
from src.api.routers.wave_campaign_assignment_task_http import (
    list_campaign_definition_assignment_tasks_response as list_campaign_definition_assignment_tasks_response,
    open_campaign_definition_assignment_task_response as open_campaign_definition_assignment_task_response,
    transition_campaign_definition_assignment_task_response as transition_campaign_definition_assignment_task_response,
)
from src.api.routers.wave_campaign_definition_http import (
    campaign_definition_conflict_http_exception,
    campaign_definition_value_http_exception,
    get_campaign_definition_or_404,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    DpmBulkReviewCampaignDefinitionRepository,
    build_bulk_review_campaign_definition_maker_checker_control_page,
    record_bulk_review_campaign_definition_maker_checker_control,
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
    return persisted_definition_or_404(persisted)


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
