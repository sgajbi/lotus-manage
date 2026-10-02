"""Thread-safe development and test adapter for composite eligibility evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import TypeVar

from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipRevision,
)
from src.core.composite_repository import DpmCompositeConflictError, DpmCompositeRepository
from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationPage,
    DpmCompositePublicationReceipt,
    publication_from_revision,
)


KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


class InMemoryDpmCompositeRepository(DpmCompositeRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._definitions: dict[tuple[str, str, str], DpmCompositeDefinition] = {}
        self._membership_revisions: dict[
            tuple[str, str, str, str], DpmCompositeMembershipRevision
        ] = {}
        self._publications: dict[int, DpmCompositeMembershipPublication] = {}
        self._receipts: dict[tuple[str, int, str], DpmCompositePublicationReceipt] = {}
        self._last_sequence = 0

    def save_definition(self, *, definition: DpmCompositeDefinition) -> None:
        key = (definition.tenant_id, definition.composite_id, definition.definition_version)
        with self._lock:
            _save_immutable(
                values=self._definitions,
                key=key,
                value=definition,
                conflict_code="COMPOSITE_DEFINITION_IMMUTABLE_CONFLICT",
            )

    def get_definition(
        self, *, tenant_id: str, composite_id: str, definition_version: str
    ) -> DpmCompositeDefinition | None:
        with self._lock:
            definition = self._definitions.get((tenant_id, composite_id, definition_version))
            return deepcopy(definition) if definition is not None else None

    def list_definitions(
        self, *, tenant_id: str, limit: int, offset: int
    ) -> list[DpmCompositeDefinition]:
        with self._lock:
            definitions = sorted(
                (
                    definition
                    for (stored_tenant_id, _, _), definition in self._definitions.items()
                    if stored_tenant_id == tenant_id
                ),
                key=lambda definition: (
                    definition.inception_date,
                    definition.composite_id,
                    definition.definition_version,
                ),
                reverse=True,
            )
            return deepcopy(definitions[offset : offset + limit])

    def save_membership_revision(self, *, revision: DpmCompositeMembershipRevision) -> None:
        definition_key = (revision.tenant_id, revision.composite_id, revision.definition_version)
        revision_key = (*definition_key, revision.membership_revision)
        with self._lock:
            if definition_key not in self._definitions:
                raise DpmCompositeConflictError("COMPOSITE_MEMBERSHIP_DEFINITION_NOT_FOUND")
            if (
                revision.supersedes_membership_revision is not None
                and (*definition_key, revision.supersedes_membership_revision)
                not in self._membership_revisions
            ):
                raise DpmCompositeConflictError(
                    "COMPOSITE_MEMBERSHIP_SUPERSEDED_REVISION_NOT_FOUND"
                )
            newly_created = revision_key not in self._membership_revisions
            _save_immutable(
                values=self._membership_revisions,
                key=revision_key,
                value=revision,
                conflict_code="COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT",
            )
            if newly_created:
                self._last_sequence += 1
                self._publications[self._last_sequence] = publication_from_revision(
                    revision=revision,
                    sequence=self._last_sequence,
                    published_at=datetime.now(timezone.utc),
                )

    def get_membership_revision(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
    ) -> DpmCompositeMembershipRevision | None:
        with self._lock:
            revision = self._membership_revisions.get(
                (tenant_id, composite_id, definition_version, membership_revision)
            )
            return deepcopy(revision) if revision is not None else None

    def list_membership_revisions(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        limit: int,
        offset: int,
    ) -> list[DpmCompositeMembershipRevision]:
        with self._lock:
            revisions = sorted(
                (
                    revision
                    for (
                        stored_tenant_id,
                        stored_composite_id,
                        stored_definition_version,
                        _,
                    ), revision in self._membership_revisions.items()
                    if (stored_tenant_id, stored_composite_id, stored_definition_version)
                    == (tenant_id, composite_id, definition_version)
                ),
                key=lambda revision: (revision.decided_at, revision.membership_revision),
                reverse=True,
            )
            return deepcopy(revisions[offset : offset + limit])

    def get_publication(
        self, *, tenant_id: str, sequence: int
    ) -> DpmCompositeMembershipPublication | None:
        with self._lock:
            publication = self._publications.get(sequence)
            return (
                deepcopy(publication)
                if publication is not None and publication.tenant_id == tenant_id
                else None
            )

    def assert_membership_published(self, *, revision: DpmCompositeMembershipRevision) -> None:
        with self._lock:
            publications = (
                publication
                for publication in self._publications.values()
                if (
                    publication.tenant_id,
                    publication.composite_id,
                    publication.definition_version,
                    publication.membership_revision,
                )
                == (
                    revision.tenant_id,
                    revision.composite_id,
                    revision.definition_version,
                    revision.membership_revision,
                )
            )
            publication = next(publications, None)
            if publication is None or publication.membership_content_hash != revision.content_hash:
                raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT")

    def list_publications(
        self, *, tenant_id: str, after_sequence: int, limit: int
    ) -> DpmCompositePublicationPage:
        with self._lock:
            available = [
                publication
                for sequence, publication in sorted(self._publications.items())
                if publication.tenant_id == tenant_id
            ]
            high_watermark = available[-1].sequence if available else 0
            if after_sequence > high_watermark:
                raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_CURSOR_AHEAD")
            next_items = [
                publication for publication in available if publication.sequence > after_sequence
            ]
            items = next_items[:limit]
            return DpmCompositePublicationPage(
                items=deepcopy(items),
                high_watermark=high_watermark,
                next_sequence=items[-1].sequence if items else after_sequence,
                has_more=len(next_items) > limit,
            )

    def save_receipt(self, *, receipt: DpmCompositePublicationReceipt) -> bool:
        key = (receipt.tenant_id, receipt.publication_sequence, receipt.consumer_id)
        with self._lock:
            publication = self._publications.get(receipt.publication_sequence)
            if publication is None or publication.tenant_id != receipt.tenant_id:
                raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_NOT_FOUND")
            if publication.membership_content_hash != receipt.membership_content_hash:
                raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_HASH_MISMATCH")
            existing = self._receipts.get(key)
            if existing is not None:
                if (
                    existing.disposition != receipt.disposition
                    or existing.reason_code != receipt.reason_code
                    or existing.receipt_evidence_hash != receipt.receipt_evidence_hash
                ):
                    raise DpmCompositeConflictError("COMPOSITE_RECEIPT_IMMUTABLE_CONFLICT")
                return False
            self._receipts[key] = deepcopy(receipt)
            return True

    def list_receipts(
        self, *, tenant_id: str, publication_sequence: int
    ) -> list[DpmCompositePublicationReceipt]:
        with self._lock:
            return deepcopy(
                sorted(
                    (
                        receipt
                        for (stored_tenant, sequence, _), receipt in self._receipts.items()
                        if stored_tenant == tenant_id and sequence == publication_sequence
                    ),
                    key=lambda receipt: receipt.consumer_id,
                )
            )


def _save_immutable(
    *, values: dict[KeyT, ValueT], key: KeyT, value: ValueT, conflict_code: str
) -> None:
    existing = values.get(key)
    if existing is not None and existing != value:
        raise DpmCompositeConflictError(conflict_code)
    if existing is None:
        values[key] = deepcopy(value)


__all__ = ["InMemoryDpmCompositeRepository"]
