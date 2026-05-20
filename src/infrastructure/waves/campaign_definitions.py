from __future__ import annotations

import json
from copy import deepcopy
from contextlib import closing
from threading import Lock
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.campaign_repository import (
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionRepository,
)
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class InMemoryDpmBulkReviewCampaignDefinitionRepository(DpmBulkReviewCampaignDefinitionRepository):
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
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmBulkReviewCampaignDefinition]:
        with self._lock:
            definitions = [
                definition
                for definition in self._definitions.values()
                if (campaign_id is None or definition.campaign_id == campaign_id)
                and (status is None or definition.status == status)
                and (as_of_date is None or definition.as_of_date == as_of_date)
            ]
            definitions.sort(
                key=lambda definition: (
                    definition.as_of_date,
                    definition.campaign_id,
                    definition.campaign_version,
                ),
                reverse=True,
            )
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

    def record_definition_launch(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        key = (definition.campaign_id, definition.campaign_version)
        with self._lock:
            existing = self._definitions.get(key)
            if existing is None:
                return None
            if existing.content_hash == definition.content_hash:
                return deepcopy(existing)
            if existing.status != "ACTIVE":
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            self._definitions[key] = deepcopy(definition)
            return deepcopy(definition)

    def record_definition_approval_decision(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        key = (definition.campaign_id, definition.campaign_version)
        with self._lock:
            existing = self._definitions.get(key)
            if existing is None:
                return None
            if existing.content_hash == definition.content_hash:
                return deepcopy(existing)
            if existing.status != "ACTIVE":
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            self._definitions[key] = deepcopy(definition)
            return deepcopy(definition)

    def record_definition_assignment_action(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
    ) -> DpmBulkReviewCampaignDefinition | None:
        key = (definition.campaign_id, definition.campaign_version)
        with self._lock:
            existing = self._definitions.get(key)
            if existing is None:
                return None
            if existing.content_hash == definition.content_hash:
                return deepcopy(existing)
            if existing.status != "ACTIVE":
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            self._definitions[key] = deepcopy(definition)
            return deepcopy(definition)


class PostgresDpmBulkReviewCampaignDefinitionRepository:
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
        return load_model_json(DpmBulkReviewCampaignDefinition, _payload(row))

    def list_definitions(
        self,
        *,
        campaign_id: str | None = None,
        status: str | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
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
        args.extend([limit, offset])
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT payload_json
                FROM dpm_bulk_review_campaign_definitions
                {where}
                ORDER BY as_of_date DESC, campaign_id DESC, campaign_version DESC
                LIMIT %s OFFSET %s
                """,
                tuple(args),
            ).fetchall()
        return [load_model_json(DpmBulkReviewCampaignDefinition, _payload(row)) for row in rows]

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
            existing = load_model_json(DpmBulkReviewCampaignDefinition, _payload(persisted))
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
            existing = load_model_json(DpmBulkReviewCampaignDefinition, _payload(persisted))
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
            connection.commit()
            return definition

    def record_definition_launch(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
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
            existing = load_model_json(DpmBulkReviewCampaignDefinition, _payload(persisted))
            if existing.content_hash == definition.content_hash:
                connection.rollback()
                return existing
            if existing.status != "ACTIVE":
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            updated = connection.execute(
                """
                UPDATE dpm_bulk_review_campaign_definitions
                SET content_hash = %s, payload_json = %s
                WHERE campaign_id = %s AND campaign_version = %s AND status = 'ACTIVE'
                """,
                (
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
            connection.commit()
            return definition

    def record_definition_approval_decision(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
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
            existing = load_model_json(DpmBulkReviewCampaignDefinition, _payload(persisted))
            if existing.content_hash == definition.content_hash:
                connection.rollback()
                return existing
            if existing.status != "ACTIVE":
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            updated = connection.execute(
                """
                UPDATE dpm_bulk_review_campaign_definitions
                SET content_hash = %s, payload_json = %s
                WHERE campaign_id = %s AND campaign_version = %s AND status = 'ACTIVE'
                """,
                (
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
            connection.commit()
            return definition

    def record_definition_assignment_action(
        self,
        *,
        definition: DpmBulkReviewCampaignDefinition,
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
            existing = load_model_json(DpmBulkReviewCampaignDefinition, _payload(persisted))
            if existing.content_hash == definition.content_hash:
                connection.rollback()
                return existing
            if existing.status != "ACTIVE":
                connection.rollback()
                raise DpmBulkReviewCampaignDefinitionConflictError(
                    "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT"
                )
            updated = connection.execute(
                """
                UPDATE dpm_bulk_review_campaign_definitions
                SET content_hash = %s, payload_json = %s
                WHERE campaign_id = %s AND campaign_version = %s AND status = 'ACTIVE'
                """,
                (
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
            connection.commit()
            return definition

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")


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
