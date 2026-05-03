from __future__ import annotations

from copy import deepcopy
from threading import Lock

from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import ConstructionRepository


class InMemoryConstructionRepository(ConstructionRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._alternative_sets: dict[str, ConstructionAlternativeSet] = {}
        self._idempotency_index: dict[str, str] = {}
        self._selections: dict[str, ConstructionAlternativeSelection] = {}

    def save_alternative_set(
        self,
        *,
        alternative_set: ConstructionAlternativeSet,
        idempotency_key: str,
    ) -> None:
        with self._lock:
            self._alternative_sets[alternative_set.alternative_set_id] = deepcopy(alternative_set)
            self._idempotency_index[idempotency_key] = alternative_set.alternative_set_id

    def get_alternative_set(
        self,
        *,
        alternative_set_id: str,
    ) -> ConstructionAlternativeSet | None:
        with self._lock:
            row = self._alternative_sets.get(alternative_set_id)
            return deepcopy(row) if row is not None else None

    def get_alternative_set_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> ConstructionAlternativeSet | None:
        with self._lock:
            alternative_set_id = self._idempotency_index.get(idempotency_key)
            if alternative_set_id is None:
                return None
            row = self._alternative_sets.get(alternative_set_id)
            return deepcopy(row) if row is not None else None

    def save_selection(
        self,
        *,
        selection: ConstructionAlternativeSelection,
    ) -> None:
        with self._lock:
            self._selections[selection.alternative_set_id] = deepcopy(selection)

    def get_selection(
        self,
        *,
        alternative_set_id: str,
    ) -> ConstructionAlternativeSelection | None:
        with self._lock:
            row = self._selections.get(alternative_set_id)
            return deepcopy(row) if row is not None else None
