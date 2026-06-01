from __future__ import annotations

from src.api.services.proof_pack_mandate_evidence import ProofPackMandateEvidence
from src.api.services.proof_pack_selected_source import ProofPackSelectedAlternativeSource
from src.core.construction.models import AuthoritativeRegimeStressContext
from src.core.proof_packs import (
    build_proof_pack_from_run,
    build_proof_pack_from_selected_alternative,
)
from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord


def build_run_proof_pack(
    *,
    run: DpmRunRecord,
    workflow_decisions: list[DpmRunWorkflowDecisionRecord],
    actor_id: str,
    reason: str | None,
    correlation_id: str | None,
    mandate_id: str | None,
    mandate_evidence: ProofPackMandateEvidence,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None,
) -> DpmPreTradeProofPack:
    return build_proof_pack_from_run(
        run=run,
        created_by=actor_id,
        reason=reason,
        correlation_id=correlation_id,
        mandate_id=mandate_id,
        mandate_twin=mandate_evidence.twin,
        mandate_health=mandate_evidence.health,
        mandate_evidence_gap_codes=mandate_evidence.gap_codes,
        workflow_decisions=workflow_decisions,
        direct_regime_stress_context=direct_regime_stress_context,
    )


def build_selected_alternative_proof_pack(
    *,
    selected_source: ProofPackSelectedAlternativeSource,
    selected_alternative_id: str,
    actor_id: str,
    reason: str | None,
    correlation_id: str | None,
    mandate_id: str | None,
    mandate_evidence: ProofPackMandateEvidence,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None,
) -> DpmPreTradeProofPack:
    return build_proof_pack_from_selected_alternative(
        alternative_set=selected_source.alternative_set,
        selected_alternative_id=selected_alternative_id,
        run=selected_source.run,
        selection=selected_source.selection,
        created_by=actor_id,
        reason=reason,
        correlation_id=correlation_id,
        mandate_id=mandate_id,
        mandate_twin=mandate_evidence.twin,
        mandate_health=mandate_evidence.health,
        mandate_evidence_gap_codes=mandate_evidence.gap_codes,
        workflow_decisions=selected_source.workflow_decisions,
        direct_regime_stress_context=direct_regime_stress_context,
    )


__all__ = ["build_run_proof_pack", "build_selected_alternative_proof_pack"]
