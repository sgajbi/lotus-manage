"""Bulk-review campaign source-event projection helpers for portfolio memory."""

from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.source_refs import (
    campaign_definition_artifact_ref,
    campaign_definition_source_refs,
    from_wave_source_ref,
)
from src.core.portfolio_memory.supportability import (
    assignment_sla_state,
    assignment_task_state,
    maker_checker_state,
    source_supportability_state,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecision,
    DpmBulkReviewCampaignDefinitionAssignmentAction,
    DpmBulkReviewCampaignDefinitionAssignmentTask,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransition,
    DpmBulkReviewCampaignDefinitionMakerCheckerControl,
)


def campaign_definition_events(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    portfolio_id: str,
) -> list[DpmPortfolioMemoryEvent]:
    events = [campaign_definition_event(definition=definition, portfolio_id=portfolio_id)]
    events.extend(
        campaign_approval_decision_event(definition=definition, decision=decision)
        for decision in definition.approval_decisions
    )
    events.extend(
        campaign_assignment_action_event(definition=definition, action=action)
        for action in definition.assignment_actions
    )
    events.extend(
        campaign_assignment_task_event(definition=definition, task=task)
        for task in definition.assignment_tasks
    )
    events.extend(
        campaign_assignment_task_transition_event(
            definition=definition,
            task=task,
            transition=transition,
        )
        for task in definition.assignment_tasks
        for transition in task.transitions
    )
    events.extend(
        campaign_maker_checker_control_event(definition=definition, control=control)
        for control in definition.maker_checker_controls
    )
    return events


def campaign_definition_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    portfolio_id: str,
) -> DpmPortfolioMemoryEvent:
    matching_candidates = [
        candidate for candidate in definition.candidates if candidate.portfolio_id == portfolio_id
    ]
    source_refs = campaign_definition_source_refs(
        definition=definition,
        portfolio_id=portfolio_id,
    )
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:definition"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_DEFINITION",
        event_time=definition.created_at.isoformat(),
        actor=definition.created_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_DEFINITION",
        source_id=f"{definition.campaign_id}:{definition.campaign_version}",
        status=definition.status,
        supportability_state=source_supportability_state(definition.status),
        summary=(
            f"Bulk-review campaign definition {definition.campaign_id} "
            f"version {definition.campaign_version} is {definition.status}."
        ),
        reason_codes=sorted(
            {
                "BULK_REVIEW_CAMPAIGN_DEFINITION_PERSISTED",
                definition.status,
                *(ref.supportability_state for ref in source_refs if ref.supportability_state),
            }
        ),
        source_refs=source_refs,
        artifact_refs=[campaign_definition_artifact_ref(definition)],
        content_hash=definition.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "as_of_date": definition.as_of_date,
            "candidate_count": len(definition.candidates),
            "matching_candidate_count": len(matching_candidates),
            "eligible_portfolio_types": definition.eligible_portfolio_types,
            "governance_evidence_present": definition.governance is not None,
            "approval_decision_count": len(definition.approval_decisions),
            "assignment_action_count": len(definition.assignment_actions),
            "assignment_task_count": len(definition.assignment_tasks),
            "maker_checker_control_count": len(definition.maker_checker_controls),
            "global_portfolio_universe_discovered": False,
            "membership_recalculated": False,
            "raw_campaign_payload_projected": False,
            "external_workflow_orchestration_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


def campaign_approval_decision_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    decision: DpmBulkReviewCampaignDefinitionApprovalDecision,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:approval:{decision.decision_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
        event_time=decision.decided_at.isoformat(),
        actor=decision.decided_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
        source_id=decision.decision_id,
        status=decision.decision_type,
        supportability_state=source_supportability_state(decision.decision_type),
        summary=f"Bulk-review campaign approval decision {decision.decision_type} recorded.",
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_RECORDED",
            decision.decision_type,
        ],
        source_refs=[from_wave_source_ref(ref) for ref in decision.source_refs],
        artifact_refs=[campaign_definition_artifact_ref(definition)],
        content_hash=decision.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "decision_ref": decision.decision_ref,
            "correlation_id": decision.correlation_id,
            "forbidden_actions": decision.forbidden_actions,
            "trade_approval_claimed": False,
            "external_execution_claimed": False,
        },
    )


def campaign_assignment_action_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    action: DpmBulkReviewCampaignDefinitionAssignmentAction,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:assignment-action:{action.action_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
        event_time=action.recorded_at.isoformat(),
        actor=action.recorded_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
        source_id=action.action_id,
        status=action.action_type,
        supportability_state=assignment_sla_state(action.sla_posture),
        summary=f"Bulk-review campaign assignment action {action.action_type} recorded.",
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_RECORDED",
            action.action_type,
            action.sla_posture,
        ],
        source_refs=[from_wave_source_ref(ref) for ref in action.source_refs],
        artifact_refs=[campaign_definition_artifact_ref(definition)],
        content_hash=action.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "action_ref": action.action_ref,
            "assigned_actor_count": len(action.assigned_actor_ids),
            "escalation_tier": action.escalation_tier,
            "sla_posture": action.sla_posture,
            "correlation_id": action.correlation_id,
            "forbidden_actions": action.forbidden_actions,
            "external_workflow_orchestration_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


def campaign_assignment_task_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    task: DpmBulkReviewCampaignDefinitionAssignmentTask,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:assignment-task:{task.task_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
        event_time=task.opened_at.isoformat(),
        actor=task.opened_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
        source_id=task.task_id,
        status=task.status,
        supportability_state=assignment_task_state(task.status, task.sla_posture),
        summary=f"Bulk-review campaign assignment task {task.task_ref} is {task.status}.",
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_RECORDED",
            task.status,
            task.sla_posture,
        ],
        source_refs=[from_wave_source_ref(ref) for ref in task.source_refs],
        artifact_refs=[campaign_definition_artifact_ref(definition)],
        content_hash=task.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "task_ref": task.task_ref,
            "task_type": task.task_type,
            "assigned_actor_count": len(task.assigned_actor_ids),
            "escalation_tier": task.escalation_tier,
            "sla_posture": task.sla_posture,
            "transition_count": len(task.transitions),
            "correlation_id": task.correlation_id,
            "forbidden_actions": task.forbidden_actions,
            "external_workflow_orchestration_claimed": False,
            "approval_state_mutation_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


def campaign_assignment_task_transition_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    task: DpmBulkReviewCampaignDefinitionAssignmentTask,
    transition: DpmBulkReviewCampaignDefinitionAssignmentTaskTransition,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:"
            f"assignment-task:{task.task_id}:transition:{transition.transition_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION",
        event_time=transition.transitioned_at.isoformat(),
        actor=transition.transitioned_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION",
        source_id=transition.transition_id,
        status=transition.to_status,
        supportability_state=assignment_task_state(
            transition.to_status,
            transition.sla_posture,
        ),
        summary=(
            f"Bulk-review campaign assignment task {task.task_ref} transition "
            f"{transition.transition_type} recorded."
        ),
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_RECORDED",
            transition.transition_type,
            transition.to_status,
            transition.sla_posture,
        ],
        source_refs=[from_wave_source_ref(ref) for ref in transition.source_refs],
        artifact_refs=[
            campaign_definition_artifact_ref(definition),
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
                source_id=task.task_id,
                content_hash=task.content_hash,
            ),
        ],
        content_hash=transition.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "task_id": task.task_id,
            "task_ref": task.task_ref,
            "task_type": task.task_type,
            "transition_ref": transition.transition_ref,
            "transition_type": transition.transition_type,
            "from_status": transition.from_status,
            "to_status": transition.to_status,
            "assigned_actor_count": len(transition.assigned_actor_ids),
            "escalation_tier": transition.escalation_tier,
            "sla_posture": transition.sla_posture,
            "due_at_present": transition.due_at is not None,
            "correlation_id": transition.correlation_id,
            "transition_reason_projected": False,
            "external_workflow_orchestration_claimed": False,
            "approval_state_mutation_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


def campaign_maker_checker_control_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    control: DpmBulkReviewCampaignDefinitionMakerCheckerControl,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:maker-checker:{control.control_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
        event_time=control.recorded_at.isoformat(),
        actor=control.recorded_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
        source_id=control.control_id,
        status=control.control_outcome,
        supportability_state=maker_checker_state(control.control_outcome),
        summary=(
            f"Bulk-review campaign maker-checker control {control.control_action} "
            f"recorded with {control.control_outcome} outcome."
        ),
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_RECORDED",
            control.control_action,
            control.control_outcome,
        ],
        source_refs=[from_wave_source_ref(ref) for ref in control.source_refs],
        artifact_refs=[campaign_definition_artifact_ref(definition)],
        content_hash=control.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "control_ref": control.control_ref,
            "control_action": control.control_action,
            "submitter_actor_id_present": control.submitter_actor_id is not None,
            "reviewer_actor_id_present": control.reviewer_actor_id is not None,
            "required_reviewer_role": control.required_reviewer_role,
            "correlation_id": control.correlation_id,
            "forbidden_actions": control.forbidden_actions,
            "trade_approval_claimed": False,
            "external_workflow_orchestration_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )
