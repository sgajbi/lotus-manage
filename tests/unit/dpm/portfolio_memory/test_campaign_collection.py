from src.core.portfolio_memory.campaign_collection import campaign_definition_memory_events
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository
from tests.unit.dpm.api.test_portfolio_memory_api import (
    PORTFOLIO_ID,
    _campaign_definition,
)


def test_campaign_definition_memory_events_projects_matching_campaign_workflow() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(definition=_campaign_definition())

    events = campaign_definition_memory_events(
        portfolio_id=PORTFOLIO_ID,
        campaign_definition_repository=repository,
        limit=100,
    )

    assert [event.event_type for event in events] == [
        "BULK_REVIEW_CAMPAIGN_DEFINITION",
        "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION",
        "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
    ]
    assert {event.source_system for event in events} == {"lotus-manage"}
    assert events[0].metadata["matching_candidate_count"] == 1
    assert events[0].metadata["global_portfolio_universe_discovered"] is False


def test_campaign_definition_memory_events_skips_non_matching_campaign_candidates() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _campaign_definition()
    repository.save_definition(
        definition=definition.model_copy(
            update={
                "campaign_id": "campaign-memory-review-other",
                "candidates": [
                    definition.candidates[0].model_copy(update={"portfolio_id": "PB_OTHER_001"})
                ],
                "content_hash": "sha256:campaign-memory-review-other",
            }
        )
    )

    events = campaign_definition_memory_events(
        portfolio_id=PORTFOLIO_ID,
        campaign_definition_repository=repository,
        limit=100,
    )

    assert events == []
