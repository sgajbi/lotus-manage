"""Subject staging uses the existing control tables and canonical publication transaction."""

import json
from typing import Any, TypeVar
from pydantic import BaseModel

from src.core.composite_definition_versions import decode_composite_definition
from src.core.composite_eligibility.staged_controls import (
    STAGED_CONTROL_ADAPTER,
    StagedControl,
    SubjectPolicyProposal,
    SubjectPolicyApproval,
    SubjectEvaluationProposal,
    control_subject,
    control_revision,
)
from src.core.composite_eligibility.staged_custody import (
    predecessor,
    require_control_custody,
    require_finalized_custody,
)
from src.core.composite_eligibility.staged_ports import SubjectKey, ControlKind
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalizationRecord,
    decode_subject_finalization,
    decode_subject_receipt,
    finalization_receipt,
    SubjectFinalizationProof,
    initial_projection,
)
from src.core.composite_eligibility.staged_subject import EligibilitySubject, subject_key
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_publication import (
    publication_from_revision,
    DpmCompositeMembershipPublication,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites import membership_store, universe_store
from src.infrastructure.composites.publication import lock_tenant_publication_order
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json

CONTROL_TABLES = {
    "CompositeSubjectPolicyProposal": (
        "dpm_composite_monthly_policy_proposals",
        "proposal_revision",
    ),
    "CompositeSubjectPolicyApproval": (
        "dpm_composite_monthly_policy_approvals",
        "proposal_revision",
    ),
    "CompositeSubjectEvaluationProposal": (
        "dpm_composite_monthly_evaluation_proposals",
        "evaluation_revision",
    ),
    "CompositeSubjectEvaluationApproval": (
        "dpm_composite_monthly_evaluation_approvals",
        "evaluation_revision",
    ),
}
ModelT = TypeVar("ModelT", bound=BaseModel)


def get_subject(connection: Any, key: SubjectKey) -> EligibilitySubject | None:
    row = connection.execute(
        """SELECT content_hash,payload_json FROM dpm_composite_eligibility_subjects
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND subject_revision=%s""",
        key,
    ).fetchone()
    if row is None:
        return None
    subject = load_model_json(EligibilitySubject, row["payload_json"])
    if subject_key(subject) != key or subject.content_hash != row["content_hash"]:
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_INTEGRITY_CONFLICT")
    return subject


def save_subject(connection: Any, subject: EligibilitySubject) -> None:
    subject = EligibilitySubject.model_validate(subject.model_dump(mode="json"))
    key = subject_key(subject)
    lock_tenant_publication_order(connection=connection, tenant_id=key[0])
    retained = get_subject(connection, key)
    if retained is not None:
        _require_same(retained.content_hash, subject.content_hash)
        return
    reserved = connection.execute(
        """SELECT 1 FROM dpm_composite_eligibility_subjects
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s""",
        key[:3],
    ).fetchone()
    definition = connection.execute(
        """SELECT 1 FROM dpm_composite_definitions
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s""",
        key[:3],
    ).fetchone()
    if reserved is not None or definition is not None:
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT")
    connection.execute(
        """INSERT INTO dpm_composite_eligibility_subjects
        (tenant_id,composite_id,definition_version,subject_revision,month,content_hash,payload_json)
        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)""",
        (*key, subject.month, subject.content_hash, dump_model_json(subject)),
    )


def get_control(
    connection: Any, key: SubjectKey, kind: ControlKind, revision: str
) -> StagedControl | None:
    from psycopg import sql

    table, revision_column = CONTROL_TABLES[kind]
    # Identifiers are closed owner constants, never caller text. Every selector is bound.
    row = connection.execute(
        sql.SQL("""SELECT content_hash,subject_content_hash,payload_json FROM {}
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND subject_revision=%s
        AND {}=%s AND custody_mode='STAGED'""").format(
            sql.Identifier(table), sql.Identifier(revision_column)
        ),
        (*key, revision),
    ).fetchone()
    if row is None:
        return None
    control = STAGED_CONTROL_ADAPTER.validate_json(
        row["payload_json"]
        if isinstance(row["payload_json"], str)
        else dump_json(row["payload_json"])
    )
    subject = control_subject(control)
    if (
        subject_key(subject),
        control.product_name,
        control_revision(control),
        control.content_hash,
        subject.content_hash,
    ) != (key, kind, revision, row["content_hash"], row["subject_content_hash"]):
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_CONTROL_INTEGRITY_CONFLICT")
    return control


def dump_json(value: Any) -> str:
    return json.dumps(value)


def save_control(connection: Any, control: StagedControl) -> None:
    control = STAGED_CONTROL_ADAPTER.validate_python(control.model_dump(mode="json"))
    subject = control_subject(control)
    key = subject_key(subject)
    lock_tenant_publication_order(connection=connection, tenant_id=key[0])
    actual = get_subject(connection, key)
    if actual is None:
        raise ValueError("COMPOSITE_SUBJECT_NOT_FOUND")
    previous = predecessor(control)
    retained = get_control(connection, key, previous[0], previous[1]) if previous else None
    require_control_custody(control, actual, retained)
    existing = get_control(connection, key, control.product_name, control_revision(control))
    if existing is not None:
        _require_same(existing.content_hash, control.content_hash)
        return
    if get_receipt_row(connection, key) is not None:
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_ALREADY_FINALIZED_CONFLICT")
    base = (*key[:3], subject.month)
    tail = (control.content_hash, dump_model_json(control), key[3], subject.content_hash)
    if isinstance(control, SubjectPolicyProposal):
        connection.execute(
            """INSERT INTO dpm_composite_monthly_policy_proposals
            (tenant_id,composite_id,definition_version,month,proposal_revision,content_hash,payload_json,subject_revision,subject_content_hash)
            VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s) ON CONFLICT DO NOTHING""",
            (*base, control_revision(control), *tail),
        )
    elif isinstance(control, SubjectPolicyApproval):
        connection.execute(
            """INSERT INTO dpm_composite_monthly_policy_approvals
            (tenant_id,composite_id,definition_version,month,proposal_revision,proposal_content_hash,content_hash,payload_json,subject_revision,subject_content_hash)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s) ON CONFLICT DO NOTHING""",
            (*base, control_revision(control), control.proposal.content_hash, *tail),
        )
    elif isinstance(control, SubjectEvaluationProposal):
        connection.execute(
            """INSERT INTO dpm_composite_monthly_evaluation_proposals
            (tenant_id,composite_id,definition_version,month,evaluation_revision,parent_membership_revision,content_hash,payload_json,subject_revision,subject_content_hash,staged_policy_content_hash)
            VALUES (%s,%s,%s,%s,%s,NULL,%s,%s::jsonb,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (*base, control_revision(control), *tail, control.policy_approval.content_hash),
        )
    else:
        connection.execute(
            """INSERT INTO dpm_composite_monthly_evaluation_approvals
            (tenant_id,composite_id,definition_version,month,evaluation_revision,membership_revision,content_hash,payload_json,subject_revision,subject_content_hash,staged_proposal_content_hash)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (
                *base,
                control_revision(control),
                control.proposal.target_membership_revision,
                *tail,
                control.proposal.content_hash,
            ),
        )
    winner = get_control(connection, key, control.product_name, control_revision(control))
    if winner is None or winner.content_hash != control.content_hash:
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_ACTIVE_CONTROL_CONFLICT")


def get_receipt_row(connection: Any, key: SubjectKey) -> SubjectFinalizationProof | None:
    row = connection.execute(
        """SELECT content_hash,payload_json FROM dpm_composite_eligibility_finalizations
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND subject_revision=%s""",
        key,
    ).fetchone()
    if row is None:
        return None
    receipt = decode_subject_receipt(row["payload_json"])
    if (
        receipt.content_hash != row["content_hash"]
        or subject_key(receipt.finalization.subject) != key
    ):
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT")
    return receipt


def get_finalization(connection: Any, key: SubjectKey) -> SubjectFinalizationProof | None:
    receipt = get_receipt_row(connection, key)
    if receipt is None:
        return None
    approval = receipt.finalization.evaluation_approval
    target = approval.proposal.target_membership_revision
    definition_row = connection.execute(
        """SELECT payload_json,content_hash FROM dpm_composite_definitions
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s""",
        key[:3],
    ).fetchone()
    member_row = connection.execute(
        """SELECT payload_json,content_hash FROM dpm_composite_membership_revisions
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND membership_revision=%s""",
        (*key[:3], target),
    ).fetchone()
    universe_row = connection.execute(
        """SELECT payload_json,content_hash FROM dpm_composite_universe_attestations
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND membership_revision=%s AND attestation_version=%s""",
        (*key[:3], target, approval.proposal.evaluation_revision),
    ).fetchone()
    published = connection.execute(
        """SELECT * FROM dpm_composite_membership_publications
        WHERE tenant_id=%s AND sequence=%s""",
        (key[0], receipt.publication_sequence),
    ).fetchone()
    member = _retained_model(member_row, DpmCompositeMembershipRevision)
    universe = _retained_model(universe_row, DpmCompositeUniverseAttestation)
    definition = (
        decode_composite_definition(definition_row["payload_json"]) if definition_row else None
    )
    if definition is not None and definition.content_hash != definition_row["content_hash"]:
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT")
    require_finalized_custody(
        receipt,
        subject=get_subject(connection, key),
        approval=get_control(
            connection, key, approval.product_name, approval.proposal.evaluation_revision
        ),
        definition=definition,
        membership=member,
        universe=universe,
        publication=_retained_publication(published, member),
    )
    return receipt


def _retained_model(row: dict[str, Any] | None, model: type[ModelT]) -> ModelT | None:
    if row is None:
        return None
    result = load_model_json(model, row["payload_json"])
    if getattr(result, "content_hash") != row["content_hash"]:
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT")
    return result


def _retained_publication(
    row: dict[str, Any] | None, member: DpmCompositeMembershipRevision | None
) -> DpmCompositeMembershipPublication | None:
    if row is None or member is None:
        return None
    if (
        row["tenant_id"],
        row["composite_id"],
        row["definition_version"],
        row["membership_revision"],
        row["membership_content_hash"],
    ) != (
        member.tenant_id,
        member.composite_id,
        member.definition_version,
        member.membership_revision,
        member.content_hash,
    ):
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT")
    return publication_from_revision(
        revision=member, sequence=row["sequence"], published_at=row["published_at"]
    )


def finalize(connection: Any, finalization: SubjectFinalizationRecord) -> SubjectFinalizationProof:
    finalization = decode_subject_finalization(finalization.model_dump(mode="json"))
    key = subject_key(finalization.subject)
    lock_tenant_publication_order(connection=connection, tenant_id=key[0])
    retained = get_finalization(connection, key)
    if retained is not None:
        _require_same(retained.finalization.content_hash, finalization.content_hash)
        return retained
    approval = finalization.evaluation_approval
    if (
        get_subject(connection, key) != finalization.subject
        or get_control(
            connection, key, approval.product_name, approval.proposal.evaluation_revision
        )
        != approval
    ):
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_RETAINED_CONTROL_MISMATCH")
    definition = finalization.definition
    connection.execute(
        """INSERT INTO dpm_composite_definitions
        (tenant_id,composite_id,definition_version,inception_date,content_hash,payload_json)
        VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
        (*key[:3], definition.inception_date, definition.content_hash, dump_model_json(definition)),
    )
    revision, universe = initial_projection(
        approval.proposal, approval.claims_digest, approval.approved_by, approval.approved_at
    )
    membership_store.store_membership_revision(connection=connection, revision=revision)
    universe_store.store_universe_attestation(connection=connection, attestation=universe)
    sequence = connection.execute(
        """SELECT sequence FROM dpm_composite_membership_publications
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND membership_revision=%s""",
        (*key[:3], revision.membership_revision),
    ).fetchone()["sequence"]
    receipt = finalization_receipt(
        finalization=finalization,
        publication_sequence=sequence,
        membership_content_hash=revision.content_hash,
        universe_content_hash=universe.content_hash,
    )
    connection.execute(
        """INSERT INTO dpm_composite_eligibility_finalizations
        (tenant_id,composite_id,definition_version,subject_revision,subject_content_hash,evaluation_revision,approval_content_hash,
        definition_content_hash,membership_revision,membership_content_hash,universe_content_hash,publication_sequence,content_hash,payload_json)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
        (
            *key,
            finalization.subject.content_hash,
            approval.proposal.evaluation_revision,
            approval.content_hash,
            definition.content_hash,
            revision.membership_revision,
            revision.content_hash,
            universe.content_hash,
            sequence,
            receipt.content_hash,
            dump_model_json(receipt),
        ),
    )
    return receipt


def _require_same(left: str, right: str) -> None:
    if left != right:
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
