from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.proof_packs.repository import DpmProofPackRepository

PROOF_PACK_RETENTION_DAYS = 365 * 7


def persist_proof_pack(
    *,
    proof_pack_repository: DpmProofPackRepository,
    proof_pack: DpmPreTradeProofPack,
    idempotency_key: str | None,
    persisted_at: datetime | None = None,
) -> None:
    retention_base = persisted_at or datetime.now(timezone.utc)
    proof_pack_repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=idempotency_key,
        retention_expires_at=retention_base + timedelta(days=PROOF_PACK_RETENTION_DAYS),
    )


__all__ = ["PROOF_PACK_RETENTION_DAYS", "persist_proof_pack"]
