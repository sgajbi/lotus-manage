from collections.abc import Iterable
from typing import Protocol

from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext

AuthorityContextUpdate = tuple[str, object]


class AuthorityContextUpdateBuilder(Protocol):
    def __call__(
        self,
        *,
        source_context: DpmCoreExecutionContext,
        authority_context: ConstructionAuthorityContext,
    ) -> AuthorityContextUpdate | None: ...


def collect_authority_context_updates(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
    update_builders: Iterable[AuthorityContextUpdateBuilder],
) -> dict[str, object]:
    context_updates: dict[str, object] = {}
    for update_builder in update_builders:
        update = update_builder(
            source_context=source_context,
            authority_context=authority_context,
        )
        if update is not None:
            context_key, context_value = update
            context_updates[context_key] = context_value
    return context_updates


def merge_authority_context_update_maps(
    *update_maps: dict[str, object],
) -> dict[str, object]:
    context_updates: dict[str, object] = {}
    for update_map in update_maps:
        context_updates.update(update_map)
    return context_updates


__all__ = [
    "AuthorityContextUpdate",
    "AuthorityContextUpdateBuilder",
    "collect_authority_context_updates",
    "merge_authority_context_update_maps",
]
