from typing import Any, cast

from src.api.services import construction_authority_context_updates
from src.api.services.construction_authority_context_updates import (
    AuthorityContextUpdate,
    collect_authority_context_updates,
    merge_authority_context_update_maps,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext


def test_authority_context_updates_exports_collector_surface() -> None:
    assert construction_authority_context_updates.__all__ == [
        "AuthorityContextUpdate",
        "AuthorityContextUpdateBuilder",
        "collect_authority_context_updates",
        "merge_authority_context_update_maps",
    ]


def _source_context() -> DpmCoreExecutionContext:
    return DpmCoreExecutionContext.model_construct(**cast(dict[str, Any], {}))


def test_collect_authority_context_updates_skips_absent_updates() -> None:
    def missing_update(
        *,
        source_context: DpmCoreExecutionContext,
        authority_context: ConstructionAuthorityContext,
    ) -> AuthorityContextUpdate | None:
        return None

    def present_update(
        *,
        source_context: DpmCoreExecutionContext,
        authority_context: ConstructionAuthorityContext,
    ) -> AuthorityContextUpdate | None:
        return ("risk_context", {"source": "risk"})

    assert collect_authority_context_updates(
        source_context=_source_context(),
        authority_context=ConstructionAuthorityContext(),
        update_builders=(missing_update, present_update),
    ) == {"risk_context": {"source": "risk"}}


def test_collect_authority_context_updates_uses_later_builder_for_same_key() -> None:
    def first_update(
        *,
        source_context: DpmCoreExecutionContext,
        authority_context: ConstructionAuthorityContext,
    ) -> AuthorityContextUpdate | None:
        return ("liquidity_context", {"source": "first"})

    def second_update(
        *,
        source_context: DpmCoreExecutionContext,
        authority_context: ConstructionAuthorityContext,
    ) -> AuthorityContextUpdate | None:
        return ("liquidity_context", {"source": "second"})

    assert collect_authority_context_updates(
        source_context=_source_context(),
        authority_context=ConstructionAuthorityContext(),
        update_builders=(first_update, second_update),
    ) == {"liquidity_context": {"source": "second"}}


def test_merge_authority_context_update_maps_keeps_later_update_for_same_key() -> None:
    assert merge_authority_context_update_maps(
        {"liquidity_context": {"source": "profile"}},
        {
            "transaction_cost_context": {"source": "financial"},
            "liquidity_context": {"source": "financial"},
        },
    ) == {
        "liquidity_context": {"source": "financial"},
        "transaction_cost_context": {"source": "financial"},
    }
