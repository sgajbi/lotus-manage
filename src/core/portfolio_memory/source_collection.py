"""Source-family collection orchestration for portfolio memory."""

from src.core.portfolio_memory.campaign_collection import campaign_definition_memory_events
from src.core.portfolio_memory.construction_collection import construction_memory_events
from src.core.portfolio_memory.mandate_collection import mandate_memory_events
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.outcome_collection import outcome_review_memory_events
from src.core.portfolio_memory.pm_quality_collection import pm_quality_memory_events
from src.core.portfolio_memory.proof_pack_collection import proof_pack_memory_events
from src.core.portfolio_memory.read_request import validate_portfolio_memory_read_limit
from src.core.portfolio_memory.source_repositories import PortfolioMemorySourceRepositories
from src.core.portfolio_memory.wave_collection import wave_memory_events


def collect_portfolio_memory_events(
    *,
    portfolio_id: str,
    repositories: PortfolioMemorySourceRepositories,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect source-family memory events without aggregating or hashing them."""

    limit = validate_portfolio_memory_read_limit(limit=limit)
    events: list[DpmPortfolioMemoryEvent] = []
    events.extend(
        proof_pack_memory_events(
            portfolio_id=portfolio_id,
            proof_pack_repository=repositories.proof_pack_repository,
            limit=limit,
        )
    )

    if repositories.mandate_repository is not None:
        events.extend(
            mandate_memory_events(
                portfolio_id=portfolio_id,
                mandate_repository=repositories.mandate_repository,
                limit=limit,
            )
        )

    if repositories.construction_repository is not None:
        events.extend(
            construction_memory_events(
                portfolio_id=portfolio_id,
                construction_repository=repositories.construction_repository,
                limit=limit,
            )
        )

    events.extend(
        wave_memory_events(
            portfolio_id=portfolio_id,
            wave_repository=repositories.wave_repository,
            limit=limit,
        )
    )

    if repositories.campaign_definition_repository is not None:
        events.extend(
            campaign_definition_memory_events(
                portfolio_id=portfolio_id,
                campaign_definition_repository=repositories.campaign_definition_repository,
                limit=limit,
            )
        )

    events.extend(
        outcome_review_memory_events(
            portfolio_id=portfolio_id,
            outcome_review_repository=repositories.outcome_review_repository,
            limit=limit,
        )
    )

    if repositories.pm_quality_score_run_repository is not None:
        events.extend(
            pm_quality_memory_events(
                portfolio_id=portfolio_id,
                score_run_repository=repositories.pm_quality_score_run_repository,
                review_action_repository=repositories.pm_quality_review_action_repository,
                summary_invocation_repository=repositories.pm_quality_summary_invocation_repository,
                limit=limit,
            )
        )

    return events
