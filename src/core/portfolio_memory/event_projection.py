"""Shared pure projection helpers for portfolio-memory events."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent


def event_source_systems(event: DpmPortfolioMemoryEvent) -> set[str]:
    return {
        source_system
        for source_system in [
            event.source_system,
            *(ref.source_system for ref in event.source_refs),
            *(ref.source_system for ref in event.artifact_refs),
        ]
        if source_system
    }


def event_source_types(event: DpmPortfolioMemoryEvent) -> set[str]:
    return {
        source_type
        for source_type in [
            event.source_type,
            *(ref.source_type for ref in event.source_refs),
            *(ref.source_type for ref in event.artifact_refs),
        ]
        if source_type
    }


def portfolio_memory_supportability_state(
    events: Iterable[DpmPortfolioMemoryEvent],
) -> str:
    states: set[str] = set()
    for event in events:
        states.add(event.supportability_state)
    if not states:
        return "EMPTY"
    for state in ("BLOCKED", "DEGRADED", "PENDING_REVIEW"):
        if state in states:
            return state
    return "READY"
