"""Persistence boundary for Manage-owned composite eligibility evidence."""

from __future__ import annotations

from typing import Protocol

from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipRevision,
)


class DpmCompositeConflictError(ValueError):
    """Raised when an immutable composite identity is replayed with different content."""


class DpmCompositeRepository(Protocol):
    def save_definition(self, *, definition: DpmCompositeDefinition) -> None:
        """Persist an immutable tenant-scoped definition revision."""

    def get_definition(
        self, *, tenant_id: str, composite_id: str, definition_version: str
    ) -> DpmCompositeDefinition | None:
        """Read one exact definition revision within its admitted tenant."""

    def list_definitions(
        self, *, tenant_id: str, limit: int, offset: int
    ) -> list[DpmCompositeDefinition]:
        """List definitions in deterministic newest-first version order."""

    def save_membership_revision(self, *, revision: DpmCompositeMembershipRevision) -> None:
        """Persist an immutable effective-dated membership snapshot."""

    def get_membership_revision(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
    ) -> DpmCompositeMembershipRevision | None:
        """Read one pinned membership revision within its admitted tenant."""

    def list_membership_revisions(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        limit: int,
        offset: int,
    ) -> list[DpmCompositeMembershipRevision]:
        """List immutable membership snapshots with deterministic pagination."""


__all__ = ["DpmCompositeConflictError", "DpmCompositeRepository"]
