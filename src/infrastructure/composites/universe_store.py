"""Shared immutable attestation storage; caller owns transaction and publication ordering."""

from typing import Any
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.mandates.serialization import dump_model_json


def store_universe_attestation(
    *, connection: Any, attestation: DpmCompositeUniverseAttestation
) -> None:
    attestation = DpmCompositeUniverseAttestation.model_validate(
        attestation.model_dump(mode="json")
    )
    key = (
        attestation.tenant_id,
        attestation.composite_id,
        attestation.definition_version,
        attestation.membership_revision,
    )
    revision = connection.execute(
        """
        SELECT content_hash FROM dpm_composite_membership_revisions
        WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
            AND membership_revision = %s
        """,
        key,
    ).fetchone()
    if revision is None:
        raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_MEMBERSHIP_NOT_FOUND")
    if revision["content_hash"] != attestation.membership_content_hash:
        raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_MEMBERSHIP_HASH_MISMATCH")
    connection.execute(
        """
        INSERT INTO dpm_composite_universe_attestations (
            tenant_id, composite_id, definition_version, membership_revision,
            membership_content_hash, attestation_version, attested_at, content_hash,
            payload_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (
            tenant_id, composite_id, definition_version, membership_revision,
            attestation_version
        ) DO NOTHING
        """,
        (
            *key,
            attestation.membership_content_hash,
            attestation.attestation_version,
            attestation.attested_at,
            attestation.content_hash,
            dump_model_json(attestation),
        ),
    )
    persisted = connection.execute(
        """
        SELECT content_hash, membership_content_hash
        FROM dpm_composite_universe_attestations
        WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
            AND membership_revision = %s AND attestation_version = %s
        """,
        (*key, attestation.attestation_version),
    ).fetchone()
    if persisted is None or (
        persisted["content_hash"],
        persisted["membership_content_hash"],
    ) != (attestation.content_hash, attestation.membership_content_hash):
        connection.rollback()
        raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_ATTESTATION_IMMUTABLE_CONFLICT")
