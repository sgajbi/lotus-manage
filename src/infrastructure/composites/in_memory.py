"""Thread-safe development and test adapter for composite eligibility evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import TypeVar

from src.core.composite_corrections import require_correction_window
from src.core.composite_membership import (
    DpmCompositeMembershipRevision,
)
from src.core.composite_definition_versions import (
    CompositeDefinition,
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
    publication_from_revision,
)
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_eligibility.evaluation_control import (
    MonthlyEvaluationApproval,
    MonthlyEvaluationProposal,
    evaluation_key as _evaluation_key,
)
from src.core.composite_eligibility.monthly_amendment import (
    MonthlyAmendmentApproval,
    MonthlyAmendmentProposal,
    MonthlyApproval,
    MonthlyProposal,
    MonthlyReceiptBinding,
    decode_monthly_approval,
    decode_monthly_proposal,
)
from src.core.composite_eligibility.monthly_authority import require_amendment_authority
from src.core.composite_eligibility.publication import build_monthly_publication
from src.core.composite_eligibility.staged_ports import SubjectKey, ControlKind
from src.core.composite_eligibility.staged_controls import StagedControl
from src.core.composite_eligibility.staged_subject import EligibilitySubject
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalization,
    SubjectFinalizationReceipt,
)
from src.infrastructure.composites.staged_memory import StagedMemoryCustody
from src.core.composite_eligibility.staged_custody import require_finalized_custody
from src.core.composite_eligibility.monthly_evidence import (
    MonthlyPublicationReceipt,
    published_monthly_receipt,
    require_monthly_receipt_lineage,
)


KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


class InMemoryDpmCompositeRepository(DpmCompositeRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._definitions: dict[tuple[str, str, str], CompositeDefinition] = {}
        self._monthly_proposals: dict[tuple[str, str, str, str, str], MonthlyPolicyProposal] = {}
        self._monthly_approvals: dict[tuple[str, str, str], MonthlyPolicyApproval] = {}
        self._monthly_evaluations: dict[tuple[str, str, str, str], MonthlyProposal] = {}
        self._monthly_evaluation_approvals: dict[tuple[str, ...], MonthlyApproval] = {}
        self._membership_revisions: dict[
            tuple[str, str, str, str], DpmCompositeMembershipRevision
        ] = {}
        self._publications: dict[int, DpmCompositeMembershipPublication] = {}
        self._receipts: dict[tuple[str, int, str], DpmCompositePublicationReceipt] = {}
        self._universe_attestations: dict[
            tuple[str, str, str, str, str], DpmCompositeUniverseAttestation
        ] = {}
        self._last_sequence = 0
        self._staged = StagedMemoryCustody(
            definitions=self._definitions,
            policies=self._monthly_proposals,
            policy_approvals=self._monthly_approvals,
            evaluations=self._monthly_evaluations,
            evaluation_approvals=self._monthly_evaluation_approvals,
        )

    def save_eligibility_subject(self, *, subject: EligibilitySubject) -> None:
        with self._lock:
            self._staged.save_subject(subject)

    def get_eligibility_subject(self, *, key: SubjectKey) -> EligibilitySubject | None:
        with self._lock:
            return self._staged.get_subject(key)

    def save_subject_control(self, *, control: StagedControl) -> None:
        with self._lock:
            self._staged.save_control(control)

    def get_subject_control(
        self, *, key: SubjectKey, kind: ControlKind, revision: str
    ) -> StagedControl | None:
        with self._lock:
            return self._staged.get_control(key, kind, revision)

    def finalize_eligibility_subject(
        self, *, finalization: SubjectFinalization
    ) -> SubjectFinalizationReceipt:
        with self._lock:
            receipt = self._staged.finalize(
                finalization,
                memberships=self._membership_revisions,
                universes=self._universe_attestations,
                publications=self._publications,
                last_sequence=self._last_sequence,
            )
            self._last_sequence = max(self._last_sequence, receipt.publication_sequence)
            return receipt

    def get_eligibility_finalization(self, *, key: SubjectKey) -> SubjectFinalizationReceipt | None:
        with self._lock:
            return self._finalization_receipt(key)

    def _finalization_receipt(self, key: SubjectKey) -> SubjectFinalizationReceipt | None:
        receipt = self._staged.receipts.get(key)
        if receipt is None:
            return None
        receipt = SubjectFinalizationReceipt.model_validate(receipt.model_dump(mode="json"))
        approval = receipt.finalization.evaluation_approval
        target = approval.proposal.target_membership_revision
        require_finalized_custody(
            receipt,
            subject=self._staged.get_subject(key),
            approval=self._staged.get_control(
                key, approval.product_name, approval.proposal.evaluation_revision
            ),
            definition=self._definitions.get(key[:3]),
            membership=self._membership_revisions.get((*key[:3], target)),
            universe=self._universe_attestations.get(
                (*key[:3], target, approval.proposal.evaluation_revision)
            ),
            publication=self._publications.get(receipt.publication_sequence),
        )
        return receipt

    def resolve_eligibility_evidence(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
        approval_content_hash: str,
    ) -> SubjectFinalizationReceipt | None:
        with self._lock:
            keys = [
                key
                for key, receipt in self._staged.receipts.items()
                if key[:3] == (tenant_id, composite_id, definition_version)
                and receipt.finalization.evaluation_approval.proposal.evaluation_revision
                == evaluation_revision
            ]
            if not keys:
                return None
            receipt = self._finalization_receipt(keys[0])
            if (
                receipt is None
                or receipt.finalization.evaluation_approval.content_hash != approval_content_hash
            ):
                raise DpmCompositeConflictError("COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH")
            return receipt

    def save_monthly_evaluation_proposal(self, *, proposal: MonthlyProposal) -> None:
        proposal = decode_monthly_proposal(proposal.model_dump(mode="json"))
        key = _evaluation_key(proposal)
        with self._lock:
            retained = self._monthly_evaluations.get(key)
            if retained is not None:
                if retained != proposal:
                    raise DpmCompositeConflictError(
                        "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT"
                    )
                return
            self._require_monthly_inputs(proposal)
            self._require_current_monthly_parent(proposal)
            if isinstance(proposal, MonthlyAmendmentProposal):
                self._require_amendment(proposal)
            _save_immutable(
                values=self._monthly_evaluations,
                key=key,
                value=proposal,
                conflict_code="COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT",
            )

    def get_monthly_evaluation_proposal(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
    ) -> MonthlyProposal | None:
        with self._lock:
            result = self._monthly_evaluations.get(
                (tenant_id, composite_id, definition_version, evaluation_revision)
            )
            if result is not None and not isinstance(
                result, (MonthlyEvaluationProposal, MonthlyAmendmentProposal)
            ):
                return None
            return (
                decode_monthly_proposal(result.model_dump(mode="json"))
                if result is not None
                else None
            )

    def save_monthly_evaluation_approval(self, *, approval: MonthlyApproval) -> None:
        approval = decode_monthly_approval(approval.model_dump(mode="json"))
        proposal = approval.proposal
        key = _evaluation_key(proposal)
        approval_key = (
            key
            if isinstance(proposal, MonthlyAmendmentProposal)
            else (*key[:2], proposal.evaluation.month)
        )
        with self._lock:
            existing = self._monthly_evaluation_approvals.get(approval_key)
            if existing is not None:
                if not isinstance(existing, (MonthlyEvaluationApproval, MonthlyAmendmentApproval)):
                    raise DpmCompositeConflictError(
                        "COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT"
                    )
                if existing != approval:
                    raise DpmCompositeConflictError(
                        "COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT"
                    )
                self._assert_monthly_publication(existing)
                return
            if isinstance(proposal, MonthlyAmendmentProposal):
                self._require_amendment(proposal)
            retained = self._monthly_evaluations.get(key)
            if retained is None or retained.content_hash != proposal.content_hash:
                raise DpmCompositeConflictError(
                    "COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_PROPOSAL_MISMATCH"
                )
            self._require_monthly_inputs(proposal)
            self._require_current_monthly_parent(proposal)
            parent = self._membership_revisions[(*key[:3], proposal.parent_membership_revision)]
            expected, revision, universe = build_monthly_publication(
                proposal,
                parent,
                approved_by=approval.approved_by,
                approved_at=approval.approved_at,
            )
            if expected != approval:
                raise DpmCompositeConflictError(
                    "COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH"
                )
            revision_key = (*key[:3], revision.membership_revision)
            universe_key = (*revision_key, universe.attestation_version)
            if (
                revision_key in self._membership_revisions
                or universe_key in self._universe_attestations
            ):
                raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_TARGET_REVISION_EXISTS")
            published = publication_from_revision(
                revision=revision,
                sequence=self._last_sequence + 1,
                published_at=datetime.now(timezone.utc),
            )
            revision, universe, approval = deepcopy((revision, universe, approval))
            self._membership_revisions[revision_key] = revision
            self._universe_attestations[universe_key] = universe
            self._monthly_evaluation_approvals[approval_key] = approval
            self._publications[published.sequence] = published
            self._last_sequence = published.sequence

    def get_monthly_evaluation_approval(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
    ) -> MonthlyApproval | None:
        with self._lock:
            result = next(
                (
                    item
                    for item in self._monthly_evaluation_approvals.values()
                    if isinstance(item, (MonthlyEvaluationApproval, MonthlyAmendmentApproval))
                    and _evaluation_key(item.proposal)
                    == (tenant_id, composite_id, definition_version, evaluation_revision)
                ),
                None,
            )
            if result is None:
                return None
            result = decode_monthly_approval(result.model_dump(mode="json"))
            self._assert_monthly_publication(result)
            return result

    def _require_monthly_inputs(self, proposal: MonthlyProposal) -> None:
        key = _evaluation_key(proposal)
        policy = self._monthly_approvals.get((*key[:2], proposal.evaluation.month))
        if policy is None or policy.content_hash != proposal.policy_approval.content_hash:
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVED_POLICY_MISMATCH")
        universe = self._universe_attestations.get(
            (*key[:3], proposal.parent_membership_revision, proposal.universe.attestation_version)
        )
        if universe != proposal.universe:
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_RETAINED_UNIVERSE_MISMATCH")

    def resolve_monthly_eligibility_evidence(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
        approval_content_hash: str,
    ) -> MonthlyPublicationReceipt | None:
        key = (tenant_id, composite_id, definition_version, evaluation_revision)
        with self._lock:
            return self._validated_monthly_receipt(key, approval_content_hash)

    def _validated_monthly_receipt(
        self, key: tuple[str, str, str, str], approval_content_hash: str
    ) -> MonthlyPublicationReceipt | None:
        receipt = self._monthly_receipt(key, approval_content_hash)
        if receipt is not None:
            try:
                require_monthly_receipt_lineage(
                    receipt,
                    lambda binding: self._monthly_receipt(
                        (*key[:3], binding.revision), binding.digest
                    ),
                )
            except ValueError as error:
                raise DpmCompositeConflictError(
                    "COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT"
                ) from error
        return receipt

    def _monthly_receipt(
        self, key: tuple[str, str, str, str], approval_content_hash: str
    ) -> MonthlyPublicationReceipt | None:
        """Caller owns the lock; no getter may acquire it a second time."""
        approval = next(
            (
                item
                for item in self._monthly_evaluation_approvals.values()
                if isinstance(item, (MonthlyEvaluationApproval, MonthlyAmendmentApproval))
                and _evaluation_key(item.proposal) == key
            ),
            None,
        )
        if approval is None or approval.proposal.publication_evidence_version is None:
            return None
        if approval.content_hash != approval_content_hash:
            raise DpmCompositeConflictError("COMPOSITE_MONTHLY_EVIDENCE_BINDING_MISMATCH")
        proposal = self._monthly_evaluations.get(key)
        definition = self._definitions.get(key[:3])
        policy = self._monthly_approvals.get((*key[:2], approval.proposal.evaluation.month))
        policy_proposal = self._monthly_proposals.get(
            (
                *key[:3],
                approval.proposal.evaluation.month,
                approval.proposal.policy_approval.proposal.proposal_revision,
            )
        )
        parent = self._membership_revisions.get(
            (*key[:3], approval.proposal.parent_membership_revision)
        )
        target = approval.proposal.target_membership_revision
        member = self._membership_revisions.get((*key[:3], target))
        universe = self._universe_attestations.get((*key[:3], target, key[3]))
        publication = self._publication_for_membership((*key[:3], target))
        if (
            proposal is None
            or definition is None
            or policy is None
            or policy_proposal is None
            or parent is None
            or member is None
            or universe is None
            or publication is None
        ):
            raise DpmCompositeConflictError("COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT")
        self._require_monthly_inputs(proposal)
        parent_publication = self._publication_for_membership(
            (*key[:3], proposal.parent_membership_revision)
        )
        receipt = published_monthly_receipt(
            definition=definition,
            approval=approval,
            retained_policy=policy,
            retained_policy_proposal=policy_proposal,
            retained_proposal=proposal,
            parent=parent,
            membership=member,
            universe=universe,
            publication=publication,
            parent_publication=parent_publication,
        )
        return receipt

    def _require_amendment(self, proposal: MonthlyAmendmentProposal) -> None:
        key = _evaluation_key(proposal)
        approvals = [
            item
            for item in self._monthly_evaluation_approvals.values()
            if isinstance(item, (MonthlyEvaluationApproval, MonthlyAmendmentApproval))
            and _evaluation_key(item.proposal)[:2] == key[:2]
            and item.proposal.evaluation.month == proposal.evaluation.month
        ]
        if not approvals and (*key[:2], proposal.evaluation.month) in (
            self._monthly_evaluation_approvals
        ):
            raise DpmCompositeConflictError("COMPOSITE_MONTHLY_AMENDMENT_STAGED_ROOT_UNSUPPORTED")
        binding = proposal.amendment.predecessor_approval_binding
        receipt = self._validated_monthly_receipt((*key[:3], binding.revision), binding.digest)
        if receipt is None:
            raise DpmCompositeConflictError(
                "COMPOSITE_MONTHLY_AMENDMENT_PREDECESSOR_RECEIPT_MISMATCH"
            )
        try:
            require_amendment_authority(
                proposal,
                approvals,
                MonthlyReceiptBinding(
                    product_version=receipt.product_version,
                    revision=binding.revision,
                    digest=receipt.content_hash,
                ),
            )
        except ValueError as error:
            raise DpmCompositeConflictError(str(error)) from error
        if any(
            len(stored_key) == 3
            and stored_key[:2] == key[:2]
            and stored_key[2] > proposal.evaluation.month
            for stored_key in self._monthly_evaluation_approvals
        ):
            raise DpmCompositeConflictError(
                "COMPOSITE_MONTHLY_AMENDMENT_DEPENDENT_MONTH_UNSUPPORTED"
            )

    def _require_current_monthly_parent(self, proposal: MonthlyProposal) -> None:
        key = _evaluation_key(proposal)
        current = next(
            (
                item
                for item in reversed(self._publications.values())
                if (item.tenant_id, item.composite_id, item.definition_version) == key[:3]
            ),
            None,
        )
        if current is None or (current.membership_revision, current.membership_content_hash) != (
            proposal.parent_membership_revision,
            proposal.parent_membership_content_hash,
        ):
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP")
        self._assert_publication_integrity(current)
        if isinstance(proposal, MonthlyAmendmentProposal) and current.sequence != (
            proposal.amendment.expected_current_publication_sequence
        ):
            raise DpmCompositeConflictError("COMPOSITE_MONTHLY_AMENDMENT_STALE_PROJECTION")
        if isinstance(proposal, MonthlyAmendmentProposal):
            proposal.require_parent_clock(current.decided_at)

    def _publication_for_membership(
        self, key: tuple[str, str, str, str]
    ) -> DpmCompositeMembershipPublication | None:
        return next(
            (
                item
                for item in self._publications.values()
                if (
                    item.tenant_id,
                    item.composite_id,
                    item.definition_version,
                    item.membership_revision,
                )
                == key
            ),
            None,
        )

    def _assert_monthly_publication(self, approval: MonthlyApproval) -> None:
        key = _evaluation_key(approval.proposal)
        target = approval.proposal.target_membership_revision
        revision = self._membership_revisions.get((*key[:3], target))
        universe = self._universe_attestations.get((*key[:3], target, key[3]))
        publication = self._publication_for_membership((*key[:3], target))
        if revision is None or revision.content_hash != approval.membership_content_hash:
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH")
        if (
            universe is None
            or universe.content_hash != approval.published_universe_content_hash
            or publication is None
        ):
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH")
        self._assert_publication_integrity(publication)

    def save_monthly_policy_proposal(self, *, proposal: MonthlyPolicyProposal) -> None:
        proposal = MonthlyPolicyProposal.model_validate(proposal.model_dump(mode="json"))
        scope = proposal.policy.scope
        key = (
            scope.tenant_id,
            scope.composite_id,
            scope.definition_version,
            proposal.policy.month,
            proposal.proposal_revision,
        )
        with self._lock:
            if key[:3] not in self._definitions:
                raise ValueError("COMPOSITE_DEFINITION_NOT_FOUND")
            definition = self._definitions[key[:3]]
            if (definition.eligibility_policy_version, definition.strategy_code) != (
                proposal.eligibility_policy_version,
                proposal.policy.scope.strategy_code,
            ):
                raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_DEFINITION_POLICY_MISMATCH")
            _save_immutable(
                values=self._monthly_proposals,
                key=key,
                value=proposal,
                conflict_code="COMPOSITE_ELIGIBILITY_PROPOSAL_IMMUTABLE_CONFLICT",
            )

    def get_monthly_policy_proposal(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
        proposal_revision: str,
    ) -> MonthlyPolicyProposal | None:
        with self._lock:
            result = self._monthly_proposals.get(
                (tenant_id, composite_id, definition_version, month, proposal_revision)
            )
            if result is not None and not isinstance(result, MonthlyPolicyProposal):
                return None
            return deepcopy(result) if result is not None else None

    def save_monthly_policy_approval(self, *, approval: MonthlyPolicyApproval) -> None:
        approval = MonthlyPolicyApproval.model_validate(approval.model_dump(mode="json"))
        proposal = approval.proposal
        scope = proposal.policy.scope
        proposal_key = (
            scope.tenant_id,
            scope.composite_id,
            scope.definition_version,
            proposal.policy.month,
            proposal.proposal_revision,
        )
        with self._lock:
            retained = self._monthly_proposals.get(proposal_key)
            if retained is None or retained.content_hash != proposal.content_hash:
                raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVAL_PROPOSAL_MISMATCH")
            _save_immutable(
                values=self._monthly_approvals,
                key=(scope.tenant_id, scope.composite_id, proposal.policy.month),
                value=approval,
                conflict_code="COMPOSITE_ELIGIBILITY_ACTIVE_POLICY_CONFLICT",
            )

    def get_monthly_policy_approval(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
    ) -> MonthlyPolicyApproval | None:
        with self._lock:
            result = self._monthly_approvals.get((tenant_id, composite_id, month))
            if (
                result is None
                or not isinstance(result, MonthlyPolicyApproval)
                or result.proposal.policy.scope.definition_version != definition_version
            ):
                return None
            return deepcopy(result)

    def save_definition(self, *, definition: CompositeDefinition) -> None:
        definition = validated_definition_snapshot(definition)
        key = (definition.tenant_id, definition.composite_id, definition.definition_version)
        with self._lock:
            if self._staged.reserved(key):
                if self._definitions.get(key) != definition:
                    raise DpmCompositeConflictError(
                        "COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT"
                    )
                return
            _save_immutable(
                values=self._definitions,
                key=key,
                value=definition,
                conflict_code="COMPOSITE_DEFINITION_IMMUTABLE_CONFLICT",
            )

    def get_definition(
        self, *, tenant_id: str, composite_id: str, definition_version: str
    ) -> CompositeDefinition | None:
        with self._lock:
            definition = self._definitions.get((tenant_id, composite_id, definition_version))
            return deepcopy(definition) if definition is not None else None

    def list_definitions(
        self, *, tenant_id: str, limit: int, offset: int
    ) -> DpmCompositeResultPage[CompositeDefinition]:
        with self._lock:
            definitions = sorted(
                (
                    definition
                    for (stored_tenant_id, _, _), definition in self._definitions.items()
                    if stored_tenant_id == tenant_id
                ),
                key=lambda definition: (
                    definition.inception_date,
                    definition.composite_id,
                    definition.definition_version,
                ),
                reverse=True,
            )
            return DpmCompositeResultPage(
                items=deepcopy(definitions[offset : offset + limit]), count=len(definitions)
            )

    def save_membership_revision(self, *, revision: DpmCompositeMembershipRevision) -> None:
        definition_key = (revision.tenant_id, revision.composite_id, revision.definition_version)
        revision_key = (*definition_key, revision.membership_revision)
        with self._lock:
            if definition_key not in self._definitions:
                raise DpmCompositeConflictError("COMPOSITE_MEMBERSHIP_DEFINITION_NOT_FOUND")
            if revision_key in self._membership_revisions:
                _save_immutable(
                    values=self._membership_revisions,
                    key=revision_key,
                    value=revision,
                    conflict_code="COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT",
                )
                return
            if (
                revision.supersedes_membership_revision is not None
                and (*definition_key, revision.supersedes_membership_revision)
                not in self._membership_revisions
            ):
                raise DpmCompositeConflictError(
                    "COMPOSITE_MEMBERSHIP_SUPERSEDED_REVISION_NOT_FOUND"
                )
            if revision.supersedes_membership_revision is not None:
                parent = self._membership_revisions[
                    (*definition_key, revision.supersedes_membership_revision)
                ]
                try:
                    require_correction_window(parent=parent, revision=revision)
                except ValueError as exc:
                    raise DpmCompositeConflictError(str(exc)) from exc
            _save_immutable(
                values=self._membership_revisions,
                key=revision_key,
                value=revision,
                conflict_code="COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT",
            )
            self._last_sequence += 1
            self._publications[self._last_sequence] = publication_from_revision(
                revision=revision,
                sequence=self._last_sequence,
                published_at=datetime.now(timezone.utc),
            )

    def get_membership_revision(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
    ) -> DpmCompositeMembershipRevision | None:
        with self._lock:
            revision = self._membership_revisions.get(
                (tenant_id, composite_id, definition_version, membership_revision)
            )
            return deepcopy(revision) if revision is not None else None

    def list_membership_revisions(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        limit: int,
        offset: int,
    ) -> DpmCompositeResultPage[DpmCompositeMembershipRevision]:
        with self._lock:
            revisions = sorted(
                (
                    revision
                    for (
                        stored_tenant_id,
                        stored_composite_id,
                        stored_definition_version,
                        _,
                    ), revision in self._membership_revisions.items()
                    if (stored_tenant_id, stored_composite_id, stored_definition_version)
                    == (tenant_id, composite_id, definition_version)
                ),
                key=lambda revision: (revision.decided_at, revision.membership_revision),
                reverse=True,
            )
            return DpmCompositeResultPage(
                items=deepcopy(revisions[offset : offset + limit]), count=len(revisions)
            )

    def get_publication(
        self, *, tenant_id: str, sequence: int
    ) -> DpmCompositeMembershipPublication | None:
        with self._lock:
            publication = self._publications.get(sequence)
            if publication is None or publication.tenant_id != tenant_id:
                return None
            self._assert_publication_integrity(publication)
            return deepcopy(publication)

    def assert_membership_published(self, *, revision: DpmCompositeMembershipRevision) -> None:
        with self._lock:
            publications = (
                publication
                for publication in self._publications.values()
                if (
                    publication.tenant_id,
                    publication.composite_id,
                    publication.definition_version,
                    publication.membership_revision,
                )
                == (
                    revision.tenant_id,
                    revision.composite_id,
                    revision.definition_version,
                    revision.membership_revision,
                )
            )
            publication = next(publications, None)
            if publication is None or publication.membership_content_hash != revision.content_hash:
                raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT")

    def _assert_publication_integrity(self, publication: DpmCompositeMembershipPublication) -> None:
        revision = self._membership_revisions.get(
            (
                publication.tenant_id,
                publication.composite_id,
                publication.definition_version,
                publication.membership_revision,
            )
        )
        if revision is None or publication.membership_content_hash != revision.content_hash:
            raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT")

    def list_publications(
        self, *, tenant_id: str, after_sequence: int, limit: int
    ) -> DpmCompositePublicationPage:
        with self._lock:
            available = [
                publication
                for sequence, publication in sorted(self._publications.items())
                if publication.tenant_id == tenant_id
            ]
            high_watermark = available[-1].sequence if available else 0
            if after_sequence > high_watermark:
                raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_CURSOR_AHEAD")
            next_items = [
                publication for publication in available if publication.sequence > after_sequence
            ]
            items = next_items[:limit]
            for publication in items:
                self._assert_publication_integrity(publication)
            return DpmCompositePublicationPage(
                items=deepcopy(items),
                high_watermark=high_watermark,
                next_sequence=items[-1].sequence if items else after_sequence,
                has_more=len(next_items) > limit,
            )

    def save_receipt(self, *, receipt: DpmCompositePublicationReceipt) -> bool:
        key = (receipt.tenant_id, receipt.publication_sequence, receipt.consumer_id)
        with self._lock:
            publication = self._publications.get(receipt.publication_sequence)
            if publication is None or publication.tenant_id != receipt.tenant_id:
                raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_NOT_FOUND")
            if publication.membership_content_hash != receipt.membership_content_hash:
                raise DpmCompositeConflictError("COMPOSITE_PUBLICATION_HASH_MISMATCH")
            existing = self._receipts.get(key)
            if existing is not None:
                if (
                    existing.disposition != receipt.disposition
                    or existing.reason_code != receipt.reason_code
                    or existing.receipt_evidence_hash != receipt.receipt_evidence_hash
                    or existing.correlation_id != receipt.correlation_id
                ):
                    raise DpmCompositeConflictError("COMPOSITE_RECEIPT_IMMUTABLE_CONFLICT")
                return False
            self._receipts[key] = deepcopy(receipt)
            return True

    def list_receipts(
        self, *, tenant_id: str, publication_sequence: int
    ) -> list[DpmCompositePublicationReceipt]:
        with self._lock:
            return deepcopy(
                sorted(
                    (
                        receipt
                        for (stored_tenant, sequence, _), receipt in self._receipts.items()
                        if stored_tenant == tenant_id and sequence == publication_sequence
                    ),
                    key=lambda receipt: receipt.consumer_id,
                )
            )

    def save_universe_attestation(self, *, attestation: DpmCompositeUniverseAttestation) -> None:
        revision_key = (
            attestation.tenant_id,
            attestation.composite_id,
            attestation.definition_version,
            attestation.membership_revision,
        )
        key = (*revision_key, attestation.attestation_version)
        with self._lock:
            revision = self._membership_revisions.get(revision_key)
            if revision is None:
                raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_MEMBERSHIP_NOT_FOUND")
            if revision.content_hash != attestation.membership_content_hash:
                raise DpmCompositeConflictError("COMPOSITE_UNIVERSE_MEMBERSHIP_HASH_MISMATCH")
            _save_immutable(
                values=self._universe_attestations,
                key=key,
                value=attestation,
                conflict_code="COMPOSITE_UNIVERSE_ATTESTATION_IMMUTABLE_CONFLICT",
            )

    def get_universe_attestation(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        membership_revision: str,
        attestation_version: str,
    ) -> DpmCompositeUniverseAttestation | None:
        with self._lock:
            attestation = self._universe_attestations.get(
                (
                    tenant_id,
                    composite_id,
                    definition_version,
                    membership_revision,
                    attestation_version,
                )
            )
            return deepcopy(attestation) if attestation is not None else None

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
        with self._lock:
            attestations = sorted(
                (
                    attestation
                    for (
                        stored_tenant,
                        stored_composite,
                        stored_definition,
                        stored_revision,
                        _,
                    ), attestation in self._universe_attestations.items()
                    if (
                        stored_tenant,
                        stored_composite,
                        stored_definition,
                        stored_revision,
                    )
                    == (tenant_id, composite_id, definition_version, membership_revision)
                ),
                key=lambda item: (item.attested_at, item.attestation_version),
                reverse=True,
            )
            return DpmCompositeResultPage(
                items=deepcopy(attestations[offset : offset + limit]), count=len(attestations)
            )


def _save_immutable(
    *, values: dict[KeyT, ValueT], key: KeyT, value: ValueT, conflict_code: str
) -> None:
    existing = values.get(key)
    if existing is not None and existing != value:
        raise DpmCompositeConflictError(conflict_code)
    if existing is None:
        values[key] = deepcopy(value)


__all__ = ["InMemoryDpmCompositeRepository"]
