from __future__ import annotations

from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs import (
    AI_EVIDENCE_REF_TYPE,
    REPORT_INPUT_REF_TYPE,
    proof_pack_id_for_rebalance_run,
    proof_pack_id_for_selected_alternative,
)
from src.core.construction.models import AuthoritativeRegimeStressContext
from src.core.proof_packs.handoffs import DpmProofPackAiEvidenceInput, DpmProofPackReportInput
from src.api.services.proof_pack_report_inputs import (
    build_proof_pack_ai_evidence_input,
    build_proof_pack_report_input,
)
from src.api.services.proof_pack_handoff_refs import (
    ensure_handoff_refs as _ensure_handoff_refs,
    hydrate_handoff_refs,
    require_handoff_ref,
)
from src.api.services.proof_pack_generation import (
    build_run_proof_pack,
    build_selected_alternative_proof_pack,
)
from src.api.services.proof_pack_mandate_evidence import resolve_mandate_evidence
from src.api.services.proof_pack_persistence import persist_proof_pack
from src.api.services.proof_pack_replay import find_replayable_proof_pack
from src.api.services.proof_pack_selected_source import resolve_selected_alternative_source
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.rebalance_runs.service import DpmRunNotFoundError, DpmRunSupportService
from src.core.waves.repository import DpmWaveRepository


class DpmProofPackReportInputNotGeneratedError(Exception):
    pass


class DpmProofPackAiEvidenceInputNotGeneratedError(Exception):
    pass


def generate_proof_pack_from_run(
    *,
    rebalance_run_id: str,
    actor_id: str,
    reason: str | None,
    correlation_id: str | None,
    mandate_id: str | None,
    idempotency_key: str | None,
    run_service: DpmRunSupportService,
    mandate_repository: DpmMandateRepository | None,
    proof_pack_repository: DpmProofPackRepository,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None = None,
) -> DpmPreTradeProofPack:
    existing = find_replayable_proof_pack(
        proof_pack_id=proof_pack_id_for_rebalance_run(rebalance_run_id=rebalance_run_id),
        idempotency_key=idempotency_key,
        proof_pack_repository=proof_pack_repository,
    )
    if existing is not None:
        return existing
    run = run_service.get_run_record(rebalance_run_id=rebalance_run_id)
    mandate_evidence = resolve_mandate_evidence(
        mandate_id=mandate_id,
        portfolio_id=run.portfolio_id,
        mandate_repository=mandate_repository,
    )
    proof_pack = build_run_proof_pack(
        run=run,
        workflow_decisions=run_service.list_workflow_decision_records(
            rebalance_run_id=rebalance_run_id
        ),
        actor_id=actor_id,
        reason=reason,
        correlation_id=correlation_id,
        mandate_id=mandate_id,
        mandate_evidence=mandate_evidence,
        direct_regime_stress_context=direct_regime_stress_context,
    )
    persist_proof_pack(
        proof_pack_repository=proof_pack_repository,
        proof_pack=proof_pack,
        idempotency_key=idempotency_key,
    )
    return proof_pack


def generate_proof_pack_from_selected_alternative(
    *,
    alternative_set_id: str,
    selected_alternative_id: str,
    actor_id: str,
    reason: str | None,
    correlation_id: str | None,
    mandate_id: str | None,
    idempotency_key: str | None,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    mandate_repository: DpmMandateRepository | None,
    proof_pack_repository: DpmProofPackRepository,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None = None,
) -> DpmPreTradeProofPack:
    existing = find_replayable_proof_pack(
        proof_pack_id=proof_pack_id_for_selected_alternative(
            alternative_set_id=alternative_set_id,
            selected_alternative_id=selected_alternative_id,
        ),
        idempotency_key=idempotency_key,
        proof_pack_repository=proof_pack_repository,
    )
    if existing is not None:
        return existing
    selected_source = resolve_selected_alternative_source(
        alternative_set_id=alternative_set_id,
        selected_alternative_id=selected_alternative_id,
        construction_repository=construction_repository,
        run_service=run_service,
    )
    mandate_evidence = resolve_mandate_evidence(
        mandate_id=mandate_id,
        portfolio_id=selected_source.alternative_set.portfolio_id,
        mandate_repository=mandate_repository,
    )
    proof_pack = build_selected_alternative_proof_pack(
        selected_source=selected_source,
        selected_alternative_id=selected_alternative_id,
        actor_id=actor_id,
        reason=reason,
        correlation_id=correlation_id,
        mandate_id=mandate_id,
        mandate_evidence=mandate_evidence,
        direct_regime_stress_context=direct_regime_stress_context,
    )
    persist_proof_pack(
        proof_pack_repository=proof_pack_repository,
        proof_pack=proof_pack,
        idempotency_key=idempotency_key,
    )
    return proof_pack


def get_proof_pack(
    *,
    proof_pack_id: str,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmPreTradeProofPack:
    proof_pack = proof_pack_repository.get_proof_pack(proof_pack_id=proof_pack_id)
    if proof_pack is None:
        raise DpmRunNotFoundError("DPM_PROOF_PACK_NOT_FOUND")
    return hydrate_handoff_refs(
        proof_pack=proof_pack,
        proof_pack_repository=proof_pack_repository,
    )


def get_report_input_ref(
    *,
    proof_pack_id: str,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmProofPackEvidenceRef:
    proof_pack = get_proof_pack(
        proof_pack_id=proof_pack_id,
        proof_pack_repository=proof_pack_repository,
    )
    ref = require_handoff_ref(
        proof_pack_id=proof_pack_id,
        hydrated_ref=proof_pack.report_input_ref,
        ref_type=REPORT_INPUT_REF_TYPE,
        proof_pack_repository=proof_pack_repository,
    )
    if ref is None:
        raise DpmProofPackReportInputNotGeneratedError("DPM_PROOF_PACK_REPORT_INPUT_NOT_GENERATED")
    return ref


def get_ai_evidence_ref(
    *,
    proof_pack_id: str,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmProofPackEvidenceRef:
    proof_pack = get_proof_pack(
        proof_pack_id=proof_pack_id,
        proof_pack_repository=proof_pack_repository,
    )
    ref = require_handoff_ref(
        proof_pack_id=proof_pack_id,
        hydrated_ref=proof_pack.ai_evidence_ref,
        ref_type=AI_EVIDENCE_REF_TYPE,
        proof_pack_repository=proof_pack_repository,
    )
    if ref is None:
        raise DpmProofPackAiEvidenceInputNotGeneratedError(
            "DPM_PROOF_PACK_AI_EVIDENCE_INPUT_NOT_GENERATED"
        )
    return ref


def get_report_input(
    *,
    proof_pack_id: str,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository | None = None,
    outcome_review_repository: DpmOutcomeReviewRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
) -> DpmProofPackReportInput:
    proof_pack = get_proof_pack(
        proof_pack_id=proof_pack_id,
        proof_pack_repository=proof_pack_repository,
    )
    return build_proof_pack_report_input(
        proof_pack=proof_pack,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )


def get_ai_evidence_input(
    *,
    proof_pack_id: str,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository | None = None,
    outcome_review_repository: DpmOutcomeReviewRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
) -> DpmProofPackAiEvidenceInput:
    proof_pack = get_proof_pack(
        proof_pack_id=proof_pack_id,
        proof_pack_repository=proof_pack_repository,
    )
    return build_proof_pack_ai_evidence_input(
        proof_pack=proof_pack,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )


def ensure_handoff_refs(
    *,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
    include_report_input: bool,
    include_ai_evidence_input: bool,
) -> DpmPreTradeProofPack:
    return _ensure_handoff_refs(
        proof_pack=proof_pack,
        proof_pack_repository=proof_pack_repository,
        include_report_input=include_report_input,
        include_ai_evidence_input=include_ai_evidence_input,
    )
