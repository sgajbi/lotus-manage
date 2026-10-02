"""Atomic PostgreSQL publication and retrieval-receipt operations for composites."""

from __future__ import annotations

from typing import Any

from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationPage,
    DpmCompositePublicationReceipt,
    publication_from_revision,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.mandates.serialization import load_model_json


def lock_tenant_publication_order(*, connection: Any, tenant_id: str) -> None:
    # A per-tenant transaction lock makes sequence allocation follow commit order.
    # Without it, a late commit with a lower sequence can be skipped by a poller.
    connection.execute(
        "SELECT pg_advisory_xact_lock(hashtext(%s)::bigint)",
        (f"dpm-composite-publication:{tenant_id}",),
    )


def publish_revision(*, connection: Any, revision: DpmCompositeMembershipRevision) -> None:
    key = (
        revision.tenant_id,
        revision.composite_id,
        revision.definition_version,
        revision.membership_revision,
    )
    connection.execute(
        """
        INSERT INTO dpm_composite_membership_publications (
            tenant_id, composite_id, definition_version, membership_revision,
            membership_content_hash
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, composite_id, definition_version, membership_revision)
        DO NOTHING
        """,
        (*key, revision.content_hash),
    )
    persisted = connection.execute(
        """
        SELECT membership_content_hash FROM dpm_composite_membership_publications
        WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
            AND membership_revision = %s
        """,
        key,
    ).fetchone()
    if persisted is None or persisted["membership_content_hash"] != revision.content_hash:
        raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_IMMUTABLE_CONFLICT")


_PUBLICATION_SELECT = """
    SELECT p.sequence, p.published_at, r.payload_json
    FROM dpm_composite_membership_publications AS p
    JOIN dpm_composite_membership_revisions AS r
      ON r.tenant_id = p.tenant_id AND r.composite_id = p.composite_id
     AND r.definition_version = p.definition_version
     AND r.membership_revision = p.membership_revision
"""


def _publication_from_row(row: Any) -> DpmCompositeMembershipPublication:
    revision = load_model_json(DpmCompositeMembershipRevision, row["payload_json"])
    return publication_from_revision(
        revision=revision,
        sequence=row["sequence"],
        published_at=row["published_at"],
    )


def get_publication(
    *, connection: Any, tenant_id: str, sequence: int
) -> DpmCompositeMembershipPublication | None:
    row = connection.execute(
        _PUBLICATION_SELECT + " WHERE p.tenant_id = %s AND p.sequence = %s",
        (tenant_id, sequence),
    ).fetchone()
    return _publication_from_row(row) if row is not None else None


def list_publications(
    *, connection: Any, tenant_id: str, after_sequence: int, limit: int
) -> DpmCompositePublicationPage:
    high_watermark = connection.execute(
        """
        SELECT COALESCE(MAX(sequence), 0) AS high_watermark
        FROM dpm_composite_membership_publications WHERE tenant_id = %s
        """,
        (tenant_id,),
    ).fetchone()["high_watermark"]
    if after_sequence > high_watermark:
        raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_CURSOR_AHEAD")
    rows = connection.execute(
        _PUBLICATION_SELECT
        + """
        WHERE p.tenant_id = %s AND p.sequence > %s AND p.sequence <= %s
        ORDER BY p.sequence ASC LIMIT %s
        """,
        (tenant_id, after_sequence, high_watermark, limit + 1),
    ).fetchall()
    items = [_publication_from_row(row) for row in rows[:limit]]
    return DpmCompositePublicationPage(
        items=items,
        high_watermark=high_watermark,
        next_sequence=items[-1].sequence if items else after_sequence,
        has_more=len(rows) > limit,
    )


def save_receipt(*, connection: Any, receipt: DpmCompositePublicationReceipt) -> bool:
    publication = connection.execute(
        """
        SELECT membership_content_hash FROM dpm_composite_membership_publications
        WHERE tenant_id = %s AND sequence = %s
        """,
        (receipt.tenant_id, receipt.publication_sequence),
    ).fetchone()
    if publication is None:
        raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_NOT_FOUND")
    if publication["membership_content_hash"] != receipt.membership_content_hash:
        raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_HASH_MISMATCH")
    created = connection.execute(
        """
        INSERT INTO dpm_composite_publication_receipts (
            tenant_id, publication_sequence, consumer_id, membership_content_hash,
            receipt_evidence_hash, disposition, reason_code, received_at, correlation_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, publication_sequence, consumer_id) DO NOTHING
        RETURNING publication_sequence
        """,
        (
            receipt.tenant_id,
            receipt.publication_sequence,
            receipt.consumer_id,
            receipt.membership_content_hash,
            receipt.receipt_evidence_hash,
            receipt.disposition,
            receipt.reason_code,
            receipt.received_at,
            receipt.correlation_id,
        ),
    ).fetchone()
    if created is not None:
        return True
    existing = connection.execute(
        """
        SELECT membership_content_hash, receipt_evidence_hash, disposition, reason_code
        FROM dpm_composite_publication_receipts
        WHERE tenant_id = %s AND publication_sequence = %s AND consumer_id = %s
        """,
        (receipt.tenant_id, receipt.publication_sequence, receipt.consumer_id),
    ).fetchone()
    if existing is None or any(
        existing[field] != getattr(receipt, field)
        for field in (
            "membership_content_hash",
            "receipt_evidence_hash",
            "disposition",
            "reason_code",
        )
    ):
        raise DpmCompositeConflictError("COMPOSITE_RECEIPT_IMMUTABLE_CONFLICT")
    return False


def list_receipts(
    *, connection: Any, tenant_id: str, publication_sequence: int
) -> list[DpmCompositePublicationReceipt]:
    rows = connection.execute(
        """
        SELECT tenant_id, publication_sequence, consumer_id, membership_content_hash,
            receipt_evidence_hash, disposition, reason_code, received_at, correlation_id
        FROM dpm_composite_publication_receipts
        WHERE tenant_id = %s AND publication_sequence = %s
        ORDER BY consumer_id
        """,
        (tenant_id, publication_sequence),
    ).fetchall()
    return [DpmCompositePublicationReceipt.model_validate(row) for row in rows]


__all__ = [
    "get_publication",
    "list_publications",
    "list_receipts",
    "lock_tenant_publication_order",
    "publish_revision",
    "save_receipt",
]
