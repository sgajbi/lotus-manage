from __future__ import annotations

from src.api.services.portfolio_memory_context_service import (
    build_report_portfolio_memory_context,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes import (
    DpmOutcomeAiEvidenceInput,
    DpmOutcomeReportInput,
    DpmPostTradeOutcomeReview,
    build_ai_evidence_input,
    build_report_input,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository


def build_outcome_report_input(
    *,
    review: DpmPostTradeOutcomeReview,
    proof_pack_repository: DpmProofPackRepository | None,
    wave_repository: DpmWaveRepository | None,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
    tenant_id: str | None,
) -> DpmOutcomeReportInput:
    return build_report_input(
        review,
        portfolio_memory_context=portfolio_memory_context_for_report(
            review=review,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
            tenant_id=tenant_id,
        ),
    )


def build_outcome_ai_evidence_input(
    *,
    review: DpmPostTradeOutcomeReview,
    proof_pack_repository: DpmProofPackRepository | None,
    wave_repository: DpmWaveRepository | None,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
    tenant_id: str | None,
) -> DpmOutcomeAiEvidenceInput:
    return build_ai_evidence_input(
        review,
        portfolio_memory_context=portfolio_memory_context_for_report(
            review=review,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
            tenant_id=tenant_id,
        ),
    )


def portfolio_memory_context_for_report(
    *,
    review: DpmPostTradeOutcomeReview,
    proof_pack_repository: DpmProofPackRepository | None,
    wave_repository: DpmWaveRepository | None,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
    tenant_id: str | None,
) -> DpmPortfolioMemoryReportContext | None:
    if proof_pack_repository is None or wave_repository is None:
        return None
    return build_report_portfolio_memory_context(
        portfolio_id=review.portfolio_id,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        tenant_id=tenant_id,
    )


__all__ = [
    "build_outcome_ai_evidence_input",
    "build_outcome_report_input",
    "portfolio_memory_context_for_report",
]
