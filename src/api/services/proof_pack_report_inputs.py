from __future__ import annotations

from src.api.services.portfolio_memory_context_service import (
    build_report_portfolio_memory_context,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.proof_packs import build_ai_evidence_input, build_report_input
from src.core.proof_packs.handoffs import DpmProofPackAiEvidenceInput, DpmProofPackReportInput
from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository


def build_proof_pack_report_input(
    *,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository | None,
    outcome_review_repository: DpmOutcomeReviewRepository | None,
    mandate_repository: DpmMandateRepository | None,
    tenant_id: str | None,
) -> DpmProofPackReportInput:
    return build_report_input(
        proof_pack,
        portfolio_memory_context=portfolio_memory_context_for_report(
            portfolio_id=proof_pack.portfolio_id,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
            tenant_id=tenant_id,
        ),
    )


def build_proof_pack_ai_evidence_input(
    *,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository | None,
    outcome_review_repository: DpmOutcomeReviewRepository | None,
    mandate_repository: DpmMandateRepository | None,
    tenant_id: str | None,
) -> DpmProofPackAiEvidenceInput:
    return build_ai_evidence_input(
        proof_pack,
        portfolio_memory_context=portfolio_memory_context_for_report(
            portfolio_id=proof_pack.portfolio_id,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
            tenant_id=tenant_id,
        ),
    )


def portfolio_memory_context_for_report(
    *,
    portfolio_id: str,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository | None,
    outcome_review_repository: DpmOutcomeReviewRepository | None,
    mandate_repository: DpmMandateRepository | None,
    tenant_id: str | None,
) -> DpmPortfolioMemoryReportContext | None:
    if wave_repository is None or outcome_review_repository is None:
        return None
    return build_report_portfolio_memory_context(
        portfolio_id=portfolio_id,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        tenant_id=tenant_id,
    )


__all__ = [
    "build_proof_pack_ai_evidence_input",
    "build_proof_pack_report_input",
    "portfolio_memory_context_for_report",
]
