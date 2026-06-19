from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _ProofPackListFilters:
    portfolio_id: str | None
    mandate_id: str | None
    status: str | None


def _ensure_proof_pack_content_is_immutable(
    *,
    existing: DpmPreTradeProofPack | None,
    proof_pack: DpmPreTradeProofPack,
) -> None:
    if existing is not None and existing.content_hash != proof_pack.content_hash:
        raise DpmProofPackConflictError("DPM_PROOF_PACK_IMMUTABLE_CONFLICT")


def _idempotency_binding(
    *,
    idempotency_key: str | None,
    existing_proof_pack_id: str | None,
    proof_pack_id: str,
) -> tuple[str, str] | None:
    if idempotency_key is None:
        return None
    if existing_proof_pack_id is not None and existing_proof_pack_id != proof_pack_id:
        raise DpmProofPackConflictError("DPM_PROOF_PACK_IDEMPOTENCY_CONFLICT")
    return idempotency_key, proof_pack_id


def _retention_metadata(
    *,
    proof_pack_id: str,
    retention_expires_at: datetime | None,
) -> DpmProofPackRetentionMetadata:
    return DpmProofPackRetentionMetadata(
        proof_pack_id=proof_pack_id,
        retention_policy=RETENTION_POLICY_PRE_TRADE_PROOF_PACK,
        retention_expires_at=(
            retention_expires_at.isoformat() if retention_expires_at is not None else None
        ),
    )


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
            _ensure_proof_pack_content_is_immutable(existing=existing, proof_pack=proof_pack)
            binding = _idempotency_binding(
                idempotency_key=idempotency_key,
                existing_proof_pack_id=(
                    self._idempotency_index.get(idempotency_key)
                    if idempotency_key is not None
                    else None
                ),
                proof_pack_id=proof_pack.proof_pack_id,
            )
            if binding is not None:
                self._idempotency_index[binding[0]] = binding[1]
            self._proof_packs[proof_pack.proof_pack_id] = deepcopy(proof_pack)
            self._retention[proof_pack.proof_pack_id] = _retention_metadata(
                proof_pack_id=proof_pack.proof_pack_id,
                retention_expires_at=retention_expires_at,
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
            page = _list_proof_packs(
                proof_packs=list(self._proof_packs.values()),
                filters=_ProofPackListFilters(
                    portfolio_id=portfolio_id,
                    mandate_id=mandate_id,
                    status=status,
                ),
                limit=limit,
                offset=offset,
            )
            return deepcopy(page)

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


def _list_proof_packs(
    *,
    proof_packs: list[DpmPreTradeProofPack],
    filters: _ProofPackListFilters,
    limit: int,
    offset: int,
) -> list[DpmPreTradeProofPack]:
    matched = [
        proof_pack
        for proof_pack in proof_packs
        if _proof_pack_matches_filters(proof_pack=proof_pack, filters=filters)
    ]
    matched.sort(key=_proof_pack_sort_key, reverse=True)
    return matched[offset : offset + limit]


def _proof_pack_matches_filters(
    *,
    proof_pack: DpmPreTradeProofPack,
    filters: _ProofPackListFilters,
) -> bool:
    return (
        _optional_match(filters.portfolio_id, proof_pack.portfolio_id)
        and _optional_match(filters.mandate_id, proof_pack.mandate_id)
        and _optional_match(filters.status, proof_pack.status)
    )


def _optional_match(expected: str | None, actual: str | None) -> bool:
    return expected is None or actual == expected


def _proof_pack_sort_key(proof_pack: DpmPreTradeProofPack) -> tuple[datetime, str]:
    return proof_pack.created_at, proof_pack.proof_pack_id
