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
from src.core.portfolio_memory.search_page import (
    build_search_page as _build_search_page,
    build_search_row as _build_search_row,
)
from src.core.portfolio_memory.read_request import (
    PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT,
    validate_portfolio_memory_read_limit as _validate_portfolio_memory_read_limit,
)
from src.core.portfolio_memory.search_request import (
    PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT,
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
    build_portfolio_memory_search_query as _build_portfolio_memory_search_query,
)
from src.core.portfolio_memory.source_collection import (
    collect_portfolio_memory_events as _collect_portfolio_memory_events,
)
from src.core.portfolio_memory.search_source_collection import (
    collect_portfolio_memory_search_events as _collect_portfolio_memory_search_events,
)
from src.core.portfolio_memory.source_repositories import (
    PortfolioMemorySourceRepositories,
    build_portfolio_memory_source_repositories as _build_portfolio_memory_source_repositories,
    require_campaign_definition_tenant_id as _require_campaign_definition_tenant_id,
    require_mandate_tenant_id as _require_mandate_tenant_id,
    require_pm_quality_tenant_id as _require_pm_quality_tenant_id,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.core.waves.repository import DpmWaveRepository


def build_portfolio_memory(
    *,
    tenant_id: str | None = None,
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
    limit: int = PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemory:
    """Compose manage-owned portfolio memory without recalculating source truth."""

    return build_portfolio_memory_from_sources(
        tenant_id=tenant_id,
        portfolio_id=portfolio_id,
        repositories=_build_portfolio_memory_source_repositories(
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


def _require_tenant_id_for_tenant_scoped_sources(
    *,
    tenant_id: str | None,
    repositories: PortfolioMemorySourceRepositories,
) -> str | None:
    pm_quality_tenant_id = _require_pm_quality_tenant_id(
        tenant_id=tenant_id,
        repositories=repositories,
    )
    if pm_quality_tenant_id is not None:
        return pm_quality_tenant_id
    campaign_tenant_id = _require_campaign_definition_tenant_id(
        tenant_id=tenant_id,
        repositories=repositories,
    )
    if campaign_tenant_id is not None:
        return campaign_tenant_id
    # Mandate snapshots and their health evidence are tenant-scoped too
    # (issue #648), so they join this list rather than being checked
    # separately downstream. Without this the caller's tenant is validated for
    # the other families, found irrelevant to them, and discarded as None -
    # which then reaches the mandate collector as an absent tenant even though
    # the caller supplied one.
    return _require_mandate_tenant_id(
        tenant_id=tenant_id,
        repositories=repositories,
    )


def build_portfolio_memory_from_sources(
    *,
    tenant_id: str | None = None,
    portfolio_id: str,
    repositories: PortfolioMemorySourceRepositories,
    limit: int = PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemory:
    """Compose portfolio memory from an explicit source-repository bundle."""

    limit = _validate_portfolio_memory_read_limit(limit=limit)
    generated_at = generated_at or datetime.now(timezone.utc)
    source_tenant_id = _require_tenant_id_for_tenant_scoped_sources(
        tenant_id=tenant_id,
        repositories=repositories,
    )
    events = _collect_portfolio_memory_events(
        tenant_id=source_tenant_id,
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
    tenant_id: str | None = None,
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
    limit: int = PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
    offset: int = PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT,
    source_scan_limit: int = PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemorySearchPage:
    """Build a bounded Manage-local index over persisted portfolio-memory evidence."""

    return search_portfolio_memory_from_sources(
        tenant_id=tenant_id,
        repositories=_build_portfolio_memory_source_repositories(
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
        portfolio_ids=portfolio_ids,
        event_type=event_type,
        supportability_state=supportability_state,
        source_system=source_system,
        source_type=source_type,
        limit=limit,
        offset=offset,
        source_scan_limit=source_scan_limit,
        generated_at=generated_at,
    )


def search_portfolio_memory_from_sources(
    *,
    tenant_id: str | None = None,
    repositories: PortfolioMemorySourceRepositories,
    portfolio_ids: list[str] | None = None,
    event_type: str | None = None,
    supportability_state: PortfolioMemorySupportabilityState | None = None,
    source_system: str | None = None,
    source_type: str | None = None,
    limit: int = PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
    offset: int = PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT,
    source_scan_limit: int = PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemorySearchPage:
    """Build a bounded Manage-local search page from an explicit source bundle."""

    generated_at = generated_at or datetime.now(timezone.utc)
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
    source_tenant_id = _require_tenant_id_for_tenant_scoped_sources(
        tenant_id=tenant_id,
        repositories=repositories,
    )
    search_sources = _collect_portfolio_memory_search_events(
        tenant_id=source_tenant_id,
        repositories=repositories,
        portfolio_ids=search_query.explicit_candidate_ids,
        limit=search_query.source_scan_limit,
    )
    search_rows = []
    for portfolio_id in search_sources.candidate_portfolio_ids:
        memory = _build_portfolio_memory_aggregate(
            portfolio_id=portfolio_id,
            events=search_sources.events_by_portfolio_id.get(portfolio_id, []),
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
        scanned_portfolio_count=len(search_sources.candidate_portfolio_ids),
        source_scan_limit=search_query.source_scan_limit,
        limit=search_query.limit,
        offset=search_query.offset,
        generated_at=generated_at.isoformat(),
    )
