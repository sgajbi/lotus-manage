from __future__ import annotations

import json
from contextlib import closing
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.rebalance_runs.idea_management_action import (
    IdeaManagementAction,
    IdeaManagementActionEvent,
)
from src.core.rebalance_runs.idea_management_action_repository import (
    IdeaManagementActionRepositoryUnavailableError,
    IdeaManagementActionCreateResult,
    IdeaManagementActionRepository,
    IdeaManagementActionRepositoryConflictError,
)
from src.infrastructure.postgres_access import (
    PostgresAccessError,
    PostgresConfigurationError,
    connect_postgres,
)
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresIdeaManagementActionRepository(IdeaManagementActionRepository):
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise PostgresConfigurationError("DPM_IDEA_MANAGEMENT_ACTION_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise PostgresConfigurationError("DPM_IDEA_MANAGEMENT_ACTION_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def create_or_replay(
        self,
        *,
        action: IdeaManagementAction,
    ) -> IdeaManagementActionCreateResult:
        with closing(self._connect()) as connection:
            inserted = connection.execute(
                """
                INSERT INTO dpm_idea_management_actions (
                    action_id, intake_id, tenant_id, legal_entity_code, portfolio_id,
                    idea_candidate_id, conversion_intent_id, request_fingerprint,
                    idempotency_scope_hash, status, source_event_version, payload_json,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
                RETURNING action_id
                """,
                _action_insert_params(action),
            ).fetchone()
            if inserted is not None:
                self._insert_event(connection=connection, event=action.events[0])
                connection.commit()
                return IdeaManagementActionCreateResult(action=action, created=True)

            existing = self._load_create_conflict(connection=connection, action=action)
            connection.rollback()
            if existing is None or not _same_intake(existing=existing, proposed=action):
                raise IdeaManagementActionRepositoryConflictError(
                    "IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT"
                )
            return IdeaManagementActionCreateResult(action=existing, created=False)

    def get_by_intake_id(
        self,
        *,
        tenant_id: str,
        legal_entity_code: str,
        intake_id: str,
    ) -> IdeaManagementAction | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_idea_management_actions
                WHERE tenant_id = %s
                  AND legal_entity_code = %s
                  AND intake_id = %s
                """,
                (tenant_id, legal_entity_code, intake_id),
            ).fetchone()
        return _load_action(row)

    def update(
        self,
        *,
        action: IdeaManagementAction,
        expected_source_event_version: int,
    ) -> IdeaManagementAction:
        if action.source_event_version != expected_source_event_version + 1:
            raise IdeaManagementActionRepositoryConflictError(
                "IDEA_MANAGEMENT_ACTION_VERSION_SEQUENCE_INVALID"
            )
        with closing(self._connect()) as connection:
            updated = connection.execute(
                """
                UPDATE dpm_idea_management_actions
                SET status = %s,
                    source_event_version = %s,
                    payload_json = %s,
                    updated_at = %s
                WHERE action_id = %s
                  AND source_event_version = %s
                RETURNING action_id
                """,
                (
                    action.status,
                    action.source_event_version,
                    action.model_dump_json(),
                    action.updated_at,
                    action.action_id,
                    expected_source_event_version,
                ),
            ).fetchone()
            if updated is None:
                connection.rollback()
                raise IdeaManagementActionRepositoryConflictError(
                    "IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT"
                )
            self._insert_event(connection=connection, event=action.events[-1])
            connection.commit()
        return action

    def _load_create_conflict(
        self,
        *,
        connection: Any,
        action: IdeaManagementAction,
    ) -> IdeaManagementAction | None:
        row = connection.execute(
            """
            SELECT payload_json
            FROM dpm_idea_management_actions
            WHERE idempotency_scope_hash = %s
               OR action_id = %s
               OR (
                    tenant_id = %s
                    AND legal_entity_code = %s
                    AND intake_id = %s
               )
            ORDER BY action_id ASC
            LIMIT 1
            """,
            (
                action.idempotency_scope_hash,
                action.action_id,
                action.tenant_id,
                action.legal_entity_code,
                action.intake_id,
            ),
        ).fetchone()
        return _load_action(row)

    @staticmethod
    def _insert_event(*, connection: Any, event: IdeaManagementActionEvent) -> None:
        connection.execute(
            """
            INSERT INTO dpm_idea_management_action_events (
                event_id, action_id, source_event_version, event_type,
                status, occurred_at, payload_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event.event_id,
                event.action_id,
                event.source_event_version,
                event.event_type,
                event.status,
                event.occurred_at,
                event.model_dump_json(),
            ),
        )

    def _connect(self) -> Any:
        """Every operation reaches PostgreSQL through here, so unavailability
        is translated ONCE into the repository protocol's own error - callers
        above the boundary never see a Postgres exception type."""

        psycopg, dict_row = _import_psycopg()
        try:
            return connect_postgres(
                self._dsn,
                connect_fn=psycopg.connect,
                row_factory=dict_row,
                application_name="lotus-manage:idea-management-actions",
            )
        except PostgresAccessError as exc:
            raise IdeaManagementActionRepositoryUnavailableError(
                "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE"
            ) from exc

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


def _action_insert_params(action: IdeaManagementAction) -> tuple[object, ...]:
    return (
        action.action_id,
        action.intake_id,
        action.tenant_id,
        action.legal_entity_code,
        action.portfolio_id,
        action.idea_candidate_id,
        action.conversion_intent_id,
        action.request_fingerprint,
        action.idempotency_scope_hash,
        action.status,
        action.source_event_version,
        action.model_dump_json(),
        action.created_at,
        action.updated_at,
    )


def _same_intake(
    *,
    existing: IdeaManagementAction,
    proposed: IdeaManagementAction,
) -> bool:
    return (
        existing.action_id == proposed.action_id
        and existing.intake_id == proposed.intake_id
        and existing.tenant_id == proposed.tenant_id
        and existing.legal_entity_code == proposed.legal_entity_code
        and existing.portfolio_id == proposed.portfolio_id
        and existing.request_fingerprint == proposed.request_fingerprint
        and existing.idempotency_scope_hash == proposed.idempotency_scope_hash
    )


def _load_action(row: Any) -> IdeaManagementAction | None:
    if row is None:
        return None
    payload = row["payload_json"]
    if not isinstance(payload, (str, bytes, bytearray, dict)):
        payload = json.dumps(payload, default=str)
    return (
        IdeaManagementAction.model_validate_json(payload)
        if not isinstance(payload, dict)
        else IdeaManagementAction.model_validate(payload)
    )


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


__all__ = ["PostgresIdeaManagementActionRepository"]
