from __future__ import annotations

from datetime import datetime, timezone

from src.core.proof_packs import (
    AI_EVIDENCE_REF_TYPE,
    REPORT_INPUT_REF_TYPE,
    build_ai_evidence_input,
    build_report_input,
)
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
    DpmProofPackStoredRef,
)
from src.core.proof_packs.repository import DpmProofPackRepository


def ensure_handoff_refs(
    *,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
    include_report_input: bool,
    include_ai_evidence_input: bool,
) -> DpmPreTradeProofPack:
    if include_report_input:
        report_input = build_report_input(proof_pack)
        append_handoff_ref(
            ref=report_input.evidence_ref,
            proof_pack=proof_pack,
            proof_pack_repository=proof_pack_repository,
        )
    if include_ai_evidence_input:
        ai_evidence_input = build_ai_evidence_input(proof_pack)
        append_handoff_ref(
            ref=ai_evidence_input.evidence_ref,
            proof_pack=proof_pack,
            proof_pack_repository=proof_pack_repository,
        )
    return hydrate_handoff_refs(
        proof_pack=proof_pack,
        proof_pack_repository=proof_pack_repository,
    )


def append_handoff_ref(
    *,
    ref: DpmProofPackEvidenceRef,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
) -> None:
    existing = find_stored_ref(
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


def hydrate_handoff_refs(
    *,
    proof_pack: DpmPreTradeProofPack,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmPreTradeProofPack:
    report_ref = proof_pack.report_input_ref
    ai_ref = proof_pack.ai_evidence_ref
    stored_report_ref = find_stored_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type=REPORT_INPUT_REF_TYPE,
        proof_pack_repository=proof_pack_repository,
    )
    stored_ai_ref = find_stored_ref(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type=AI_EVIDENCE_REF_TYPE,
        proof_pack_repository=proof_pack_repository,
    )
    if stored_report_ref is not None:
        report_ref = stored_ref_to_evidence_ref(stored_report_ref)
    if stored_ai_ref is not None:
        ai_ref = stored_ref_to_evidence_ref(stored_ai_ref)
    if report_ref == proof_pack.report_input_ref and ai_ref == proof_pack.ai_evidence_ref:
        return proof_pack
    return proof_pack.model_copy(
        update={
            "report_input_ref": report_ref,
            "ai_evidence_ref": ai_ref,
        }
    )


def find_stored_ref(
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


def stored_ref_to_evidence_ref(ref: DpmProofPackStoredRef) -> DpmProofPackEvidenceRef:
    return DpmProofPackEvidenceRef(
        ref_type=ref.ref_type,
        ref_id=ref.ref_id,
        source_system=ref.source_system,
        content_hash=ref.content_hash,
    )
