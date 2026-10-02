"""PostgreSQL adapter for immutable composite eligibility evidence."""

from __future__ import annotations

import json
from contextlib import closing
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.composite_membership import (
    DpmCompositeDefinition,
    DpmCompositeMembershipRevision,
)
from src.core.composite_repository import DpmCompositeConflictError, DpmCompositeRepository
from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationPage,
    DpmCompositePublicationReceipt,
)
from src.infrastructure.composites import publication as publication_sql
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json
from src.infrastructure.postgres_access import connect_postgres
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresDpmCompositeRepository(DpmCompositeRepository):
    """Durable, tenant-scoped persistence for Manage-owned composite evidence."""

    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_COMPOSITE_POSTGRES_DSN_REQUIRED")
        if not has_psycopg():
            raise RuntimeError("DPM_COMPOSITE_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_definition(self, *, definition: DpmCompositeDefinition) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_composite_definitions (
                    tenant_id, composite_id, definition_version, inception_date, content_hash,
                    payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, composite_id, definition_version) DO NOTHING
                """,
                (
                    definition.tenant_id,
                    definition.composite_id,
                    definition.definition_version,
                    definition.inception_date,
                    definition.content_hash,
                    dump_model_json(definition),
                ),
            )
            persisted = connection.execute(
                """
                SELECT content_hash FROM dpm_composite_definitions
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                """,
                (definition.tenant_id, definition.composite_id, definition.definition_version),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != definition.content_hash:
                connection.rollback()
                raise DpmCompositeConflictError("COMPOSITE_DEFINITION_IMMUTABLE_CONFLICT")
            connection.commit()

    def get_definition(
        self, *, tenant_id: str, composite_id: str, definition_version: str
    ) -> DpmCompositeDefinition | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM dpm_composite_definitions
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                """,
                (tenant_id, composite_id, definition_version),
            ).fetchone()
        return _load_definition(row) if row is not None else None

    def list_definitions(
        self, *, tenant_id: str, limit: int, offset: int
    ) -> list[DpmCompositeDefinition]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM dpm_composite_definitions
                WHERE tenant_id = %s
                ORDER BY inception_date DESC, composite_id DESC, definition_version DESC
                LIMIT %s OFFSET %s
                """,
                (tenant_id, limit, offset),
            ).fetchall()
        return [_load_definition(row) for row in rows]

    def save_membership_revision(self, *, revision: DpmCompositeMembershipRevision) -> None:
        key = (revision.tenant_id, revision.composite_id, revision.definition_version)
        with closing(self._connect()) as connection:
            publication_sql.lock_tenant_publication_order(
                connection=connection, tenant_id=revision.tenant_id
            )
            definition = connection.execute(
                """
                SELECT 1 FROM dpm_composite_definitions
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                """,
                key,
            ).fetchone()
            if definition is None:
                connection.rollback()
                raise DpmCompositeConflictError("COMPOSITE_MEMBERSHIP_DEFINITION_NOT_FOUND")
            if revision.supersedes_membership_revision is not None:
                parent = connection.execute(
                    """
                    SELECT 1 FROM dpm_composite_membership_revisions
                    WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                        AND membership_revision = %s
                    """,
                    (*key, revision.supersedes_membership_revision),
                ).fetchone()
                if parent is None:
                    connection.rollback()
                    raise DpmCompositeConflictError(
                        "COMPOSITE_MEMBERSHIP_SUPERSEDED_REVISION_NOT_FOUND"
                    )
            connection.execute(
                """
                INSERT INTO dpm_composite_membership_revisions (
                    tenant_id, composite_id, definition_version, membership_revision, decided_at,
                    content_hash, payload_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, composite_id, definition_version, membership_revision)
                DO NOTHING
                """,
                (
                    *key,
                    revision.membership_revision,
                    revision.decided_at,
                    revision.content_hash,
                    dump_model_json(revision),
                ),
            )
            persisted = connection.execute(
                """
                SELECT content_hash FROM dpm_composite_membership_revisions
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                    AND membership_revision = %s
                """,
                (*key, revision.membership_revision),
            ).fetchone()
            if persisted is None or persisted["content_hash"] != revision.content_hash:
                connection.rollback()
                raise DpmCompositeConflictError("COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT")
            publication_sql.publish_revision(connection=connection, revision=revision)
            connection.commit()

    def get_membership_revision(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
    ) -> DpmCompositeMembershipRevision | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM dpm_composite_membership_revisions
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                    AND membership_revision = %s
                """,
                (tenant_id, composite_id, definition_version, membership_revision),
            ).fetchone()
        return _load_membership_revision(row) if row is not None else None

    def list_membership_revisions(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        limit: int,
        offset: int,
    ) -> list[DpmCompositeMembershipRevision]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM dpm_composite_membership_revisions
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                ORDER BY decided_at DESC, membership_revision DESC
                LIMIT %s OFFSET %s
                """,
                (tenant_id, composite_id, definition_version, limit, offset),
            ).fetchall()
        return [_load_membership_revision(row) for row in rows]

    def get_publication(
        self, *, tenant_id: str, sequence: int
    ) -> DpmCompositeMembershipPublication | None:
        with closing(self._connect()) as connection:
            return publication_sql.get_publication(
                connection=connection, tenant_id=tenant_id, sequence=sequence
            )

    def assert_membership_published(self, *, revision: DpmCompositeMembershipRevision) -> None:
        with closing(self._connect()) as connection:
            publication_sql.assert_membership_published(connection=connection, revision=revision)

    def list_publications(
        self, *, tenant_id: str, after_sequence: int, limit: int
    ) -> DpmCompositePublicationPage:
        with closing(self._connect()) as connection:
            return publication_sql.list_publications(
                connection=connection,
                tenant_id=tenant_id,
                after_sequence=after_sequence,
                limit=limit,
            )

    def save_receipt(self, *, receipt: DpmCompositePublicationReceipt) -> bool:
        with closing(self._connect()) as connection:
            created = publication_sql.save_receipt(connection=connection, receipt=receipt)
            connection.commit()
            return created

    def list_receipts(
        self, *, tenant_id: str, publication_sequence: int
    ) -> list[DpmCompositePublicationReceipt]:
        with closing(self._connect()) as connection:
            return publication_sql.list_receipts(
                connection=connection,
                tenant_id=tenant_id,
                publication_sequence=publication_sequence,
            )

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="dpm")

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return connect_postgres(
            self._dsn,
            connect_fn=psycopg.connect,
            row_factory=dict_row,
            application_name="lotus-manage-composite-repository",
        )


def _load_definition(row: Any) -> DpmCompositeDefinition:
    return load_model_json(DpmCompositeDefinition, _payload(row))


def _load_membership_revision(row: Any) -> DpmCompositeMembershipRevision:
    return load_model_json(DpmCompositeMembershipRevision, _payload(row))


def _payload(row: Any) -> str | dict[str, Any]:
    payload = row["payload_json"]
    if isinstance(payload, (str, dict)):
        return payload
    return json.dumps(payload, default=str)


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


__all__ = ["PostgresDpmCompositeRepository"]
