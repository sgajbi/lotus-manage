from __future__ import annotations

from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.handoffs import (
    DpmPortfolioMemoryReportContext,
    build_portfolio_memory_report_context,
)
from src.core.portfolio_memory.service import build_portfolio_memory_from_sources
from src.core.portfolio_memory.source_repositories import (
    PortfolioMemorySourceRepositories,
    build_portfolio_memory_source_repositories,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository


def build_report_portfolio_memory_context(
    *,
    portfolio_id: str,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
) -> DpmPortfolioMemoryReportContext:
    return build_report_portfolio_memory_context_from_sources(
        portfolio_id=portfolio_id,
        repositories=build_portfolio_memory_source_repositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
        ),
    )


def build_report_portfolio_memory_context_from_sources(
    *,
    portfolio_id: str,
    repositories: PortfolioMemorySourceRepositories,
) -> DpmPortfolioMemoryReportContext:
    memory = build_portfolio_memory_from_sources(
        portfolio_id=portfolio_id,
        repositories=repositories,
    )
    return build_portfolio_memory_report_context(memory)
