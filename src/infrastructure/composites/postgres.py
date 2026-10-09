"""PostgreSQL adapter for immutable composite eligibility evidence."""

from __future__ import annotations

import json
from contextlib import closing
from typing import Any

from src.core.common.capabilities import has_psycopg
from src.core.composite_membership import (
    DpmCompositeMembershipRevision,
)
from src.core.composite_definition_versions import (
    CompositeDefinition,
    decode_composite_definition,
    validated_definition_snapshot,
)
from src.core.composite_repository import (
    DpmCompositeConflictError,
    DpmCompositeRepository,
    DpmCompositeResultPage,
)
from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationPage,
    DpmCompositePublicationReceipt,
)
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_eligibility.monthly_amendment import MonthlyApproval, MonthlyProposal
from src.core.composite_eligibility.monthly_evidence import MonthlyPublicationReceipt
from src.infrastructure.composites import (
    policy_control,
    membership_store,
    universe_store,
    evaluation_control,
    staged_postgres,
    monthly_evidence,
)
from src.core.composite_eligibility.staged_ports import SubjectKey, ControlKind
from src.core.composite_eligibility.staged_controls import StagedControl
from src.core.composite_eligibility.staged_subject import EligibilitySubject
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalization,
    SubjectFinalizationReceipt,
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

    def save_eligibility_subject(self, *, subject: EligibilitySubject) -> None:
        with closing(self._connect()) as connection:
            staged_postgres.save_subject(connection, subject)
            connection.commit()

    def get_eligibility_subject(self, *, key: SubjectKey) -> EligibilitySubject | None:
        with closing(self._connect()) as connection:
            return staged_postgres.get_subject(connection, key)

    def save_subject_control(self, *, control: StagedControl) -> None:
        with closing(self._connect()) as connection:
            staged_postgres.save_control(connection, control)
            connection.commit()

    def get_subject_control(
        self, *, key: SubjectKey, kind: ControlKind, revision: str
    ) -> StagedControl | None:
        with closing(self._connect()) as connection:
            return staged_postgres.get_control(connection, key, kind, revision)

    def finalize_eligibility_subject(
        self, *, finalization: SubjectFinalization
    ) -> SubjectFinalizationReceipt:
        with closing(self._connect()) as connection:
            receipt = staged_postgres.finalize(connection, finalization)
            connection.commit()
            return receipt

    def get_eligibility_finalization(self, *, key: SubjectKey) -> SubjectFinalizationReceipt | None:
        with closing(self._connect()) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            return staged_postgres.get_finalization(connection, key)

    def resolve_eligibility_evidence(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
        approval_content_hash: str,
    ) -> SubjectFinalizationReceipt | None:
        with closing(self._connect()) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            row = connection.execute(
                """SELECT subject_revision FROM dpm_composite_monthly_evaluation_approvals
                WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND evaluation_revision=%s
                AND custody_mode='STAGED'""",
                (tenant_id, composite_id, definition_version, evaluation_revision),
            ).fetchone()
            if row is None:
                return None
            receipt = staged_postgres.get_finalization(
                connection, (tenant_id, composite_id, definition_version, row["subject_revision"])
            )
            if (
                receipt is not None
                and receipt.finalization.evaluation_approval.content_hash != approval_content_hash
            ):
                raise DpmCompositeConflictError("COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH")
            return receipt

    def resolve_monthly_eligibility_evidence(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
        approval_content_hash: str,
    ) -> MonthlyPublicationReceipt | None:
        with closing(self._connect()) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            return monthly_evidence.resolve(
                connection,
                (tenant_id, composite_id, definition_version, evaluation_revision),
                approval_content_hash,
            )

    def save_monthly_evaluation_proposal(self, *, proposal: MonthlyProposal) -> None:
        with closing(self._connect()) as connection:
            evaluation_control.save_proposal(connection, proposal)
            connection.commit()

    def get_monthly_evaluation_proposal(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
    ) -> MonthlyProposal | None:
        with closing(self._connect()) as connection:
            return evaluation_control.get_proposal(
                connection, (tenant_id, composite_id, definition_version, evaluation_revision)
            )

    def save_monthly_evaluation_approval(self, *, approval: MonthlyApproval) -> None:
        with closing(self._connect()) as connection:
            evaluation_control.save_approval(connection, approval)
            connection.commit()

    def get_monthly_evaluation_approval(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
    ) -> MonthlyApproval | None:
        with closing(self._connect()) as connection:
            return evaluation_control.get_approval(
                connection, (tenant_id, composite_id, definition_version, evaluation_revision)
            )

    def save_monthly_policy_proposal(self, *, proposal: MonthlyPolicyProposal) -> None:
        with closing(self._connect()) as connection:
            policy_control.save_proposal(connection, proposal)
            connection.commit()

    def get_monthly_policy_proposal(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
        proposal_revision: str,
    ) -> MonthlyPolicyProposal | None:
        with closing(self._connect()) as connection:
            return policy_control.get_proposal(
                connection, (tenant_id, composite_id, definition_version, month, proposal_revision)
            )

    def save_monthly_policy_approval(self, *, approval: MonthlyPolicyApproval) -> None:
        with closing(self._connect()) as connection:
            policy_control.save_approval(connection, approval)
            connection.commit()

    def get_monthly_policy_approval(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
    ) -> MonthlyPolicyApproval | None:
        with closing(self._connect()) as connection:
            return policy_control.get_approval(
                connection, (tenant_id, composite_id, definition_version, month)
            )

    def save_definition(self, *, definition: CompositeDefinition) -> None:
        definition = validated_definition_snapshot(definition)
        with closing(self._connect()) as connection:
            publication_sql.lock_tenant_publication_order(
                connection=connection, tenant_id=definition.tenant_id
            )
            reserved = connection.execute(
                """SELECT subject_revision FROM dpm_composite_eligibility_subjects
                WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s""",
                (definition.tenant_id, definition.composite_id, definition.definition_version),
            ).fetchone()
            if reserved is not None:
                receipt = staged_postgres.get_finalization(
                    connection,
                    (
                        definition.tenant_id,
                        definition.composite_id,
                        definition.definition_version,
                        reserved["subject_revision"],
                    ),
                )
                if receipt is None or receipt.finalization.definition != definition:
                    raise DpmCompositeConflictError(
                        "COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT"
                    )
                return
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
    ) -> CompositeDefinition | None:
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
    ) -> DpmCompositeResultPage[CompositeDefinition]:
        with closing(self._connect()) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM dpm_composite_definitions WHERE tenant_id = %s",
                (tenant_id,),
            ).fetchone()["count"]
            rows = connection.execute(
                """
                SELECT payload_json FROM dpm_composite_definitions
                WHERE tenant_id = %s
                ORDER BY inception_date DESC, composite_id DESC, definition_version DESC
                LIMIT %s OFFSET %s
                """,
                (tenant_id, limit, offset),
            ).fetchall()
        return DpmCompositeResultPage(items=[_load_definition(row) for row in rows], count=count)

    def save_membership_revision(self, *, revision: DpmCompositeMembershipRevision) -> None:
        with closing(self._connect()) as connection:
            publication_sql.lock_tenant_publication_order(
                connection=connection, tenant_id=revision.tenant_id
            )
            membership_store.store_membership_revision(connection=connection, revision=revision)
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
    ) -> DpmCompositeResultPage[DpmCompositeMembershipRevision]:
        with closing(self._connect()) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            count = connection.execute(
                """
                SELECT COUNT(*) AS count FROM dpm_composite_membership_revisions
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                """,
                (tenant_id, composite_id, definition_version),
            ).fetchone()["count"]
            rows = connection.execute(
                """
                SELECT payload_json FROM dpm_composite_membership_revisions
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                ORDER BY decided_at DESC, membership_revision DESC
                LIMIT %s OFFSET %s
                """,
                (tenant_id, composite_id, definition_version, limit, offset),
            ).fetchall()
        return DpmCompositeResultPage(
            items=[_load_membership_revision(row) for row in rows], count=count
        )

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

    def save_universe_attestation(self, *, attestation: DpmCompositeUniverseAttestation) -> None:
        with closing(self._connect()) as connection:
            universe_store.store_universe_attestation(
                connection=connection, attestation=attestation
            )
            connection.commit()

    def get_universe_attestation(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
        attestation_version: str,
    ) -> DpmCompositeUniverseAttestation | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json, content_hash, membership_content_hash
                FROM dpm_composite_universe_attestations
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                    AND membership_revision = %s AND attestation_version = %s
                """,
                (
                    tenant_id,
                    composite_id,
                    definition_version,
                    membership_revision,
                    attestation_version,
                ),
            ).fetchone()
        return _load_universe_attestation(row) if row is not None else None

    def list_universe_attestations(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
        limit: int,
        offset: int,
    ) -> DpmCompositeResultPage[DpmCompositeUniverseAttestation]:
        key = (tenant_id, composite_id, definition_version, membership_revision)
        with closing(self._connect()) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            count = connection.execute(
                """
                SELECT COUNT(*) AS count FROM dpm_composite_universe_attestations
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                    AND membership_revision = %s
                """,
                key,
            ).fetchone()["count"]
            rows = connection.execute(
                """
                SELECT payload_json, content_hash, membership_content_hash
                FROM dpm_composite_universe_attestations
                WHERE tenant_id = %s AND composite_id = %s AND definition_version = %s
                    AND membership_revision = %s
                ORDER BY attested_at DESC, attestation_version DESC
                LIMIT %s OFFSET %s
                """,
                (*key, limit, offset),
            ).fetchall()
        return DpmCompositeResultPage(
            items=[_load_universe_attestation(row) for row in rows], count=count
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


def _load_definition(row: Any) -> CompositeDefinition:
    return decode_composite_definition(_payload(row))


def _load_membership_revision(row: Any) -> DpmCompositeMembershipRevision:
    return load_model_json(DpmCompositeMembershipRevision, _payload(row))


def _load_universe_attestation(row: Any) -> DpmCompositeUniverseAttestation:
    attestation = load_model_json(DpmCompositeUniverseAttestation, _payload(row))
    if (row["content_hash"], row["membership_content_hash"]) != (
        attestation.content_hash,
        attestation.membership_content_hash,
    ):
        raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_ATTESTATION_INTEGRITY_CONFLICT")
    return attestation


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
