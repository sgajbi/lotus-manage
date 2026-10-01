"""Thread-safe development and test adapter for composite eligibility evidence."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import TypeVar

from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipRevision,
)
from src.core.composite_repository import DpmCompositeConflictError, DpmCompositeRepository


KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


class InMemoryDpmCompositeRepository(DpmCompositeRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._definitions: dict[tuple[str, str, str], DpmCompositeDefinition] = {}
        self._membership_revisions: dict[
            tuple[str, str, str, str], DpmCompositeMembershipRevision
        ] = {}

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
            _save_immutable(
                values=self._membership_revisions,
                key=revision_key,
                value=revision,
                conflict_code="COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT",
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


def _save_immutable(
    *, values: dict[KeyT, ValueT], key: KeyT, value: ValueT, conflict_code: str
) -> None:
    existing = values.get(key)
    if existing is not None and existing != value:
        raise DpmCompositeConflictError(conflict_code)
    if existing is None:
        values[key] = deepcopy(value)


__all__ = ["InMemoryDpmCompositeRepository"]
