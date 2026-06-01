from src.core.construction.models import ConstructionAlternativeSet


def proposed_changes_from_alternative_set(
    alternative_set: ConstructionAlternativeSet,
) -> list[dict[str, object]]:
    for alternative in alternative_set.alternatives:
        changes = alternative.diagnostics.get("proposed_changes")
        if isinstance(changes, list) and changes:
            return [change for change in changes if isinstance(change, dict)]
    return []


__all__ = ["proposed_changes_from_alternative_set"]
