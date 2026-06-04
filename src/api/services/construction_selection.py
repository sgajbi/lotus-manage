import uuid

from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import ConstructionAlternativeNotFoundError


def build_construction_selection(
    *,
    alternative_set: ConstructionAlternativeSet,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str | None,
    selection_id: str | None = None,
) -> ConstructionAlternativeSelection:
    if alternative_id not in construction_alternative_ids(alternative_set=alternative_set):
        raise ConstructionAlternativeNotFoundError("CONSTRUCTION_ALTERNATIVE_NOT_FOUND")
    return ConstructionAlternativeSelection(
        selection_id=selection_id or f"casel_{uuid.uuid4().hex[:12]}",
        alternative_set_id=alternative_set.alternative_set_id,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )


def construction_alternative_ids(
    *,
    alternative_set: ConstructionAlternativeSet,
) -> set[str]:
    return {alternative.alternative_id for alternative in alternative_set.alternatives}


__all__ = [
    "build_construction_selection",
    "construction_alternative_ids",
]
