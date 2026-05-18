"""Persistence contracts for RFC-0039 construction alternative sets."""

from typing import Protocol

from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)


class ConstructionAlternativeSetNotFoundError(Exception):
    """Raised when an alternative set does not exist."""


class ConstructionAlternativeNotFoundError(Exception):
    """Raised when a selection references an unknown alternative."""


class ConstructionIdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused for a different request hash."""


class ConstructionRepository(Protocol):
    def save_alternative_set(
        self,
        *,
        alternative_set: ConstructionAlternativeSet,
        idempotency_key: str,
    ) -> None:
        """Persist an alternative set and its idempotency lookup."""

    def get_alternative_set(
        self,
        *,
        alternative_set_id: str,
    ) -> ConstructionAlternativeSet | None:
        """Return an alternative set by identifier, or None when absent."""

    def get_alternative_set_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> ConstructionAlternativeSet | None:
        """Return the alternative set previously associated with an idempotency key."""

    def list_alternative_sets(
        self,
        *,
        portfolio_id: str,
        limit: int,
    ) -> list[ConstructionAlternativeSet]:
        """Return recent alternative sets for a portfolio, newest first."""

    def save_selection(
        self,
        *,
        selection: ConstructionAlternativeSelection,
    ) -> None:
        """Persist a selection decision for an alternative set."""

    def get_selection(
        self,
        *,
        alternative_set_id: str,
    ) -> ConstructionAlternativeSelection | None:
        """Return the latest selection decision for an alternative set."""
