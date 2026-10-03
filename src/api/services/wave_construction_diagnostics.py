from src.core.construction.models import ConstructionAlternativeSet


def proposed_changes_from_alternative_set(
    alternative_set: ConstructionAlternativeSet,
    *,
    selected_alternative_id: str | None = None,
) -> list[dict[str, object]]:
    for alternative in alternative_set.alternatives:
        if (
            selected_alternative_id is not None
            and alternative.alternative_id != selected_alternative_id
        ):
            continue
        changes = alternative.diagnostics.get("proposed_changes")
        if isinstance(changes, list) and changes:
            return [change for change in changes if isinstance(change, dict)]
    return []


__all__ = ["proposed_changes_from_alternative_set"]
