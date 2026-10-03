from __future__ import annotations

from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.proof_packs.identity import ProofPackSourceValidationError
from src.core.proof_packs.supportability import is_no_action_proof_pack


def find_replayable_proof_pack(
    *,
    proof_pack_id: str,
    idempotency_key: str | None,
    proof_pack_repository: DpmProofPackRepository,
    tenant_id: str,
) -> DpmPreTradeProofPack | None:
    if idempotency_key is not None:
        existing = proof_pack_repository.get_proof_pack_by_idempotency(
            idempotency_key=idempotency_key,
            tenant_id=tenant_id,
        )
        if existing is not None:
            return _require_economic_source(existing)
    existing = proof_pack_repository.get_proof_pack(
        proof_pack_id=proof_pack_id,
        tenant_id=tenant_id,
    )
    return _require_economic_source(existing) if existing is not None else None


def _require_economic_source(proof_pack: DpmPreTradeProofPack) -> DpmPreTradeProofPack:
    if is_no_action_proof_pack(proof_pack) and proof_pack.rebalance_run_id is not None:
        raise ProofPackSourceValidationError("DPM_NO_ACTION_EVALUATION_RUN_NOT_ECONOMIC_SOURCE")
    return proof_pack
