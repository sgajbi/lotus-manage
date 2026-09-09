"""Persistence contracts for RFC-0040 proof packs."""

from datetime import datetime
from typing import Protocol

from src.core.common.derived_identity import derived_identity
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackRetentionMetadata,
    DpmProofPackStoredRef,
)


class DpmProofPackNotFoundError(Exception):
    """Raised when a proof pack does not exist."""


class DpmProofPackConflictError(Exception):
    """Raised when immutable proof-pack identity or idempotency conflicts."""


def proof_pack_idempotency_mapping_key(*, tenant_id: str, idempotency_key: str) -> str:
    """Namespace a caller-chosen proof-pack replay key by admitted tenant."""

    return derived_identity("pik", tenant_id, idempotency_key)


def require_proof_pack_tenant(
    *, proof_pack: DpmPreTradeProofPack, tenant_id: str
) -> DpmPreTradeProofPack:
    """Require the built aggregate to agree with admitted write authority."""

    if proof_pack.tenant_id != tenant_id:
        raise DpmProofPackConflictError("DPM_PROOF_PACK_TENANT_MISMATCH")
    return proof_pack


class DpmProofPackRepository(Protocol):
    def save_proof_pack(
        self,
        *,
        proof_pack: DpmPreTradeProofPack,
        idempotency_key: str | None,
        retention_expires_at: datetime | None,
        tenant_id: str,
    ) -> None:
        """Persist an immutable proof pack."""

    def get_proof_pack(self, *, proof_pack_id: str, tenant_id: str) -> DpmPreTradeProofPack | None:
        """Return a proof pack by id, or None when absent."""

    def get_proof_pack_by_idempotency(
        self,
        *,
        idempotency_key: str,
        tenant_id: str,
    ) -> DpmPreTradeProofPack | None:
        """Return the proof pack associated with an idempotency key."""

    def list_proof_packs(
        self,
        *,
        tenant_id: str,
        portfolio_id: str | None = None,
        mandate_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPreTradeProofPack]:
        """Return a bounded page of proof packs matching optional search filters."""

    def get_retention_metadata(
        self,
        *,
        proof_pack_id: str,
    ) -> DpmProofPackRetentionMetadata | None:
        """Return retention metadata for a proof pack."""

    def append_ref(self, *, ref: DpmProofPackStoredRef) -> None:
        """Append a post-creation reference without mutating the proof-pack body."""

    def list_refs(self, *, proof_pack_id: str) -> list[DpmProofPackStoredRef]:
        """Return append-only refs for a proof pack."""
