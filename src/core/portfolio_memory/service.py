"""Source-backed portfolio memory read-model assembly."""

from datetime import datetime, timezone

from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.pm_quality.repository import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationRepository,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemorySearchPage,
    PortfolioMemorySupportabilityState,
)
from src.core.portfolio_memory.aggregate import (
    build_portfolio_memory_aggregate as _build_portfolio_memory_aggregate,
)
from src.core.portfolio_memory.candidate_portfolios import (
    candidate_portfolio_ids_from_sources as _candidate_portfolio_ids_from_sources,
)
from src.core.portfolio_memory.search_page import (
    build_search_page as _build_search_page,
    build_search_row as _build_search_row,
)
from src.core.portfolio_memory.search_request import (
    build_portfolio_memory_search_query as _build_portfolio_memory_search_query,
)
from src.core.portfolio_memory.source_collection import (
    collect_portfolio_memory_events as _collect_portfolio_memory_events,
)
from src.core.portfolio_memory.source_repositories import PortfolioMemorySourceRepositories
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.core.waves.repository import DpmWaveRepository


def build_portfolio_memory(
    *,
    portfolio_id: str,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None = None,
    construction_repository: ConstructionRepository | None = None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None = None,
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository | None = None,
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None = None,
    limit: int = 100,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemory:
    """Compose manage-owned portfolio memory without recalculating source truth."""

    return build_portfolio_memory_from_sources(
        portfolio_id=portfolio_id,
        repositories=_source_repositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
            construction_repository=construction_repository,
            pm_quality_score_run_repository=pm_quality_score_run_repository,
            pm_quality_review_action_repository=pm_quality_review_action_repository,
            pm_quality_summary_invocation_repository=pm_quality_summary_invocation_repository,
            campaign_definition_repository=campaign_definition_repository,
        ),
        limit=limit,
        generated_at=generated_at,
    )


def build_portfolio_memory_from_sources(
    *,
    portfolio_id: str,
    repositories: PortfolioMemorySourceRepositories,
    limit: int = 100,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemory:
    """Compose portfolio memory from an explicit source-repository bundle."""

    generated_at = generated_at or datetime.now(timezone.utc)
    events = _collect_portfolio_memory_events(
        portfolio_id=portfolio_id,
        repositories=repositories,
        limit=limit,
    )
    return _build_portfolio_memory_aggregate(
        portfolio_id=portfolio_id,
        events=events,
        limit=limit,
        generated_at=generated_at,
    )


def search_portfolio_memory(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None = None,
    construction_repository: ConstructionRepository | None = None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None = None,
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository | None = None,
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None = None,
    portfolio_ids: list[str] | None = None,
    event_type: str | None = None,
    supportability_state: PortfolioMemorySupportabilityState | None = None,
    source_system: str | None = None,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    source_scan_limit: int = 500,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemorySearchPage:
    """Build a bounded Manage-local index over persisted portfolio-memory evidence."""

    generated_at = generated_at or datetime.now(timezone.utc)
    repositories = _source_repositories(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        construction_repository=construction_repository,
        pm_quality_score_run_repository=pm_quality_score_run_repository,
        pm_quality_review_action_repository=pm_quality_review_action_repository,
        pm_quality_summary_invocation_repository=pm_quality_summary_invocation_repository,
        campaign_definition_repository=campaign_definition_repository,
    )
    search_query = _build_portfolio_memory_search_query(
        portfolio_ids=portfolio_ids,
        event_type=event_type,
        supportability_state=supportability_state,
        source_system=source_system,
        source_type=source_type,
        limit=limit,
        offset=offset,
        source_scan_limit=source_scan_limit,
    )
    candidate_ids = _candidate_portfolio_ids_from_sources(
        repositories=repositories,
        portfolio_ids=portfolio_ids,
        source_scan_limit=search_query.source_scan_limit,
    )
    search_rows = []
    for portfolio_id in candidate_ids:
        memory = build_portfolio_memory_from_sources(
            portfolio_id=portfolio_id,
            repositories=repositories,
            limit=search_query.source_scan_limit,
            generated_at=generated_at,
        )
        row = _build_search_row(
            memory=memory,
            filters=search_query.filters,
            explicit_candidate_ids=search_query.explicit_candidate_ids,
        )
        if row is not None:
            search_rows.append(row)

    return _build_search_page(
        search_rows=search_rows,
        filters=search_query.filters,
        explicit_candidate_ids=search_query.explicit_candidate_ids,
        scanned_portfolio_count=len(candidate_ids),
        source_scan_limit=search_query.source_scan_limit,
        limit=search_query.limit,
        offset=search_query.offset,
        generated_at=generated_at.isoformat(),
    )


def _source_repositories(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
    construction_repository: ConstructionRepository | None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None,
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository | None,
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None,
) -> PortfolioMemorySourceRepositories:
    return PortfolioMemorySourceRepositories(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        construction_repository=construction_repository,
        pm_quality_score_run_repository=pm_quality_score_run_repository,
        pm_quality_review_action_repository=pm_quality_review_action_repository,
        pm_quality_summary_invocation_repository=pm_quality_summary_invocation_repository,
        campaign_definition_repository=campaign_definition_repository,
    )
