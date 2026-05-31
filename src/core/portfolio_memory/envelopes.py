"""Deterministic envelope finalization for portfolio-memory read models."""

from typing import Any

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEventLookup,
    DpmPortfolioMemorySearchPage,
)

_VOLATILE_HASH_FIELDS = {"content_hash", "generated_at"}


def replay_stable_content_hash(payload: dict[str, Any]) -> str:
    return hash_canonical_payload(strip_keys(payload, exclude=_VOLATILE_HASH_FIELDS))


def finalize_portfolio_memory(memory: DpmPortfolioMemory) -> DpmPortfolioMemory:
    payload = memory.model_dump(mode="json")
    payload["content_hash"] = replay_stable_content_hash(payload)
    return DpmPortfolioMemory.model_validate(payload)


def finalize_search_page_payload(
    page_payload: dict[str, Any],
) -> DpmPortfolioMemorySearchPage:
    page_for_hash = DpmPortfolioMemorySearchPage.model_validate(
        {**page_payload, "content_hash": "sha256:pending"}
    )
    payload = dict(page_payload)
    payload["content_hash"] = replay_stable_content_hash(page_for_hash.model_dump(mode="json"))
    return DpmPortfolioMemorySearchPage.model_validate(payload)


def finalize_event_lookup(
    lookup: DpmPortfolioMemoryEventLookup,
) -> DpmPortfolioMemoryEventLookup:
    payload = lookup.model_dump(mode="json")
    payload["content_hash"] = replay_stable_content_hash(payload)
    return DpmPortfolioMemoryEventLookup.model_validate(payload)
