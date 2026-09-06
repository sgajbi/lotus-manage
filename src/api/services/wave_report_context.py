from src.api.services.portfolio_memory_context_service import (
    build_report_portfolio_memory_context,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


def portfolio_memory_context_for_report(
    *,
    wave: DpmRebalanceWave,
    proof_pack_repository: DpmProofPackRepository | None,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository | None,
    mandate_repository: DpmMandateRepository | None,
    tenant_id: str | None,
) -> DpmPortfolioMemoryReportContext | None:
    if proof_pack_repository is None or outcome_review_repository is None or not wave.items:
        return None
    portfolio_id = wave.items[0].portfolio_id
    return build_report_portfolio_memory_context(
        portfolio_id=portfolio_id,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        tenant_id=tenant_id,
    )


__all__ = ["portfolio_memory_context_for_report"]
