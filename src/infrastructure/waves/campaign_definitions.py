from __future__ import annotations

import json
from collections.abc import Iterable
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.waves.campaign_assignment_plan import (
    build_bulk_review_campaign_assignment_plan_item,
)
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.campaign_repository import (
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionRepository,
)
from src.core.waves.campaign_workflow_board import (
    build_bulk_review_campaign_workflow_board_item,
)
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_access import connect_postgres
from src.infrastructure.postgres_migrations import apply_postgres_migrations


def _load_campaign_definition_payload(
    payload: str | dict[str, Any],
) -> DpmBulkReviewCampaignDefinition:
    try:
        return load_model_json(DpmBulkReviewCampaignDefinition, payload)
    except ValueError as exc:
        if "BULK_REVIEW_CAMPAIGN_DEFINITION_HASH_MISMATCH" not in str(exc):
            raise
        legacy_payload = json.loads(payload) if isinstance(payload, str) else deepcopy(payload)
        legacy_payload["content_hash"] = ""
        return DpmBulkReviewCampaignDefinition.model_validate(legacy_payload)


_WORKFLOW_UPDATE_OPERATIONS = frozenset(
    {
        "approval_decision",
        "assignment_action",
        "assignment_task",
        "launch",
        "maker_checker_control",
    }
)


def _validate_workflow_update_operation(operation: str) -> None:
    if operation not in _WORKFLOW_UPDATE_OPERATIONS:
        raise ValueError(f"Unsupported campaign workflow update operation: {operation}")


class _CampaignWorkflowUpdateMixin:
    def record_definition_launch(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        return self._record_workflow_definition_update(definition, expected_content_hash, "launch")

    def record_definition_approval_decision(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        return self._record_workflow_definition_update(
            definition, expected_content_hash, "approval_decision"
        )

    def record_definition_assignment_action(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        return self._record_workflow_definition_update(
            definition, expected_content_hash, "assignment_action"
        )

    def record_definition_assignment_task(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        return self._record_workflow_definition_update(
            definition, expected_content_hash, "assignment_task"
        )

    def record_definition_maker_checker_control(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        return self._record_workflow_definition_update(
            definition, expected_content_hash, "maker_checker_control"
        )

    def _record_workflow_definition_update(
        self,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
        operation: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        raise NotImplementedError


class InMemoryDpmBulkReviewCampaignDefinitionRepository(
    _CampaignWorkflowUpdateMixin,
    DpmBulkReviewCampaignDefinitionRepository,
):
    def __init__(self) -> None:
        self._lock = Lock()
        self._definitions: dict[tuple[str, str], DpmBulkReviewCampaignDefinition] = {}

    def save_definition(self, *, definition: DpmBulkReviewCampaignDefinition) -> None:
        key = (definition.campaign_id, definition.campaign_version)
        with self._lock:
            existing = self._definitions.get(key)
            if existing is not None and existing.content_hash != definition.content_hash:
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_IMMUTABLE_CONFLICT"
                )
            self._definitions[key] = deepcopy(definition)

    def get_definition(
        self,
        *,
        campaign_id: str,
        campaign_version: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        with self._lock:
            definition = self._definitions.get((campaign_id, campaign_version))
            return deepcopy(definition) if definition is not None else None

    def list_definitions(
        self,
        *,
        campaign_id: str | None = None,
        status: str | None = None,
        as_of_date: str | None = None,
        limit: int | None = 50,
        offset: int = 0,
    ) -> list[DpmBulkReviewCampaignDefinition]:
        with self._lock:
            return deepcopy(
                _paged_definitions(
                    definitions=self._definitions.values(),
                    campaign_id=campaign_id,
                    status=status,
                    as_of_date=as_of_date,
                    limit=limit,
                    offset=offset,
                )
            )

    def list_definitions_by_workflow_projection(
        self,
        *,
        campaign_id: str | None = None,
        status: str | None = None,
        as_of_date: str | None = None,
        include_closed: bool = False,
        board_status: str | None = None,
        next_action: str | None = None,
        assignment_escalation_tier: str | None = None,
        assignment_task_status: str | None = None,
        assigned_actor_id: str | None = None,
        assignment_sla_posture: str | None = None,
        maker_checker_outcome: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[DpmBulkReviewCampaignDefinition]:
        definitions = [
            definition
            for definition in self._definitions.values()
            if _definition_matches_filters(
                definition,
                campaign_id=campaign_id,
                status=status,
                as_of_date=as_of_date,
            )
            and _workflow_projection_matches(
                definition=definition,
                include_closed=include_closed,
                board_status=board_status,
                next_action=next_action,
                assignment_escalation_tier=assignment_escalation_tier,
                assignment_task_status=assignment_task_status,
                assigned_actor_id=assigned_actor_id,
                assignment_sla_posture=assignment_sla_posture,
                maker_checker_outcome=maker_checker_outcome,
            )
        ]
        definitions.sort(key=_definition_sort_key, reverse=True)
        if limit is None:
            return deepcopy(definitions[offset:])
        return deepcopy(definitions[offset : offset + limit])

    def retire_definition(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        key = (definition.campaign_id, definition.campaign_version)
        with self._lock:
            existing = self._definitions.get(key)
            if existing is None:
                return None
            if existing.status == "RETIRED":
                return deepcopy(existing)
            if existing.status != "ACTIVE":
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            self._definitions[key] = deepcopy(definition)
            return deepcopy(definition)

    def supersede_definition(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        key = (definition.campaign_id, definition.campaign_version)
        with self._lock:
            existing = self._definitions.get(key)
            if existing is None:
                return None
            if existing.status == "SUPERSEDED":
                return deepcopy(existing)
            if existing.status != "ACTIVE":
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            self._definitions[key] = deepcopy(definition)
            return deepcopy(definition)

    def _record_workflow_definition_update(
        self,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
        operation: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        _validate_workflow_update_operation(operation)
        with self._lock:
            return self._record_active_definition_update(
                definition,
                expected_content_hash=expected_content_hash,
            )

    def _record_active_definition_update(
        self,
        definition: DpmBulkReviewCampaignDefinition,
        *,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        key = (definition.campaign_id, definition.campaign_version)
        existing = self._definitions.get(key)
        if existing is None:
            return None
        if existing.content_hash == definition.content_hash:
            return deepcopy(existing)
        if existing.status != "ACTIVE":
            raise DpmBulkReviewCampaignDefinitionConflictError(
                "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
            )
        if existing.content_hash != expected_content_hash:
            raise DpmBulkReviewCampaignDefinitionConflictError(
                "BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE"
            )
        self._definitions[key] = deepcopy(definition)
        return deepcopy(definition)


def _paged_definitions(
    *,
    definitions: Iterable[DpmBulkReviewCampaignDefinition],
    campaign_id: str | None,
    status: str | None,
    as_of_date: str | None,
    limit: int | None,
    offset: int,
) -> list[DpmBulkReviewCampaignDefinition]:
    filtered = [
        definition
        for definition in definitions
        if _definition_matches_filters(
            definition,
            campaign_id=campaign_id,
            status=status,
            as_of_date=as_of_date,
        )
    ]
    filtered.sort(key=_definition_sort_key, reverse=True)
    if limit is None:
        return filtered[offset:]
    return filtered[offset : offset + limit]


def _definition_matches_filters(
    definition: DpmBulkReviewCampaignDefinition,
    *,
    campaign_id: str | None,
    status: str | None,
    as_of_date: str | None,
) -> bool:
    return (
        _optional_text_filter_matches(definition.campaign_id, campaign_id)
        and _optional_text_filter_matches(definition.status, status)
        and _optional_text_filter_matches(definition.as_of_date, as_of_date)
    )


def _optional_text_filter_matches(value: str, expected: str | None) -> bool:
    return expected is None or value == expected


def _definition_sort_key(
    definition: DpmBulkReviewCampaignDefinition,
) -> tuple[str, str, str]:
    return (definition.as_of_date, definition.campaign_id, definition.campaign_version)


class PostgresDpmBulkReviewCampaignDefinitionRepository(_CampaignWorkflowUpdateMixin):
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_CAMPAIGN_DEFINITION_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_CAMPAIGN_DEFINITION_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_definition(self, *, definition: DpmBulkReviewCampaignDefinition) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_bulk_review_campaign_definitions (
                    campaign_id, campaign_version, status, as_of_date, content_hash, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (campaign_id, campaign_version) DO NOTHING
                """,
                (
                    definition.campaign_id,
                    definition.campaign_version,
                    definition.status,
                    definition.as_of_date,
                    definition.content_hash,
                    dump_model_json(definition),
                ),
            )
            persisted = connection.execute(
                """
                SELECT content_hash
                FROM dpm_bulk_review_campaign_definitions
                WHERE campaign_id = %s AND campaign_version = %s
                """,
                (definition.campaign_id, definition.campaign_version),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != definition.content_hash:
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_IMMUTABLE_CONFLICT"
                )
            _upsert_workflow_read_model_projection(connection=connection, definition=definition)
            connection.commit()

    def get_definition(
        self,
        *,
        campaign_id: str,
        campaign_version: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM dpm_bulk_review_campaign_definitions
                WHERE campaign_id = %s AND campaign_version = %s
                """,
                (campaign_id, campaign_version),
            ).fetchone()
        if row is None:
            return None
        return _load_campaign_definition_payload(_payload(row))

    def list_definitions(
        self,
        *,
        campaign_id: str | None = None,
        status: str | None = None,
        as_of_date: str | None = None,
        limit: int | None = 50,
        offset: int = 0,
    ) -> list[DpmBulkReviewCampaignDefinition]:
        clauses: list[str] = []
        args: list[Any] = []
        for column, value in (
            ("campaign_id", campaign_id),
            ("status", status),
            ("as_of_date", as_of_date),
        ):
            if value is not None:
                clauses.append(f"{column} = %s")
                args.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        pagination = ""
        if limit is not None:
            pagination = "LIMIT %s OFFSET %s"
            args.extend([limit, offset])
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT payload_json
                FROM dpm_bulk_review_campaign_definitions
                {where}
                ORDER BY as_of_date DESC, campaign_id DESC, campaign_version DESC
                {pagination}
                """,
                tuple(args),
            ).fetchall()
        return [_load_campaign_definition_payload(_payload(row)) for row in rows]

    def list_definitions_by_workflow_projection(
        self,
        *,
        campaign_id: str | None = None,
        status: str | None = None,
        as_of_date: str | None = None,
        include_closed: bool = False,
        board_status: str | None = None,
        next_action: str | None = None,
        assignment_escalation_tier: str | None = None,
        assignment_task_status: str | None = None,
        assigned_actor_id: str | None = None,
        assignment_sla_posture: str | None = None,
        maker_checker_outcome: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[DpmBulkReviewCampaignDefinition]:
        clauses: list[str] = []
        args: list[Any] = []
        for column, value in (
            ("d.campaign_id", campaign_id),
            ("d.status", status),
            ("d.as_of_date", as_of_date),
            ("w.board_status", board_status),
            ("w.next_action", next_action),
            ("w.assignment_escalation_tier", assignment_escalation_tier),
            ("w.assignment_sla_posture", assignment_sla_posture),
        ):
            if value is not None:
                clauses.append(f"{column} = %s")
                args.append(value)
        if not include_closed:
            clauses.append("w.board_status <> 'CLOSED'")
        if assignment_task_status is not None:
            clauses.append("%s = ANY(w.assignment_task_statuses)")
            args.append(assignment_task_status)
        if assigned_actor_id is not None:
            clauses.append("%s = ANY(w.assigned_actor_ids)")
            args.append(assigned_actor_id)
        if maker_checker_outcome is not None:
            clauses.append("%s = ANY(w.maker_checker_outcomes)")
            args.append(maker_checker_outcome)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        pagination = ""
        if limit is not None:
            pagination = "LIMIT %s OFFSET %s"
            args.extend([limit, offset])
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT d.payload_json
                FROM dpm_bulk_review_campaign_definitions d
                JOIN dpm_bulk_review_campaign_workflow_read_model w
                  ON w.campaign_id = d.campaign_id
                 AND w.campaign_version = d.campaign_version
                {where}
                ORDER BY d.as_of_date DESC, d.campaign_id DESC, d.campaign_version DESC
                {pagination}
                """,
                tuple(args),
            ).fetchall()
        return [_load_campaign_definition_payload(_payload(row)) for row in rows]

    def retire_definition(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        with closing(self._connect()) as connection:
            persisted = connection.execute(
                """
                SELECT status, payload_json
                FROM dpm_bulk_review_campaign_definitions
                WHERE campaign_id = %s AND campaign_version = %s
                """,
                (definition.campaign_id, definition.campaign_version),
            ).fetchone()
            if persisted is None:
                connection.rollback()
                return None
            existing = _load_campaign_definition_payload(_payload(persisted))
            if existing.status == "RETIRED":
                connection.rollback()
                return existing
            updated = connection.execute(
                """
                UPDATE dpm_bulk_review_campaign_definitions
                SET status = %s, content_hash = %s, payload_json = %s
                WHERE campaign_id = %s AND campaign_version = %s AND status = 'ACTIVE'
                """,
                (
                    definition.status,
                    definition.content_hash,
                    dump_model_json(definition),
                    definition.campaign_id,
                    definition.campaign_version,
                ),
            )
            rowcount = getattr(updated, "rowcount", 1)
            if rowcount != 1:
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            _upsert_workflow_read_model_projection(connection=connection, definition=definition)
            connection.commit()
            return definition

    def supersede_definition(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        with closing(self._connect()) as connection:
            persisted = connection.execute(
                """
                SELECT status, payload_json
                FROM dpm_bulk_review_campaign_definitions
                WHERE campaign_id = %s AND campaign_version = %s
                """,
                (definition.campaign_id, definition.campaign_version),
            ).fetchone()
            if persisted is None:
                connection.rollback()
                return None
            existing = _load_campaign_definition_payload(_payload(persisted))
            if existing.status == "SUPERSEDED":
                connection.rollback()
                return existing
            updated = connection.execute(
                """
                UPDATE dpm_bulk_review_campaign_definitions
                SET status = %s, content_hash = %s, payload_json = %s
                WHERE campaign_id = %s AND campaign_version = %s AND status = 'ACTIVE'
                """,
                (
                    definition.status,
                    definition.content_hash,
                    dump_model_json(definition),
                    definition.campaign_id,
                    definition.campaign_version,
                ),
            )
            rowcount = getattr(updated, "rowcount", 1)
            if rowcount != 1:
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            _upsert_workflow_read_model_projection(connection=connection, definition=definition)
            connection.commit()
            return definition

    def _record_workflow_definition_update(
        self,
        definition: DpmBulkReviewCampaignDefinition,
        expected_content_hash: str,
        operation: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        _validate_workflow_update_operation(operation)
        return self._record_active_definition_update(
            definition,
            expected_content_hash=expected_content_hash,
        )

    def _record_active_definition_update(
        self,
        definition: DpmBulkReviewCampaignDefinition,
        *,
        expected_content_hash: str,
    ) -> DpmBulkReviewCampaignDefinition | None:
        with closing(self._connect()) as connection:
            persisted = connection.execute(
                """
                SELECT status, content_hash, payload_json
                FROM dpm_bulk_review_campaign_definitions
                WHERE campaign_id = %s AND campaign_version = %s
                """,
                (definition.campaign_id, definition.campaign_version),
            ).fetchone()
            if persisted is None:
                connection.rollback()
                return None
            existing = _load_campaign_definition_payload(_payload(persisted))
            if existing.content_hash == definition.content_hash:
                connection.rollback()
                return existing
            if existing.status != "ACTIVE":
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            if existing.content_hash != expected_content_hash:
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE"
                )
            updated = connection.execute(
                """
                UPDATE dpm_bulk_review_campaign_definitions
                SET content_hash = %s, payload_json = %s
                WHERE campaign_id = %s
                  AND campaign_version = %s
                  AND status = 'ACTIVE'
                  AND content_hash = %s
                """,
                (
                    definition.content_hash,
                    dump_model_json(definition),
                    definition.campaign_id,
                    definition.campaign_version,
                    expected_content_hash,
                ),
            )
            rowcount = getattr(updated, "rowcount", 1)
            if rowcount != 1:
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE"
                )
            _upsert_workflow_read_model_projection(connection=connection, definition=definition)
            connection.commit()
            return definition

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return connect_postgres(
            self._dsn,
            connect_fn=psycopg.connect,
            row_factory=dict_row,
            application_name="lotus-manage:campaign-definitions",
        )

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")
            _rebuild_workflow_read_model_projection(connection=connection)


def _workflow_projection_matches(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    include_closed: bool,
    board_status: str | None,
    next_action: str | None,
    assignment_escalation_tier: str | None,
    assignment_task_status: str | None,
    assigned_actor_id: str | None,
    assignment_sla_posture: str | None,
    maker_checker_outcome: str | None,
) -> bool:
    projection = _workflow_read_model_projection(definition)
    return (
        (include_closed or projection["board_status"] != "CLOSED")
        and _optional_text_filter_matches(str(projection["board_status"]), board_status)
        and _optional_text_filter_matches(str(projection["next_action"]), next_action)
        and _optional_text_filter_matches(
            str(projection["assignment_escalation_tier"]),
            assignment_escalation_tier,
        )
        and _optional_text_filter_matches(
            str(projection["assignment_sla_posture"]),
            assignment_sla_posture,
        )
        and _optional_member_filter_matches(
            projection["assignment_task_statuses"],
            assignment_task_status,
        )
        and _optional_member_filter_matches(
            projection["assigned_actor_ids"],
            assigned_actor_id,
        )
        and _optional_member_filter_matches(
            projection["maker_checker_outcomes"],
            maker_checker_outcome,
        )
    )


def _optional_member_filter_matches(values: object, expected: str | None) -> bool:
    return expected is None or expected in set(values if isinstance(values, list) else [])


def _rebuild_workflow_read_model_projection(*, connection: Any) -> None:
    rows = connection.execute(
        """
        SELECT payload_json
        FROM dpm_bulk_review_campaign_definitions
        """
    ).fetchall()
    for row in rows:
        _upsert_workflow_read_model_projection(
            connection=connection,
            definition=_load_campaign_definition_payload(_payload(row)),
        )
    connection.commit()


def _upsert_workflow_read_model_projection(
    *,
    connection: Any,
    definition: DpmBulkReviewCampaignDefinition,
) -> None:
    projection = _workflow_read_model_projection(definition)
    connection.execute(
        """
        INSERT INTO dpm_bulk_review_campaign_workflow_read_model (
            campaign_id,
            campaign_version,
            definition_status,
            as_of_date,
            definition_content_hash,
            workflow_read_model_hash,
            board_status,
            next_action,
            assignment_escalation_tier,
            assignment_sla_posture,
            assigned_actor_ids,
            assignment_task_statuses,
            assignment_task_escalation_tiers,
            assignment_task_sla_postures,
            maker_checker_outcomes,
            approval_decision_types,
            approval_decision_count,
            assignment_action_count,
            assignment_task_count,
            assignment_task_transition_count,
            maker_checker_control_count,
            projection_payload_json,
            projected_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (campaign_id, campaign_version) DO UPDATE SET
            definition_status = EXCLUDED.definition_status,
            as_of_date = EXCLUDED.as_of_date,
            definition_content_hash = EXCLUDED.definition_content_hash,
            workflow_read_model_hash = EXCLUDED.workflow_read_model_hash,
            board_status = EXCLUDED.board_status,
            next_action = EXCLUDED.next_action,
            assignment_escalation_tier = EXCLUDED.assignment_escalation_tier,
            assignment_sla_posture = EXCLUDED.assignment_sla_posture,
            assigned_actor_ids = EXCLUDED.assigned_actor_ids,
            assignment_task_statuses = EXCLUDED.assignment_task_statuses,
            assignment_task_escalation_tiers = EXCLUDED.assignment_task_escalation_tiers,
            assignment_task_sla_postures = EXCLUDED.assignment_task_sla_postures,
            maker_checker_outcomes = EXCLUDED.maker_checker_outcomes,
            approval_decision_types = EXCLUDED.approval_decision_types,
            approval_decision_count = EXCLUDED.approval_decision_count,
            assignment_action_count = EXCLUDED.assignment_action_count,
            assignment_task_count = EXCLUDED.assignment_task_count,
            assignment_task_transition_count = EXCLUDED.assignment_task_transition_count,
            maker_checker_control_count = EXCLUDED.maker_checker_control_count,
            projection_payload_json = EXCLUDED.projection_payload_json,
            projected_at = EXCLUDED.projected_at
        """,
        (
            projection["campaign_id"],
            projection["campaign_version"],
            projection["definition_status"],
            projection["as_of_date"],
            projection["definition_content_hash"],
            projection["workflow_read_model_hash"],
            projection["board_status"],
            projection["next_action"],
            projection["assignment_escalation_tier"],
            projection["assignment_sla_posture"],
            projection["assigned_actor_ids"],
            projection["assignment_task_statuses"],
            projection["assignment_task_escalation_tiers"],
            projection["assignment_task_sla_postures"],
            projection["maker_checker_outcomes"],
            projection["approval_decision_types"],
            projection["approval_decision_count"],
            projection["assignment_action_count"],
            projection["assignment_task_count"],
            projection["assignment_task_transition_count"],
            projection["maker_checker_control_count"],
            json.dumps(projection, sort_keys=True, separators=(",", ":"), default=str),
            datetime.now(timezone.utc),
        ),
    )


def _workflow_read_model_projection(
    definition: DpmBulkReviewCampaignDefinition,
) -> dict[str, object]:
    board = build_bulk_review_campaign_workflow_board_item(
        definition=definition,
        requested_as_of_date=definition.as_of_date,
        actor_id=None,
        active_on=None,
    )
    assignment_plan = build_bulk_review_campaign_assignment_plan_item(
        definition=definition,
        requested_as_of_date=definition.as_of_date,
        actor_id=None,
        active_on=None,
    )
    assignment_task_transition_count = sum(
        len(task.transitions) for task in definition.assignment_tasks
    )
    assigned_actor_ids = sorted(
        {
            actor_id
            for values in [
                board.assigned_actor_ids,
                assignment_plan.assigned_actor_ids,
                *[action.assigned_actor_ids for action in definition.assignment_actions],
                *[task.assigned_actor_ids for task in definition.assignment_tasks],
            ]
            for actor_id in values
            if actor_id
        }
    )
    projection: dict[str, object] = {
        "projection_name": "BulkReviewCampaignWorkflowReadModel",
        "projection_version": "v1",
        "projection_owner": "lotus-manage",
        "durable_source_table": "dpm_bulk_review_campaign_definitions",
        "durable_source_payload": "payload_json",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "definition_status": definition.status,
        "as_of_date": definition.as_of_date,
        "definition_content_hash": definition.content_hash,
        "board_status": board.board_status,
        "next_action": board.next_action,
        "assignment_escalation_tier": assignment_plan.escalation_tier,
        "assignment_sla_posture": assignment_plan.sla_posture,
        "assigned_actor_ids": assigned_actor_ids,
        "assignment_task_statuses": sorted({task.status for task in definition.assignment_tasks}),
        "assignment_task_escalation_tiers": sorted(
            {task.escalation_tier for task in definition.assignment_tasks}
        ),
        "assignment_task_sla_postures": sorted(
            {task.sla_posture for task in definition.assignment_tasks}
        ),
        "maker_checker_outcomes": sorted(
            {control.control_outcome for control in definition.maker_checker_controls}
        ),
        "approval_decision_types": sorted(
            {decision.decision_type for decision in definition.approval_decisions}
        ),
        "approval_decision_count": len(definition.approval_decisions),
        "assignment_action_count": len(definition.assignment_actions),
        "assignment_task_count": len(definition.assignment_tasks),
        "assignment_task_transition_count": assignment_task_transition_count,
        "maker_checker_control_count": len(definition.maker_checker_controls),
        "lineage": {
            "definition_content_hash": definition.content_hash,
            "board_content_hash": board.content_hash,
            "assignment_plan_content_hash": assignment_plan.content_hash,
        },
    }
    projection["workflow_read_model_hash"] = hash_canonical_payload(
        strip_keys(projection, exclude={"workflow_read_model_hash"})
    )
    return projection


def _payload(row: Any) -> str | dict[str, Any]:
    payload = row["payload_json"]
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return json.dumps(payload, default=str)
    return payload


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row
