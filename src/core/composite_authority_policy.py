"""One economic authority per member/fact/closed interval, never fallback selection."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.composite_authority_models import (
        CompositeEconomicAuthorityPayload,
        CompositeFactSelection,
        ProviderRegistrationBinding,
    )


def _canonical_ids(values: list[str], code: str) -> None:
    if values != sorted(set(values)):
        raise ValueError(code)


def require_authority_coverage(payload: CompositeEconomicAuthorityPayload) -> None:
    start, end = (
        date.fromisoformat(payload.effective_from),
        date.fromisoformat(payload.effective_to),
    )
    if end < start:
        raise ValueError("COMPOSITE_AUTHORITY_WINDOW_INVALID")
    _require_identity_registry(payload)
    windows = _selected_fact_windows(payload, start, end)
    facts = {"BEGINNING_ASSETS", "MEMBER_RETURN"}
    for optional_fact in ("ENDING_ASSETS", "BENCHMARK_RETURN"):
        if any(key[1] == optional_fact for key in windows):
            facts.add(optional_fact)
    for member in payload.member_identities:
        for fact in facts:
            _require_continuous_window(windows.get((member.member_id, fact), []), start, end)


def _require_identity_registry(payload: CompositeEconomicAuthorityPayload) -> None:
    members = [item.member_id for item in payload.member_identities]
    _canonical_ids(members, "COMPOSITE_AUTHORITY_MEMBERS_NONCANONICAL")
    provider_ids = [item.provider_id for item in payload.providers]
    _canonical_ids(provider_ids, "COMPOSITE_AUTHORITY_PROVIDERS_NONCANONICAL")
    _canonical_ids(
        [item.selection_id for item in payload.selections],
        "COMPOSITE_AUTHORITY_SELECTIONS_NONCANONICAL",
    )
    providers = {item.provider_id: item for item in payload.providers}
    _require_internal_owners(providers)
    if any(member.provider_id not in providers for member in payload.member_identities):
        raise ValueError("COMPOSITE_AUTHORITY_MEMBER_PROVIDER_UNKNOWN")
    for member in payload.member_identities:
        external = providers[member.provider_id].source_kind == "EXTERNAL_PROVIDER"
        if external != (member.identity_kind == "EXTERNAL_MEMBER"):
            raise ValueError("COMPOSITE_AUTHORITY_MEMBER_KIND_MISMATCH")


def _require_internal_owners(providers: dict[str, ProviderRegistrationBinding]) -> None:
    for provider in providers.values():
        owner = {"LOTUS_CORE": "lotus-core", "LOTUS_PERFORMANCE": "lotus-performance"}.get(
            provider.source_kind
        )
        if owner is not None and provider.provider_id != owner:
            raise ValueError("COMPOSITE_AUTHORITY_INTERNAL_OWNER_MISMATCH")


def _selected_fact_windows(
    payload: CompositeEconomicAuthorityPayload, start: date, end: date
) -> dict[tuple[str, str], list[tuple[date, date]]]:
    providers = {item.provider_id: item for item in payload.providers}
    members = {item.member_id for item in payload.member_identities}
    windows: dict[tuple[str, str], list[tuple[date, date]]] = {}
    external_selections: set[bool] = set()
    for selection in payload.selections:
        provider = providers.get(selection.provider_id)
        if provider is None or selection.economic_authority != selection.provider_id:
            raise ValueError("COMPOSITE_AUTHORITY_PROVIDER_MISMATCH")
        _require_fact_source(selection, provider, payload)
        _require_selected_members(selection, members)
        if selection.fact != "BENCHMARK_RETURN":
            external_selections.add(provider.source_kind == "EXTERNAL_PROVIDER")
        left, right = (
            date.fromisoformat(selection.effective_from),
            date.fromisoformat(selection.effective_to),
        )
        if not start <= left <= right <= end:
            raise ValueError("COMPOSITE_AUTHORITY_SELECTION_WINDOW_INVALID")
        for member_id in selection.member_ids:
            windows.setdefault((member_id, selection.fact), []).append((left, right))
    expected_mode = {
        frozenset({False}): "INTERNAL",
        frozenset({True}): "EXTERNAL",
        frozenset({False, True}): "HYBRID",
    }.get(frozenset(external_selections))
    if payload.mode != expected_mode:
        raise ValueError("COMPOSITE_AUTHORITY_MODE_MISMATCH")
    return windows


def _require_selected_members(selection: CompositeFactSelection, members: set[str]) -> None:
    _canonical_ids(selection.member_ids, "COMPOSITE_AUTHORITY_SELECTION_MEMBERS_NONCANONICAL")
    if not set(selection.member_ids) <= members:
        raise ValueError("COMPOSITE_AUTHORITY_MEMBER_UNKNOWN")


def _require_fact_source(
    selection: CompositeFactSelection,
    provider: ProviderRegistrationBinding,
    payload: CompositeEconomicAuthorityPayload,
) -> None:
    internal_kind = "LOTUS_CORE"
    if selection.fact == "MEMBER_RETURN":
        internal_kind = "LOTUS_PERFORMANCE"
        if selection.method_profile_binding != payload.return_method_binding:
            raise ValueError("COMPOSITE_AUTHORITY_METHOD_BINDING_MISMATCH")
    elif selection.method_profile_binding is not None:
        raise ValueError("COMPOSITE_AUTHORITY_METHOD_BINDING_UNEXPECTED")
    if provider.source_kind not in {"EXTERNAL_PROVIDER", internal_kind}:
        raise ValueError("COMPOSITE_AUTHORITY_FACT_KIND_MISMATCH")


def _require_continuous_window(windows: list[tuple[date, date]], start: date, end: date) -> None:
    covered_to: date | None = None
    for left, right in sorted(windows):
        if covered_to is not None and left <= covered_to:
            raise ValueError("COMPOSITE_ECONOMIC_AUTHORITY_OVERLAP")
        if left != (start if covered_to is None else covered_to + timedelta(days=1)):
            raise ValueError("COMPOSITE_ECONOMIC_AUTHORITY_GAP")
        covered_to = right
    if covered_to != end:
        raise ValueError("COMPOSITE_ECONOMIC_AUTHORITY_GAP")
