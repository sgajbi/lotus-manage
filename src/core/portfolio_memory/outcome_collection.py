"""Outcome-review repository collection for portfolio-memory events."""

from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.outcome_projection import outcome_review_events


def outcome_review_memory_events(
    *,
    portfolio_id: str,
    outcome_review_repository: DpmOutcomeReviewRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect post-trade outcome-review memory events for one portfolio."""

    events: list[DpmPortfolioMemoryEvent] = []
    for review in outcome_review_repository.list_outcome_reviews(
        portfolio_id=portfolio_id,
        limit=limit,
    ):
        persisted_events = outcome_review_repository.list_events(
            outcome_review_id=review.outcome_review_id
        )
        events.extend(outcome_review_events(review=review, persisted_events=persisted_events))
    return events
