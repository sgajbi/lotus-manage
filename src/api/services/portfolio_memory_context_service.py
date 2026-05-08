from __future__ import annotations

from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.handoffs import (
    DpmPortfolioMemoryReportContext,
    build_portfolio_memory_report_context,
)
from src.core.portfolio_memory.service import build_portfolio_memory
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
    memory = build_portfolio_memory(
        portfolio_id=portfolio_id,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )
    return build_portfolio_memory_report_context(memory)
