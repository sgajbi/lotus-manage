from __future__ import annotations

from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.proof_packs.repository import DpmProofPackRepository


def find_replayable_proof_pack(
    *,
    proof_pack_id: str,
    idempotency_key: str | None,
    proof_pack_repository: DpmProofPackRepository,
) -> DpmPreTradeProofPack | None:
    if idempotency_key is not None:
        existing = proof_pack_repository.get_proof_pack_by_idempotency(
            idempotency_key=idempotency_key
        )
        if existing is not None:
            return existing
    return proof_pack_repository.get_proof_pack(proof_pack_id=proof_pack_id)
