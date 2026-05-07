"""Persistence contracts for RFC-0040 proof packs."""

from datetime import datetime
from typing import Protocol

from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackRetentionMetadata,
    DpmProofPackStoredRef,
)


class DpmProofPackNotFoundError(Exception):
    """Raised when a proof pack does not exist."""


class DpmProofPackConflictError(Exception):
    """Raised when immutable proof-pack identity or idempotency conflicts."""


class DpmProofPackRepository(Protocol):
    def save_proof_pack(
        self,
        *,
        proof_pack: DpmPreTradeProofPack,
        idempotency_key: str | None,
        retention_expires_at: datetime | None,
    ) -> None:
        """Persist an immutable proof pack."""

    def get_proof_pack(self, *, proof_pack_id: str) -> DpmPreTradeProofPack | None:
        """Return a proof pack by id, or None when absent."""

    def get_proof_pack_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> DpmPreTradeProofPack | None:
        """Return the proof pack associated with an idempotency key."""

    def list_proof_packs(
        self,
        *,
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
