"""Exact published monthly evidence; no financial admission or new approval engine."""

from typing import Literal

from pydantic import Field, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import EvidenceBinding, Identity, StrictAuthorityModel
from src.core.composite_definition_versions import CompositeDefinition, decode_composite_definition
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_eligibility.evaluation_control import (
    MonthlyEvaluationApproval,
    MonthlyEvaluationProposal,
)
from src.core.composite_eligibility.publication import build_monthly_publication
from src.core.composite_membership import (
    DpmCompositeMembershipRevision,
    DpmCompositeDefinition,
    DpmCompositeSourceAuthority,
)
from src.core.composite_publication import DpmCompositeMembershipPublication
from src.core.composite_universe import DpmCompositeUniverseAttestation


class MonthlyEligibilityPublicationReceipt(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEligibilityPublicationReceipt"] = (
        "CompositeMonthlyEligibilityPublicationReceipt"
    )
    product_version: Literal["v1"] = "v1"
    definition: CompositeDefinition
    approval: MonthlyEvaluationApproval
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
    def require_exact_bound_content(self) -> "MonthlyEligibilityPublicationReceipt":
        self.definition = decode_composite_definition(self.definition.model_dump(mode="json"))
        self.approval = MonthlyEvaluationApproval.model_validate(
            self.approval.model_dump(mode="json")
        )
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


def published_monthly_receipt(
    *,
    definition: CompositeDefinition,
    approval: MonthlyEvaluationApproval,
    retained_policy: MonthlyPolicyApproval,
    retained_policy_proposal: MonthlyPolicyProposal,
    retained_proposal: MonthlyEvaluationProposal,
    parent: DpmCompositeMembershipRevision,
    membership: DpmCompositeMembershipRevision,
    universe: DpmCompositeUniverseAttestation,
    publication: DpmCompositeMembershipPublication,
) -> MonthlyEligibilityPublicationReceipt:
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
    return MonthlyEligibilityPublicationReceipt(
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
