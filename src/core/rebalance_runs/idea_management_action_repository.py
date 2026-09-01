from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.rebalance_runs.idea_management_action import IdeaManagementAction


class IdeaManagementActionRepositoryConflictError(Exception):
    """Raised when immutable identity or optimistic concurrency conflicts."""


@dataclass(frozen=True)
class IdeaManagementActionCreateResult:
    action: IdeaManagementAction
    created: bool


class IdeaManagementActionRepository(Protocol):
    def create_or_replay(
        self,
        *,
        action: IdeaManagementAction,
    ) -> IdeaManagementActionCreateResult: ...

    def get_by_intake_id(
        self,
        *,
        tenant_id: str,
        legal_entity_code: str,
        intake_id: str,
    ) -> IdeaManagementAction | None: ...

    def update(
        self,
        *,
        action: IdeaManagementAction,
        expected_source_event_version: int,
    ) -> IdeaManagementAction: ...


__all__ = [
    "IdeaManagementActionCreateResult",
    "IdeaManagementActionRepository",
    "IdeaManagementActionRepositoryConflictError",
]
