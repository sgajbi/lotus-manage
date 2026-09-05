from __future__ import annotations

from copy import deepcopy
from threading import Lock

from src.core.rebalance_runs.idea_management_action import IdeaManagementAction
from src.core.rebalance_runs.idea_management_action_repository import (
    IdeaManagementActionCreateResult,
    IdeaManagementActionRepository,
    IdeaManagementActionRepositoryConflictError,
)


class InMemoryIdeaManagementActionRepository(IdeaManagementActionRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._actions: dict[str, IdeaManagementAction] = {}
        self._action_id_by_intake_scope: dict[tuple[str, str, str], str] = {}
        self._action_id_by_conversion_scope: dict[tuple[str, str, str, str], str] = {}
        self._action_id_by_idempotency_scope: dict[str, str] = {}

    def create_or_replay(
        self,
        *,
        action: IdeaManagementAction,
    ) -> IdeaManagementActionCreateResult:
        with self._lock:
            existing = self._existing_for_create(action)
            if existing is not None:
                return IdeaManagementActionCreateResult(action=deepcopy(existing), created=False)
            self._actions[action.action_id] = deepcopy(action)
            self._action_id_by_intake_scope[
                (action.tenant_id, action.legal_entity_code, action.intake_id)
            ] = action.action_id
            self._action_id_by_conversion_scope[
                (
                    action.tenant_id,
                    action.legal_entity_code,
                    action.portfolio_id,
                    action.conversion_intent_id,
                )
            ] = action.action_id
            self._action_id_by_idempotency_scope[action.idempotency_scope_hash] = action.action_id
            return IdeaManagementActionCreateResult(action=deepcopy(action), created=True)

    def get_by_intake_id(
        self,
        *,
        tenant_id: str,
        legal_entity_code: str,
        intake_id: str,
    ) -> IdeaManagementAction | None:
        with self._lock:
            action_id = self._action_id_by_intake_scope.get(
                (tenant_id, legal_entity_code, intake_id)
            )
            action = self._actions.get(action_id or "")
            return deepcopy(action) if action is not None else None

    def get_by_conversion_intent(
        self,
        *,
        tenant_id: str,
        legal_entity_code: str,
        portfolio_id: str,
        conversion_intent_id: str,
    ) -> IdeaManagementAction | None:
        with self._lock:
            action_id = self._action_id_by_conversion_scope.get(
                (tenant_id, legal_entity_code, portfolio_id, conversion_intent_id)
            )
            action = self._actions.get(action_id or "")
            return deepcopy(action) if action is not None else None

    def update(
        self,
        *,
        action: IdeaManagementAction,
        expected_source_event_version: int,
    ) -> IdeaManagementAction:
        with self._lock:
            existing = self._actions.get(action.action_id)
            if existing is None:
                raise IdeaManagementActionRepositoryConflictError(
                    "IDEA_MANAGEMENT_ACTION_NOT_FOUND"
                )
            if existing.source_event_version != expected_source_event_version:
                raise IdeaManagementActionRepositoryConflictError(
                    "IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT"
                )
            if action.source_event_version != expected_source_event_version + 1:
                raise IdeaManagementActionRepositoryConflictError(
                    "IDEA_MANAGEMENT_ACTION_VERSION_SEQUENCE_INVALID"
                )
            self._actions[action.action_id] = deepcopy(action)
            return deepcopy(action)

    def _existing_for_create(
        self,
        action: IdeaManagementAction,
    ) -> IdeaManagementAction | None:
        action_id = self._action_id_by_idempotency_scope.get(action.idempotency_scope_hash)
        if action_id is None:
            intake_key = (action.tenant_id, action.legal_entity_code, action.intake_id)
            action_id = self._action_id_by_intake_scope.get(intake_key)
        if action_id is None:
            conversion_key = (
                action.tenant_id,
                action.legal_entity_code,
                action.portfolio_id,
                action.conversion_intent_id,
            )
            action_id = self._action_id_by_conversion_scope.get(conversion_key)
        if action_id is None:
            action_id = action.action_id if action.action_id in self._actions else None
        if action_id is None:
            return None
        existing = self._actions[action_id]
        if (
            existing.request_fingerprint != action.request_fingerprint
            or existing.action_id != action.action_id
        ):
            raise IdeaManagementActionRepositoryConflictError(
                "IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT"
            )
        return existing

    def reset(self) -> None:
        with self._lock:
            self._actions.clear()
            self._action_id_by_intake_scope.clear()
            self._action_id_by_conversion_scope.clear()
            self._action_id_by_idempotency_scope.clear()


__all__ = ["InMemoryIdeaManagementActionRepository"]
