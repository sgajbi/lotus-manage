from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from collections.abc import Iterator
from threading import RLock

from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import ConstructionRepository
from src.core.construction.repository import (
    ConstructionAlternativeSetNotFoundError,
    ConstructionIdempotencyConflictError,
    require_construction_tenant_id,
)


class InMemoryConstructionRepository(ConstructionRepository):
    def __init__(self) -> None:
        self._lock = RLock()
        self._alternative_sets: dict[str, ConstructionAlternativeSet] = {}
        self._idempotency_index: dict[tuple[str, str], str] = {}
        self._selections: dict[str, ConstructionAlternativeSelection] = {}

    @contextmanager
    def idempotency_guard(self, *, tenant_id: str, idempotency_key: str) -> Iterator[None]:
        del tenant_id, idempotency_key
        with self._lock:
            yield

    def save_alternative_set(
        self,
        *,
        alternative_set: ConstructionAlternativeSet,
        idempotency_key: str,
    ) -> ConstructionAlternativeSet:
        tenant_id = require_construction_tenant_id(alternative_set.tenant_id)
        owned_set = alternative_set.model_copy(update={"tenant_id": tenant_id})
        with self._lock:
            key = (tenant_id, idempotency_key)
            existing_id = self._idempotency_index.get(key)
            if existing_id is not None:
                return deepcopy(self._alternative_sets[existing_id])
            if owned_set.alternative_set_id in self._alternative_sets:
                raise ConstructionIdempotencyConflictError(
                    "CONSTRUCTION_ALTERNATIVE_SET_ID_CONFLICT"
                )
            self._alternative_sets[owned_set.alternative_set_id] = deepcopy(owned_set)
            self._idempotency_index[key] = owned_set.alternative_set_id
            return deepcopy(owned_set)

    def get_alternative_set(
        self,
        *,
        alternative_set_id: str,
        tenant_id: str,
    ) -> ConstructionAlternativeSet | None:
        with self._lock:
            row = self._alternative_sets.get(alternative_set_id)
            return deepcopy(row) if row is not None and row.tenant_id == tenant_id else None

    def get_alternative_set_by_idempotency(
        self,
        *,
        idempotency_key: str,
        tenant_id: str,
    ) -> ConstructionAlternativeSet | None:
        with self._lock:
            alternative_set_id = self._idempotency_index.get((tenant_id, idempotency_key))
            if alternative_set_id is None:
                return None
            row = self._alternative_sets.get(alternative_set_id)
            return deepcopy(row) if row is not None else None

    def list_alternative_sets(
        self,
        *,
        portfolio_id: str,
        tenant_id: str,
        limit: int,
    ) -> list[ConstructionAlternativeSet]:
        with self._lock:
            rows = [
                deepcopy(row)
                for row in self._alternative_sets.values()
                if row.portfolio_id == portfolio_id and row.tenant_id == tenant_id
            ]
        return sorted(
            rows,
            key=lambda row: (row.generated_at, row.alternative_set_id),
            reverse=True,
        )[:limit]

    def save_selection(
        self,
        *,
        selection: ConstructionAlternativeSelection,
    ) -> None:
        tenant_id = require_construction_tenant_id(selection.tenant_id)
        with self._lock:
            alternative_set = self._alternative_sets.get(selection.alternative_set_id)
            if alternative_set is None or alternative_set.tenant_id != tenant_id:
                raise ConstructionAlternativeSetNotFoundError(
                    "CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND"
                )
            current = self._selections.get(selection.alternative_set_id)
            if current is not None and current.tenant_id != tenant_id:
                raise ConstructionAlternativeSetNotFoundError(
                    "CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND"
                )
            self._selections[selection.alternative_set_id] = deepcopy(
                selection.model_copy(update={"tenant_id": tenant_id})
            )

    def get_selection(
        self,
        *,
        alternative_set_id: str,
        tenant_id: str,
    ) -> ConstructionAlternativeSelection | None:
        with self._lock:
            row = self._selections.get(alternative_set_id)
            return deepcopy(row) if row is not None and row.tenant_id == tenant_id else None
