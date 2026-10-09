"""Shared cross-adapter identity and dependency checks for existing control custody."""

from src.core.composite_eligibility.staged_controls import (
    StagedControl,
    SubjectPolicyProposal,
    SubjectPolicyApproval,
    SubjectEvaluationProposal,
    SubjectEvaluationApproval,
    control_subject,
    control_revision,
)
from src.core.composite_eligibility.staged_publication import (
    initial_projection,
    SubjectFinalizationProof,
)
from src.core.composite_eligibility.staged_subject import EligibilitySubject, subject_key
from src.core.composite_eligibility.staged_ports import ControlKind
from src.core.composite_definition_versions import CompositeDefinition
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_publication import DpmCompositeMembershipPublication


def predecessor(control: StagedControl) -> tuple[ControlKind, str, str] | None:
    item: StagedControl
    if isinstance(control, SubjectPolicyProposal):
        return None
    if isinstance(control, SubjectPolicyApproval):
        item = control.proposal
    elif isinstance(control, SubjectEvaluationProposal):
        item = control.policy_approval
    else:
        item = control.proposal
    return item.product_name, control_revision(item), item.content_hash


def require_control_custody(
    control: StagedControl, subject: EligibilitySubject, retained_predecessor: StagedControl | None
) -> None:
    if control_subject(control) != subject:
        raise ValueError("COMPOSITE_SUBJECT_RETAINED_SUBJECT_MISMATCH")
    expected = predecessor(control)
    if expected is not None and (
        retained_predecessor is None
        or (
            retained_predecessor.product_name,
            control_revision(retained_predecessor),
            retained_predecessor.content_hash,
        )
        != expected
        or subject_key(control_subject(retained_predecessor)) != subject_key(subject)
    ):
        raise ValueError("COMPOSITE_SUBJECT_RETAINED_CONTROL_MISMATCH")
    if isinstance(control, SubjectEvaluationApproval):
        revision, universe = initial_projection(
            control.proposal, control.claims_digest, control.approved_by, control.approved_at
        )
        if (revision.content_hash, universe.content_hash) != (
            control.membership_content_hash,
            control.universe_content_hash,
        ):
            raise ValueError("COMPOSITE_SUBJECT_PROJECTION_MISMATCH")


def require_finalized_custody(
    receipt: SubjectFinalizationProof,
    *,
    subject: EligibilitySubject | None,
    approval: StagedControl | None,
    definition: CompositeDefinition | None,
    membership: DpmCompositeMembershipRevision | None,
    universe: DpmCompositeUniverseAttestation | None,
    publication: DpmCompositeMembershipPublication | None,
) -> None:
    finalization = receipt.finalization
    if (
        subject != finalization.subject
        or approval != finalization.evaluation_approval
        or definition != finalization.definition
    ):
        raise ValueError("COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT")
    approval = finalization.evaluation_approval
    expected_member, expected_universe = initial_projection(
        approval.proposal, approval.claims_digest, approval.approved_by, approval.approved_at
    )
    if membership != expected_member or universe != expected_universe or publication is None:
        raise ValueError("COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT")
    subject = finalization.subject
    if (
        publication.tenant_id,
        publication.composite_id,
        publication.definition_version,
        publication.membership_revision,
        publication.membership_content_hash,
        publication.sequence,
    ) != (
        subject.tenant_id,
        subject.composite_id,
        subject.definition_version,
        expected_member.membership_revision,
        expected_member.content_hash,
        receipt.publication_sequence,
    ):
        raise ValueError("COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT")
