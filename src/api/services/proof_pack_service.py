from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from src.core.construction.repository import ConstructionRepository
from src.core.proof_packs import (
    AI_EVIDENCE_REF_TYPE,
    REPORT_INPUT_REF_TYPE,
    ProofPackSourceValidationError,
    build_ai_evidence_input,
    build_proof_pack_from_run,
    build_proof_pack_from_selected_alternative,
    build_report_input,
)
from src.core.proof_packs.handoffs import DpmProofPackAiEvidenceInput, DpmProofPackReportInput
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
    DpmProofPackStoredRef,
)
from src.core.proof_packs.repository import (
    DpmProofPackConflictError,
    DpmProofPackRepository,
)
from src.core.rebalance_runs.service import DpmRunNotFoundError, DpmRunSupportService

PROOF_PACK_RETENTION_DAYS = 365 * 7


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
    proof_pack_repository: DpmProofPackRepository,
) -> DpmPreTradeProofPack:
    if idempotency_key is not None:
        existing = proof_pack_repository.get_proof_pack_by_idempotency(
            idempotency_key=idempotency_key
        )
        if existing is not None:
            return existing
    run = run_service.get_run_record(rebalance_run_id=rebalance_run_id)
    proof_pack = build_proof_pack_from_run(
        run=run,
        created_by=actor_id,
        reason=reason,
        correlation_id=correlation_id,
        mandate_id=mandate_id,
        workflow_decisions=run_service.list_workflow_decision_records(
            rebalance_run_id=rebalance_run_id
        ),
    )
    _persist(
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
    proof_pack_repository: DpmProofPackRepository,
) -> DpmPreTradeProofPack:
    if idempotency_key is not None:
        existing = proof_pack_repository.get_proof_pack_by_idempotency(
            idempotency_key=idempotency_key
        )
        if existing is not None:
            return existing
    alternative_set = construction_repository.get_alternative_set(
        alternative_set_id=alternative_set_id
    )
    if alternative_set is None:
        raise ProofPackSourceValidationError("DPM_ALTERNATIVE_SET_NOT_FOUND")
    selection = construction_repository.get_selection(alternative_set_id=alternative_set_id)
    selected = next(
        (
            alternative
            for alternative in alternative_set.alternatives
            if alternative.alternative_id == selected_alternative_id
        ),
        None,
    )
    if selected is None:
        raise ProofPackSourceValidationError("DPM_SELECTED_ALTERNATIVE_NOT_FOUND")
    run = None
    workflow_decisions = []
    if selected.rebalance_run_id is not None:
        try:
            run = run_service.get_run_record(rebalance_run_id=selected.rebalance_run_id)
            workflow_decisions = run_service.list_workflow_decision_records(
                rebalance_run_id=selected.rebalance_run_id
            )
        except DpmRunNotFoundError:
            run = None
            workflow_decisions = []
    proof_pack = build_proof_pack_from_selected_alternative(
        alternative_set=alternative_set,
        selected_alternative_id=selected_alternative_id,
        run=run,
        selection=selection,
        created_by=actor_id,
        reason=reason,
        correlation_id=correlation_id,
        mandate_id=mandate_id,
        workflow_decisions=workflow_decisions,
    )
    _persist(
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
    return _hydrate_handoff_refs(
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
    if proof_pack.report_input_ref is None:
        stored_ref = _find_stored_ref(
            proof_pack_id=proof_pack_id,
            ref_type=REPORT_INPUT_REF_TYPE,
            proof_pack_repository=proof_pack_repository,
        )
        if stored_ref is None:
            raise DpmProofPackReportInputNotGeneratedError(
                "DPM_PROOF_PACK_REPORT_INPUT_NOT_GENERATED"
            )
        return _stored_ref_to_evidence_ref(stored_ref)
    return proof_pack.report_input_ref


def get_ai_evidence_ref(
    *,
    proof_pack_id: str,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmProofPackEvidenceRef:
    proof_pack = get_proof_pack(
        proof_pack_id=proof_pack_id,
        proof_pack_repository=proof_pack_repository,
    )
    if proof_pack.ai_evidence_ref is None:
        stored_ref = _find_stored_ref(
            proof_pack_id=proof_pack_id,
            ref_type=AI_EVIDENCE_REF_TYPE,
            proof_pack_repository=proof_pack_repository,
        )
        if stored_ref is None:
            raise DpmProofPackAiEvidenceInputNotGeneratedError(
                "DPM_PROOF_PACK_AI_EVIDENCE_INPUT_NOT_GENERATED"
            )
        return _stored_ref_to_evidence_ref(stored_ref)
    return proof_pack.ai_evidence_ref


def get_report_input(
    *,
    proof_pack_id: str,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmProofPackReportInput:
    return build_report_input(
        get_proof_pack(
            proof_pack_id=proof_pack_id,
            proof_pack_repository=proof_pack_repository,
        )
    )


def get_ai_evidence_input(
    *,
    proof_pack_id: str,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmProofPackAiEvidenceInput:
    return build_ai_evidence_input(
        get_proof_pack(
            proof_pack_id=proof_pack_id,
            proof_pack_repository=proof_pack_repository,
        )
    )


def ensure_handoff_refs(
    *,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
    include_report_input: bool,
    include_ai_evidence_input: bool,
) -> DpmPreTradeProofPack:
    if include_report_input:
        report_input = build_report_input(proof_pack)
        _append_handoff_ref(
            ref=report_input.evidence_ref,
            proof_pack=proof_pack,
            proof_pack_repository=proof_pack_repository,
        )
    if include_ai_evidence_input:
        ai_evidence_input = build_ai_evidence_input(proof_pack)
        _append_handoff_ref(
            ref=ai_evidence_input.evidence_ref,
            proof_pack=proof_pack,
            proof_pack_repository=proof_pack_repository,
        )
    return _hydrate_handoff_refs(
        proof_pack=proof_pack,
        proof_pack_repository=proof_pack_repository,
    )


def to_api_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, DpmProofPackConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, DpmRunNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ProofPackSourceValidationError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (
            DpmProofPackReportInputNotGeneratedError,
            DpmProofPackAiEvidenceInputNotGeneratedError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=type(exc).__name__
    )


def _persist(
    *,
    proof_pack_repository: DpmProofPackRepository,
    proof_pack: DpmPreTradeProofPack,
    idempotency_key: str | None,
) -> None:
    proof_pack_repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=idempotency_key,
        retention_expires_at=datetime.now(timezone.utc) + timedelta(days=PROOF_PACK_RETENTION_DAYS),
    )


def _append_handoff_ref(
    *,
    ref: DpmProofPackEvidenceRef,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
) -> None:
    existing = _find_stored_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type=ref.ref_type,
        proof_pack_repository=proof_pack_repository,
    )
    if existing is not None and existing.content_hash == ref.content_hash:
        return
    proof_pack_repository.append_ref(
        ref=DpmProofPackStoredRef(
            proof_pack_id=proof_pack.proof_pack_id,
            ref_type=ref.ref_type,
            ref_id=ref.ref_id,
            source_system=ref.source_system,
            content_hash=ref.content_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )


def _hydrate_handoff_refs(
    *,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmPreTradeProofPack:
    report_ref = proof_pack.report_input_ref
    ai_ref = proof_pack.ai_evidence_ref
    stored_report_ref = _find_stored_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type=REPORT_INPUT_REF_TYPE,
        proof_pack_repository=proof_pack_repository,
    )
    stored_ai_ref = _find_stored_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type=AI_EVIDENCE_REF_TYPE,
        proof_pack_repository=proof_pack_repository,
    )
    if stored_report_ref is not None:
        report_ref = _stored_ref_to_evidence_ref(stored_report_ref)
    if stored_ai_ref is not None:
        ai_ref = _stored_ref_to_evidence_ref(stored_ai_ref)
    if report_ref == proof_pack.report_input_ref and ai_ref == proof_pack.ai_evidence_ref:
        return proof_pack
    return proof_pack.model_copy(
        update={
            "report_input_ref": report_ref,
            "ai_evidence_ref": ai_ref,
        }
    )


def _find_stored_ref(
    *,
    proof_pack_id: str,
    ref_type: str,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmProofPackStoredRef | None:
    return next(
        (
            ref
            for ref in reversed(proof_pack_repository.list_refs(proof_pack_id=proof_pack_id))
            if ref.ref_type == ref_type
        ),
        None,
    )


def _stored_ref_to_evidence_ref(ref: DpmProofPackStoredRef) -> DpmProofPackEvidenceRef:
    return DpmProofPackEvidenceRef(
        ref_type=ref.ref_type,
        ref_id=ref.ref_id,
        source_system=ref.source_system,
        content_hash=ref.content_hash,
    )
