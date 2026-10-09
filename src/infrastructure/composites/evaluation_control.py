"""Atomic PostgreSQL evaluation custody using the existing canonical publication ledger."""

from typing import Any

from src.core.composite_eligibility.evaluation_control import (
    evaluation_key,
)
from src.core.composite_eligibility.monthly_amendment import (
    MonthlyAmendmentProposal,
    MonthlyApproval,
    MonthlyProposal,
    MonthlyReceiptBinding,
    decode_monthly_approval,
    decode_monthly_proposal,
)
from src.core.composite_eligibility.monthly_authority import (
    MAX_MONTHLY_AUTHORITY_RECORDS,
    require_amendment_authority,
)
from src.core.composite_eligibility.publication import build_monthly_publication
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.infrastructure.composites import (
    membership_store,
    policy_control,
    publication,
    universe_store,
    monthly_evidence,
)
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json


def save_proposal(connection: Any, proposal: MonthlyProposal) -> None:
    proposal = decode_monthly_proposal(proposal.model_dump(mode="json"))
    key = evaluation_key(proposal)
    publication.lock_tenant_publication_order(connection=connection, tenant_id=key[0])
    retained = get_proposal(connection, key)
    if retained is not None:
        if retained != proposal:
            raise DpmCompositeConflictError(
                "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT"
            )
        return
    _require_retained_inputs(connection, proposal)
    _require_current_parent(connection, proposal)
    if isinstance(proposal, MonthlyAmendmentProposal):
        _require_amendment(connection, proposal)
    connection.execute(
        """INSERT INTO dpm_composite_monthly_evaluation_proposals
        (tenant_id, composite_id, definition_version, evaluation_revision, month,
        parent_membership_revision, content_hash, payload_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (tenant_id, composite_id, definition_version, evaluation_revision) DO NOTHING""",
        (
            *key,
            proposal.evaluation.month,
            proposal.parent_membership_revision,
            proposal.content_hash,
            dump_model_json(proposal),
        ),
    )
    retained = get_proposal(connection, key)
    if retained is None or retained.content_hash != proposal.content_hash:
        raise DpmCompositeConflictError(
            "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT"
        )


def get_proposal(connection: Any, key: tuple[str, str, str, str]) -> MonthlyProposal | None:
    row = connection.execute(
        """SELECT content_hash, payload_json FROM dpm_composite_monthly_evaluation_proposals
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND evaluation_revision=%s AND subject_revision IS NULL""",
        key,
    ).fetchone()
    if row is None:
        return None
    proposal = decode_monthly_proposal(row["payload_json"])
    if proposal.content_hash != row["content_hash"] or evaluation_key(proposal) != key:
        raise DpmCompositeConflictError(
            "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_INTEGRITY_CONFLICT"
        )
    return proposal


def _require_retained_inputs(connection: Any, proposal: MonthlyProposal) -> None:
    key = evaluation_key(proposal)
    policy = policy_control.get_approval(connection, (*key[:3], proposal.evaluation.month))
    if policy is None or policy.content_hash != proposal.policy_approval.content_hash:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVED_POLICY_MISMATCH")
    universe = connection.execute(
        """SELECT content_hash, payload_json FROM dpm_composite_universe_attestations
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s
        AND membership_revision=%s AND attestation_version=%s""",
        (*key[:3], proposal.parent_membership_revision, proposal.universe.attestation_version),
    ).fetchone()
    if universe is None or universe["content_hash"] != proposal.universe.content_hash:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_RETAINED_UNIVERSE_MISMATCH")

    actual = load_model_json(DpmCompositeUniverseAttestation, universe["payload_json"])
    if actual != proposal.universe:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_RETAINED_UNIVERSE_MISMATCH")


def _require_current_parent(connection: Any, proposal: MonthlyProposal) -> None:
    key = evaluation_key(proposal)
    current = connection.execute(
        """SELECT sequence, membership_revision, membership_content_hash FROM dpm_composite_membership_publications
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s ORDER BY sequence DESC LIMIT 1""",
        key[:3],
    ).fetchone()
    if current is None or (current["membership_revision"], current["membership_content_hash"]) != (
        proposal.parent_membership_revision,
        proposal.parent_membership_content_hash,
    ):
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP")
    if isinstance(proposal, MonthlyAmendmentProposal) and current["sequence"] != (
        proposal.amendment.expected_current_publication_sequence
    ):
        raise DpmCompositeConflictError("COMPOSITE_MONTHLY_AMENDMENT_STALE_PROJECTION")
    if isinstance(proposal, MonthlyAmendmentProposal):
        parent = _load_revision(connection, (*key[:3], proposal.parent_membership_revision))
        if parent is None:
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP")
        proposal.require_parent_clock(parent.decided_at)


def save_approval(connection: Any, approval: MonthlyApproval) -> None:
    approval = decode_monthly_approval(approval.model_dump(mode="json"))
    proposal = approval.proposal
    key = evaluation_key(proposal)
    publication.lock_tenant_publication_order(connection=connection, tenant_id=key[0])
    retained_approval = get_approval(connection, key)
    if retained_approval is not None:
        if retained_approval != approval:
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT")
        return
    if isinstance(proposal, MonthlyAmendmentProposal):
        _require_amendment(connection, proposal)
    elif (
        connection.execute(
            """SELECT 1 FROM dpm_composite_monthly_evaluation_approvals
        WHERE tenant_id=%s AND composite_id=%s AND month=%s LIMIT 1""",
            (*key[:2], proposal.evaluation.month),
        ).fetchone()
        is not None
    ):
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT")
    retained = get_proposal(connection, key)
    if retained is None or retained.content_hash != proposal.content_hash:
        raise DpmCompositeConflictError(
            "COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_PROPOSAL_MISMATCH"
        )
    _require_retained_inputs(connection, proposal)
    _require_current_parent(connection, proposal)
    parent = _load_revision(connection, (*key[:3], proposal.parent_membership_revision))
    if parent is None:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP")
    expected_approval, revision, universe = build_monthly_publication(
        proposal,
        parent,
        approved_by=approval.approved_by,
        approved_at=approval.approved_at,
    )
    if expected_approval != approval:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH")
    _require_new_target(connection, (*key[:3], revision.membership_revision))
    membership_store.store_membership_revision(connection=connection, revision=revision)
    universe_store.store_universe_attestation(connection=connection, attestation=universe)
    connection.execute(
        """INSERT INTO dpm_composite_monthly_evaluation_approvals
        (tenant_id, composite_id, definition_version, month, evaluation_revision,
        membership_revision, content_hash, payload_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)""",
        (
            *key[:3],
            proposal.evaluation.month,
            key[3],
            revision.membership_revision,
            approval.content_hash,
            dump_model_json(approval),
        ),
    )


def _require_new_target(connection: Any, key: tuple[str, str, str, str]) -> None:
    if _load_revision(connection, key) is not None:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_TARGET_REVISION_EXISTS")


def _load_revision(
    connection: Any, key: tuple[str, str, str, str]
) -> DpmCompositeMembershipRevision | None:
    row = connection.execute(
        """SELECT payload_json FROM dpm_composite_membership_revisions WHERE tenant_id=%s
        AND composite_id=%s AND definition_version=%s AND membership_revision=%s""",
        key,
    ).fetchone()
    return (
        load_model_json(DpmCompositeMembershipRevision, row["payload_json"])
        if row is not None
        else None
    )


def get_approval(connection: Any, key: tuple[str, str, str, str]) -> MonthlyApproval | None:
    row = connection.execute(
        """SELECT content_hash, payload_json FROM dpm_composite_monthly_evaluation_approvals
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND evaluation_revision=%s AND subject_revision IS NULL""",
        key,
    ).fetchone()
    if row is None:
        return None
    approval = decode_monthly_approval(row["payload_json"])
    if approval.content_hash != row["content_hash"] or evaluation_key(approval.proposal) != key:
        raise DpmCompositeConflictError(
            "COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_INTEGRITY_CONFLICT"
        )
    revision = _load_revision(connection, (*key[:3], approval.proposal.target_membership_revision))
    if revision is None or revision.content_hash != approval.membership_content_hash:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH")
    publication.assert_membership_published(connection=connection, revision=revision)
    universe = connection.execute(
        """SELECT content_hash, payload_json FROM dpm_composite_universe_attestations
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND membership_revision=%s AND attestation_version=%s""",
        (*key[:3], revision.membership_revision, approval.proposal.evaluation_revision),
    ).fetchone()

    if universe is None:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH")
    actual = load_model_json(DpmCompositeUniverseAttestation, universe["payload_json"])
    if (
        actual.content_hash != approval.published_universe_content_hash
        or actual.content_hash != universe["content_hash"]
    ):
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH")
    return approval


def _require_amendment(connection: Any, proposal: MonthlyAmendmentProposal) -> None:
    key = evaluation_key(proposal)
    rows = connection.execute(
        """SELECT evaluation_revision, custody_mode FROM dpm_composite_monthly_evaluation_approvals
        WHERE tenant_id=%s AND composite_id=%s AND month=%s
        ORDER BY evaluation_revision LIMIT %s""",
        (*key[:2], proposal.evaluation.month, MAX_MONTHLY_AUTHORITY_RECORDS + 1),
    ).fetchall()
    if any(row["custody_mode"] != "LEGACY" for row in rows):
        raise DpmCompositeConflictError("COMPOSITE_MONTHLY_AMENDMENT_STAGED_ROOT_UNSUPPORTED")
    approvals = [get_approval(connection, (*key[:3], row["evaluation_revision"])) for row in rows]
    if any(item is None for item in approvals):
        raise DpmCompositeConflictError("COMPOSITE_MONTHLY_AUTHORITY_SCOPE_MISMATCH")
    binding = proposal.amendment.predecessor_approval_binding
    receipt = monthly_evidence.resolve(connection, (*key[:3], binding.revision), binding.digest)
    if receipt is None:
        raise DpmCompositeConflictError("COMPOSITE_MONTHLY_AMENDMENT_PREDECESSOR_RECEIPT_MISMATCH")
    try:
        require_amendment_authority(
            proposal,
            [item for item in approvals if item is not None],
            MonthlyReceiptBinding(
                product_version=receipt.product_version,
                revision=binding.revision,
                digest=receipt.content_hash,
            ),
        )
    except ValueError as error:
        raise DpmCompositeConflictError(str(error)) from error
    if (
        connection.execute(
            """SELECT 1 FROM dpm_composite_monthly_evaluation_approvals
        WHERE tenant_id=%s AND composite_id=%s AND month>%s LIMIT 1""",
            (*key[:2], proposal.evaluation.month),
        ).fetchone()
        is not None
    ):
        raise DpmCompositeConflictError("COMPOSITE_MONTHLY_AMENDMENT_DEPENDENT_MONTH_UNSUPPORTED")
