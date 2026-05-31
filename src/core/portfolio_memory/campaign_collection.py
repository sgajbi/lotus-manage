"""Campaign-definition repository collection for portfolio-memory events."""

from src.core.portfolio_memory.campaign_projection import campaign_definition_events
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository


def campaign_definition_memory_events(
    *,
    portfolio_id: str,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect campaign workflow memory events for definitions containing one portfolio."""

    definitions = [
        definition
        for definition in campaign_definition_repository.list_definitions(limit=limit)
        if any(candidate.portfolio_id == portfolio_id for candidate in definition.candidates)
    ]
    events: list[DpmPortfolioMemoryEvent] = []
    for definition in definitions:
        events.extend(
            campaign_definition_events(
                definition=definition,
                portfolio_id=portfolio_id,
            )
        )
    return events
