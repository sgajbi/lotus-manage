"""Shared immutable revision storage; caller owns transaction and publication ordering."""

from typing import Any
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites import publication as publication_sql
from src.infrastructure.mandates.serialization import dump_model_json


def store_membership_revision(*, connection: Any, revision: DpmCompositeMembershipRevision) -> None:
    revision = DpmCompositeMembershipRevision.model_validate(revision.model_dump(mode="json"))
    key = (revision.tenant_id, revision.composite_id, revision.definition_version)
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
            raise DpmCompositeConflictError("COMPOSITE_MEMBERSHIP_SUPERSEDED_REVISION_NOT_FOUND")
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
