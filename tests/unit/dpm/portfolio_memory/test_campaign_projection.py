from src.core.portfolio_memory.campaign_projection import campaign_definition_events
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID, _campaign_definition


def _event_by_type(event_type: str):
    return next(
        event
        for event in campaign_definition_events(
            definition=_campaign_definition(),
            portfolio_id=PORTFOLIO_ID,
        )
        if event.event_type == event_type
    )


def test_campaign_definition_event_preserves_source_lineage_without_global_discovery() -> None:
    event = _event_by_type("BULK_REVIEW_CAMPAIGN_DEFINITION")

    assert event.source_type == "BULK_REVIEW_CAMPAIGN_DEFINITION"
    assert event.supportability_state == "READY"
    assert event.metadata["matching_candidate_count"] == 1
    assert event.metadata["global_portfolio_universe_discovered"] is False
    assert event.metadata["membership_recalculated"] is False
    assert event.metadata["raw_campaign_payload_projected"] is False
    assert event.metadata["external_execution_claimed"] is False
    assert event.artifact_refs[0].source_type == "BulkReviewCampaignDefinition"
    assert {ref.source_system for ref in event.source_refs} == {"lotus-core", "lotus-manage"}


def test_campaign_assignment_task_transition_event_preserves_boundary_flags() -> None:
    event = _event_by_type("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION")

    assert event.supportability_state == "PENDING_REVIEW"
    assert event.metadata["transition_reason_projected"] is False
    assert event.metadata["external_workflow_orchestration_claimed"] is False
    assert event.metadata["approval_state_mutation_claimed"] is False
    assert event.metadata["client_contact_claimed"] is False
    assert event.metadata["external_execution_claimed"] is False
    assert event.artifact_refs[1].source_type == "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK"


def test_campaign_maker_checker_event_preserves_no_external_approval_or_execution_claims() -> None:
    event = _event_by_type("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL")

    assert event.supportability_state == "READY"
    assert event.metadata["submitter_actor_id_present"] is True
    assert event.metadata["reviewer_actor_id_present"] is True
    assert event.metadata["trade_approval_claimed"] is False
    assert event.metadata["external_workflow_orchestration_claimed"] is False
    assert event.metadata["client_contact_claimed"] is False
    assert event.metadata["external_execution_claimed"] is False
