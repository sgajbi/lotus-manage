"""Exact published monthly evidence; no financial admission or new approval engine."""

from collections.abc import Callable
from typing import Literal

from pydantic import Field, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import EvidenceBinding, Identity, StrictAuthorityModel
from src.core.composite_definition_versions import CompositeDefinition, decode_composite_definition
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_eligibility.evaluation_control import (
    MonthlyEvaluationApprovalContent,
    MonthlyEvaluationApproval,
)
from src.core.composite_eligibility.monthly_amendment import (
    MonthlyAmendmentApproval,
    MonthlyApproval,
    MonthlyApprovalBinding,
    MonthlyProposal,
    MonthlySourceAmendment,
)
from src.core.composite_eligibility.publication import build_monthly_publication
from src.core.composite_eligibility.monthly_authority import (
    MAX_MONTHLY_AUTHORITY_RECORDS,
    approval_binding,
    selected_monthly_approval,
    require_source_correction,
)
from src.core.composite_eligibility.evaluation_control import evaluation_key
from src.core.composite_membership import (
    DpmCompositeMembershipRevision,
    DpmCompositeDefinition,
    DpmCompositeSourceAuthority,
)
from src.core.composite_publication import DpmCompositeMembershipPublication
from src.core.composite_universe import DpmCompositeUniverseAttestation


class MonthlyEligibilityReceiptContent(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEligibilityPublicationReceipt"] = (
        "CompositeMonthlyEligibilityPublicationReceipt"
    )
    product_version: Literal["v1", "v2"]
    definition: CompositeDefinition
    approval: MonthlyEvaluationApprovalContent
    membership_binding: EvidenceBinding
    universe_binding: EvidenceBinding
    source_cut_id: Identity
    publication_sequence: int = Field(gt=0)
    completeness: Literal["UNVERIFIED"] = "UNVERIFIED"
    content_hash: str = ""

    @model_validator(mode="before")
    @classmethod
    def require_full_strict_definition_wire(cls, wire: object) -> object:
        if isinstance(wire, dict):
            definition = wire.get("definition")
            if isinstance(definition, dict) and definition.get("product_version", "v1") == "v1":
                authority = definition.get("source_authority")
                if set(definition) - set(DpmCompositeDefinition.model_fields) or (
                    isinstance(authority, dict)
                    and set(authority) - set(DpmCompositeSourceAuthority.model_fields)
                ):
                    raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_DEFINITION_WIRE_INVALID")
        return wire

    @model_validator(mode="after")
    def require_exact_bound_content(self) -> "MonthlyEligibilityReceiptContent":
        self.definition = decode_composite_definition(self.definition.model_dump(mode="json"))
        self.approval = type(self.approval).model_validate(self.approval.model_dump(mode="json"))
        proposal = self.approval.proposal
        scope = proposal.policy_approval.proposal.policy.scope
        if (
            proposal.publication_evidence_version != "v1"
            or proposal.source_assembly_evidence is None
        ):
            raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_UNAVAILABLE")
        if (
            self.definition.tenant_id,
            self.definition.composite_id,
            self.definition.definition_version,
            self.definition.eligibility_policy_version,
            self.definition.reporting_currency,
            self.definition.strategy_code,
            self.source_cut_id,
        ) != (
            scope.tenant_id,
            scope.composite_id,
            scope.definition_version,
            proposal.policy_approval.proposal.eligibility_policy_version,
            proposal.observations.reporting_currency,
            scope.strategy_code,
            proposal.universe.source_cut_id,
        ):
            raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_SCOPE_MISMATCH")
        expected_member = EvidenceBinding(
            product_name="CompositeMembership",
            product_version="v1",
            revision=proposal.target_membership_revision,
            digest=self.approval.membership_content_hash,
        )
        expected_universe = EvidenceBinding(
            product_name="CompositeUniverseAttestation",
            product_version="v1",
            revision=proposal.evaluation_revision,
            digest=self.approval.published_universe_content_hash,
        )
        if (self.membership_binding, self.universe_binding) != (expected_member, expected_universe):
            raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_BINDING_MISMATCH")
        # Only the root self-hash is excluded. Nested hashes, including the approval
        # digest, remain in this proof's canonical content.
        expected = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_CONTENT_MISMATCH")
        self.content_hash = expected
        return self


class MonthlyEligibilityPublicationReceipt(MonthlyEligibilityReceiptContent):
    """Frozen ordinary receipt, including embedded definition product v1 or v2."""

    product_version: Literal["v1"] = "v1"
    approval: MonthlyEvaluationApproval


class MonthlyAmendmentPublicationReceipt(MonthlyEligibilityReceiptContent):
    """Exact approved replacement graph with bounded predecessor locators."""

    product_version: Literal["v2"] = "v2"
    approval: MonthlyAmendmentApproval
    lineage: MonthlySourceAmendment

    @model_validator(mode="after")
    def require_approved_lineage(self) -> "MonthlyAmendmentPublicationReceipt":
        if self.lineage != self.approval.proposal.amendment:
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_RECEIPT_LINEAGE_MISMATCH")
        return self


MonthlyPublicationReceipt = (
    MonthlyEligibilityPublicationReceipt | MonthlyAmendmentPublicationReceipt
)


def require_monthly_receipt_lineage(
    receipt: MonthlyPublicationReceipt,
    load: Callable[[MonthlyApprovalBinding], MonthlyPublicationReceipt | None],
) -> None:
    """Validate a bounded retained predecessor path under the caller's read snapshot."""
    approvals: list[MonthlyApproval] = [receipt.approval]
    current = receipt
    while isinstance(current.approval, MonthlyAmendmentApproval):
        if len(approvals) >= MAX_MONTHLY_AUTHORITY_RECORDS:
            raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT")
        lineage = current.approval.proposal.amendment
        binding = lineage.predecessor_approval_binding
        predecessor = load(binding)
        if predecessor is None or (
            predecessor.content_hash != lineage.predecessor_receipt_binding.digest
            or predecessor.product_version != lineage.predecessor_receipt_binding.product_version
            or approval_binding(predecessor.approval) != binding
        ):
            raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT")
        require_source_correction(current.approval.proposal, predecessor.approval)
        approvals.append(predecessor.approval)
        current = predecessor
    selected_monthly_approval(
        approvals,
        scope=evaluation_key(receipt.approval.proposal)[:3],
        month=receipt.approval.proposal.evaluation.month,
    )


def published_monthly_receipt(
    *,
    definition: CompositeDefinition,
    approval: MonthlyApproval,
    retained_policy: MonthlyPolicyApproval,
    retained_policy_proposal: MonthlyPolicyProposal,
    retained_proposal: MonthlyProposal,
    parent: DpmCompositeMembershipRevision,
    membership: DpmCompositeMembershipRevision,
    universe: DpmCompositeUniverseAttestation,
    publication: DpmCompositeMembershipPublication,
    parent_publication: DpmCompositeMembershipPublication | None = None,
) -> MonthlyPublicationReceipt:
    """Call only with custody loaded under one repository read snapshot/lock."""
    if retained_policy.proposal != retained_policy_proposal or (
        approval.proposal != retained_proposal
        or approval.proposal.policy_approval != retained_policy
    ):
        raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT")
    expected_approval, expected_member, expected_universe = build_monthly_publication(
        retained_proposal,
        parent,
        approved_by=approval.approved_by,
        approved_at=approval.approved_at,
    )
    if (approval, membership, universe) != (expected_approval, expected_member, expected_universe):
        raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT")
    # Explicit full-object comparison above protects the nested locator digest that
    # the legacy universe self-hash intentionally omits.
    if (
        publication.tenant_id,
        publication.composite_id,
        publication.definition_version,
        publication.membership_revision,
        publication.membership_content_hash,
        publication.policy_version,
        publication.source_cut_id,
        publication.decision_count,
        publication.supersedes_membership_revision,
        publication.affected_from,
        publication.affected_to,
        publication.decided_at,
    ) != (
        membership.tenant_id,
        membership.composite_id,
        membership.definition_version,
        membership.membership_revision,
        membership.content_hash,
        membership.policy_version,
        membership.source_cut_id,
        len(membership.decisions),
        membership.supersedes_membership_revision,
        membership.affected_from,
        membership.affected_to,
        membership.decided_at,
    ):
        raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT")
    content = dict(
        definition=definition,
        approval=approval,
        membership_binding=EvidenceBinding(
            product_name="CompositeMembership",
            product_version="v1",
            revision=membership.membership_revision,
            digest=membership.content_hash,
        ),
        universe_binding=EvidenceBinding(
            product_name="CompositeUniverseAttestation",
            product_version="v1",
            revision=universe.attestation_version,
            digest=universe.content_hash,
        ),
        source_cut_id=universe.source_cut_id,
        publication_sequence=publication.sequence,
    )
    if isinstance(approval, MonthlyAmendmentApproval):
        if parent_publication is None or (
            parent_publication.tenant_id,
            parent_publication.composite_id,
            parent_publication.definition_version,
            parent_publication.membership_revision,
            parent_publication.membership_content_hash,
            parent_publication.sequence,
        ) != (
            parent.tenant_id,
            parent.composite_id,
            parent.definition_version,
            parent.membership_revision,
            parent.content_hash,
            approval.proposal.amendment.expected_current_publication_sequence,
        ):
            raise ValueError("COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT")
        return MonthlyAmendmentPublicationReceipt.model_validate(
            content | {"lineage": approval.proposal.amendment}
        )
    return MonthlyEligibilityPublicationReceipt.model_validate(content)
