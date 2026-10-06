"""Persistence boundary for Manage-owned composite eligibility evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from src.core.composite_membership import (
    DpmCompositeMembershipRevision,
)
from src.core.composite_definition_versions import CompositeDefinition
from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationPage,
    DpmCompositePublicationReceipt,
)
from src.core.composite_universe import DpmCompositeUniverseAttestation


class DpmCompositeConflictError(ValueError):
    """Raised when an immutable composite identity is replayed with different content."""


ItemT = TypeVar("ItemT")


@dataclass(frozen=True)
class DpmCompositeResultPage(Generic[ItemT]):
    """One tenant-scoped page and its total count from the same read snapshot."""

    items: list[ItemT]
    count: int


class DpmCompositeRepository(Protocol):
    def save_definition(self, *, definition: CompositeDefinition) -> None:
        """Persist an immutable tenant-scoped definition revision."""

    def get_definition(
        self, *, tenant_id: str, composite_id: str, definition_version: str
    ) -> CompositeDefinition | None:
        """Read one exact definition revision within its admitted tenant."""

    def list_definitions(
        self, *, tenant_id: str, limit: int, offset: int
    ) -> DpmCompositeResultPage[CompositeDefinition]:
        """List definitions and total tenant count in one read snapshot."""

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
    ) -> DpmCompositeResultPage[DpmCompositeMembershipRevision]:
        """List immutable revisions and total scoped count in one read snapshot."""

    def get_publication(
        self, *, tenant_id: str, sequence: int
    ) -> DpmCompositeMembershipPublication | None:
        """Read one immutable publication within its tenant."""

    def list_publications(
        self, *, tenant_id: str, after_sequence: int, limit: int
    ) -> DpmCompositePublicationPage:
        """Traverse committed tenant publications under a stable page watermark."""

    def save_receipt(self, *, receipt: DpmCompositePublicationReceipt) -> bool:
        """Persist one consumer acknowledgement; replay or conflict by immutable identity."""

    def assert_membership_published(self, *, revision: DpmCompositeMembershipRevision) -> None:
        """Fail closed when an immutable revision lacks matching publication evidence."""

    def list_receipts(
        self, *, tenant_id: str, publication_sequence: int
    ) -> list[DpmCompositePublicationReceipt]:
        """Inspect bounded consumer acknowledgements for one publication."""

    def save_universe_attestation(self, *, attestation: DpmCompositeUniverseAttestation) -> None:
        """Persist immutable completeness evidence for one membership revision."""

    def get_universe_attestation(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
        attestation_version: str,
    ) -> DpmCompositeUniverseAttestation | None:
        """Read one pinned tenant-owned universe attestation."""

    def list_universe_attestations(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
        limit: int,
        offset: int,
    ) -> DpmCompositeResultPage[DpmCompositeUniverseAttestation]:
        """List immutable attestations and total scoped count in one snapshot."""


__all__ = ["DpmCompositeConflictError", "DpmCompositeRepository", "DpmCompositeResultPage"]
