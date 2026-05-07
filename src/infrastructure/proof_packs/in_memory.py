from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import Lock

from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackRetentionMetadata,
    DpmProofPackStoredRef,
)
from src.core.proof_packs.repository import (
    DpmProofPackConflictError,
    DpmProofPackRepository,
)

RETENTION_POLICY_PRE_TRADE_PROOF_PACK = "DPM_PRE_TRADE_PROOF_PACK_7Y"


class InMemoryDpmProofPackRepository(DpmProofPackRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._proof_packs: dict[str, DpmPreTradeProofPack] = {}
        self._idempotency_index: dict[str, str] = {}
        self._retention: dict[str, DpmProofPackRetentionMetadata] = {}
        self._refs: dict[str, list[DpmProofPackStoredRef]] = {}

    def save_proof_pack(
        self,
        *,
        proof_pack: DpmPreTradeProofPack,
        idempotency_key: str | None,
        retention_expires_at: datetime | None,
    ) -> None:
        with self._lock:
            existing = self._proof_packs.get(proof_pack.proof_pack_id)
            if existing is not None and existing.content_hash != proof_pack.content_hash:
                raise DpmProofPackConflictError("DPM_PROOF_PACK_IMMUTABLE_CONFLICT")
            if idempotency_key is not None:
                existing_id = self._idempotency_index.get(idempotency_key)
                if existing_id is not None and existing_id != proof_pack.proof_pack_id:
                    raise DpmProofPackConflictError("DPM_PROOF_PACK_IDEMPOTENCY_CONFLICT")
                self._idempotency_index[idempotency_key] = proof_pack.proof_pack_id
            self._proof_packs[proof_pack.proof_pack_id] = deepcopy(proof_pack)
            self._retention[proof_pack.proof_pack_id] = DpmProofPackRetentionMetadata(
                proof_pack_id=proof_pack.proof_pack_id,
                retention_policy=RETENTION_POLICY_PRE_TRADE_PROOF_PACK,
                retention_expires_at=(
                    retention_expires_at.isoformat() if retention_expires_at is not None else None
                ),
            )

    def get_proof_pack(self, *, proof_pack_id: str) -> DpmPreTradeProofPack | None:
        with self._lock:
            row = self._proof_packs.get(proof_pack_id)
            return deepcopy(row) if row is not None else None

    def get_proof_pack_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> DpmPreTradeProofPack | None:
        with self._lock:
            proof_pack_id = self._idempotency_index.get(idempotency_key)
            if proof_pack_id is None:
                return None
            row = self._proof_packs.get(proof_pack_id)
            return deepcopy(row) if row is not None else None

    def list_proof_packs(
        self,
        *,
        portfolio_id: str | None = None,
        mandate_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPreTradeProofPack]:
        with self._lock:
            proof_packs = [
                proof_pack
                for proof_pack in self._proof_packs.values()
                if (portfolio_id is None or proof_pack.portfolio_id == portfolio_id)
                and (mandate_id is None or proof_pack.mandate_id == mandate_id)
                and (status is None or proof_pack.status == status)
            ]
            proof_packs.sort(
                key=lambda proof_pack: (proof_pack.created_at, proof_pack.proof_pack_id),
                reverse=True,
            )
            return deepcopy(proof_packs[offset : offset + limit])

    def get_retention_metadata(
        self,
        *,
        proof_pack_id: str,
    ) -> DpmProofPackRetentionMetadata | None:
        with self._lock:
            row = self._retention.get(proof_pack_id)
            return deepcopy(row) if row is not None else None

    def append_ref(self, *, ref: DpmProofPackStoredRef) -> None:
        with self._lock:
            if ref.proof_pack_id not in self._proof_packs:
                return
            refs = self._refs.setdefault(ref.proof_pack_id, [])
            if ref not in refs:
                refs.append(deepcopy(ref))

    def list_refs(self, *, proof_pack_id: str) -> list[DpmProofPackStoredRef]:
        with self._lock:
            return deepcopy(self._refs.get(proof_pack_id, []))
