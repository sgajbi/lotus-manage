from src.core.outcomes import DpmOutcomeEvent
from src.core.portfolio_memory.outcome_collection import outcome_review_memory_events
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID
from tests.unit.infrastructure.test_outcome_review_repository import _review


def test_outcome_review_memory_events_projects_review_and_persisted_events() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    review = _review()
    repository.save_outcome_review(review=review, retention_expires_at=None)
    repository.append_event(
        event=DpmOutcomeEvent(
            event_id="dor_001_refreshed",
            event_type="OUTCOME_REVIEW_SOURCE_REFRESHED",
            event_time="2026-05-06T01:30:00Z",
            actor="system",
            outcome_review_id=review.outcome_review_id,
            state="READY",
            reason_codes=["SOURCE_REFRESHED"],
        )
    )

    events = outcome_review_memory_events(
        portfolio_id=PORTFOLIO_ID,
        outcome_review_repository=repository,
        limit=100,
    )

    assert [event.event_type for event in events] == [
        "OUTCOME_REVIEW_CREATED",
        "OUTCOME_REVIEW_EVENT",
        "OUTCOME_REVIEW_EVENT",
    ]
    assert events[0].source_id == review.outcome_review_id
    assert {event.source_id for event in events[1:]} == {
        "dor_001_created",
        "dor_001_refreshed",
    }
    assert all(
        event.metadata == {"outcome_review_id": review.outcome_review_id} for event in events[1:]
    )


def test_outcome_review_memory_events_uses_portfolio_filter() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(
        review=_review().model_copy(update={"portfolio_id": "PB_OTHER_001"}),
        retention_expires_at=None,
    )

    events = outcome_review_memory_events(
        portfolio_id=PORTFOLIO_ID,
        outcome_review_repository=repository,
        limit=100,
    )

    assert events == []
