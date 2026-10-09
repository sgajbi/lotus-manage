"""Staging shares the adapter's existing four control collections and publication lock."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from src.core.composite_definition_versions import CompositeDefinition
from src.core.composite_eligibility.staged_controls import (
    STAGED_CONTROL_ADAPTER,
    StagedControl,
    control_subject,
    control_revision,
)
from src.core.composite_eligibility.staged_custody import predecessor, require_control_custody
from src.core.composite_eligibility.staged_ports import SubjectKey, ControlKind
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalizationRecord,
    decode_subject_finalization,
    finalization_receipt,
    SubjectFinalizationProof,
    initial_projection,
)
from src.core.composite_eligibility.staged_subject import EligibilitySubject, subject_key
from src.core.composite_publication import publication_from_revision
from src.core.composite_publication import DpmCompositeMembershipPublication
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_repository import DpmCompositeConflictError


class StagedMemoryCustody:
    """Caller owns the repository lock; collections are borrowed, never duplicated."""

    def __init__(
        self,
        *,
        definitions: dict[tuple[str, str, str], CompositeDefinition],
        policies: Any,
        policy_approvals: Any,
        evaluations: Any,
        evaluation_approvals: Any,
    ) -> None:
        self.subjects: dict[SubjectKey, EligibilitySubject] = {}
        self.receipts: dict[SubjectKey, SubjectFinalizationProof] = {}
        self.definitions = definitions
        self.controls = {
            "CompositeSubjectPolicyProposal": policies,
            "CompositeSubjectPolicyApproval": policy_approvals,
            "CompositeSubjectEvaluationProposal": evaluations,
            "CompositeSubjectEvaluationApproval": evaluation_approvals,
        }

    def save_subject(self, subject: EligibilitySubject) -> None:
        subject = EligibilitySubject.model_validate(subject.model_dump(mode="json"))
        key = subject_key(subject)
        existing = self.subjects.get(key)
        if existing is not None:
            _require_same(existing.content_hash, subject.content_hash)
            return
        if key[:3] in self.definitions or any(other[:3] == key[:3] for other in self.subjects):
            raise DpmCompositeConflictError("COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT")
        self.subjects[key] = deepcopy(subject)

    def get_subject(self, key: SubjectKey) -> EligibilitySubject | None:
        result = self.subjects.get(key)
        return (
            EligibilitySubject.model_validate(result.model_dump(mode="json"))
            if result is not None
            else None
        )

    def reserved(self, definition_key: tuple[str, str, str]) -> bool:
        return any(key[:3] == definition_key for key in self.subjects)

    def get_control(
        self, key: SubjectKey, kind: ControlKind, revision: str
    ) -> StagedControl | None:
        subject = self.get_subject(key)
        if subject is None:
            return None
        result = self.controls[kind].get(_control_key(key, subject.month, kind, revision))
        if result is None or result.product_name != kind:
            return None
        result = STAGED_CONTROL_ADAPTER.validate_python(result.model_dump(mode="json"))
        if subject_key(control_subject(result)) != key or control_revision(result) != revision:
            return None
        return result

    def save_control(self, control: StagedControl) -> None:
        control = STAGED_CONTROL_ADAPTER.validate_python(control.model_dump(mode="json"))
        subject = control_subject(control)
        key = subject_key(subject)
        actual = self.get_subject(key)
        if actual is None:
            raise ValueError("COMPOSITE_SUBJECT_NOT_FOUND")
        previous = predecessor(control)
        retained = self.get_control(key, previous[0], previous[1]) if previous else None
        require_control_custody(control, actual, retained)
        slot = _control_key(key, subject.month, control.product_name, control_revision(control))
        collection = self.controls[control.product_name]
        existing = collection.get(slot)
        if existing is not None:
            _require_same(existing.content_hash, control.content_hash)
            return
        if key in self.receipts:
            raise DpmCompositeConflictError("COMPOSITE_SUBJECT_ALREADY_FINALIZED_CONFLICT")
        collection[slot] = deepcopy(control)

    def finalize(
        self,
        finalization: SubjectFinalizationRecord,
        *,
        memberships: dict[tuple[str, str, str, str], DpmCompositeMembershipRevision],
        universes: dict[tuple[str, str, str, str, str], DpmCompositeUniverseAttestation],
        publications: dict[int, DpmCompositeMembershipPublication],
        last_sequence: int,
    ) -> SubjectFinalizationProof:
        finalization = decode_subject_finalization(finalization.model_dump(mode="json"))
        key = subject_key(finalization.subject)
        retained = self.receipts.get(key)
        if retained is not None:
            _require_same(retained.finalization.content_hash, finalization.content_hash)
            return deepcopy(retained)
        if self.get_subject(key) != finalization.subject:
            raise DpmCompositeConflictError("COMPOSITE_SUBJECT_RETAINED_SUBJECT_MISMATCH")
        approval = finalization.evaluation_approval
        actual = self.get_control(key, approval.product_name, approval.proposal.evaluation_revision)
        if actual != approval:
            raise DpmCompositeConflictError("COMPOSITE_SUBJECT_RETAINED_CONTROL_MISMATCH")
        if key[:3] in self.definitions:
            raise DpmCompositeConflictError("COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT")
        revision, universe = initial_projection(
            approval.proposal, approval.claims_digest, approval.approved_by, approval.approved_at
        )
        member_key = (*key[:3], revision.membership_revision)
        universe_key = (*member_key, universe.attestation_version)
        if member_key in memberships or universe_key in universes:
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_TARGET_REVISION_EXISTS")
        publication = publication_from_revision(
            revision=revision, sequence=last_sequence + 1, published_at=datetime.now(timezone.utc)
        )
        receipt = finalization_receipt(
            finalization=finalization,
            publication_sequence=publication.sequence,
            membership_content_hash=revision.content_hash,
            universe_content_hash=universe.content_hash,
        )
        # Validate/copy every object before the first mutation; all writes are under one owning lock.
        definition, revision, universe, publication, receipt = deepcopy(
            (finalization.definition, revision, universe, publication, receipt)
        )
        self.definitions[key[:3]] = definition
        memberships[member_key] = revision
        universes[universe_key] = universe
        publications[publication.sequence] = publication
        self.receipts[key] = receipt
        return deepcopy(receipt)


def _control_key(key: SubjectKey, month: str, kind: ControlKind, revision: str) -> tuple[str, ...]:
    if kind == "CompositeSubjectPolicyProposal":
        return (*key[:3], month, revision)
    if kind in {"CompositeSubjectPolicyApproval", "CompositeSubjectEvaluationApproval"}:
        return (*key[:2], month)
    return (*key[:3], revision)


def _require_same(left: str, right: str) -> None:
    if left != right:
        raise DpmCompositeConflictError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
