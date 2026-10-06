"""Content-bound synthetic policy control; not institutional identity attestation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import EvidenceBinding, Identity, StrictAuthorityModel
from src.core.composite_eligibility.observations import UtcInstant
from src.core.composite_eligibility.policy import ResolvedMonthlyPolicy, month_window


class MonthlyPolicyProposal(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyPolicyProposal"] = "CompositeMonthlyPolicyProposal"
    product_version: Literal["v1"] = "v1"
    proposal_revision: Identity
    eligibility_policy_version: Identity
    policy: ResolvedMonthlyPolicy
    attachments: list[EvidenceBinding] = Field(min_length=1, max_length=20)
    proposed_by: Identity
    proposed_at: UtcInstant
    content_hash: str = ""

    @model_validator(mode="after")
    def require_prospective_pinned_material(self) -> MonthlyPolicyProposal:
        self.policy = ResolvedMonthlyPolicy.model_validate(self.policy.model_dump(mode="json"))
        first, _ = month_window(self.policy.month)
        if datetime.fromisoformat(self.proposed_at).date().isoformat() >= first:
            raise ValueError("COMPOSITE_ELIGIBILITY_RETROSPECTIVE_POLICY_FORBIDDEN")
        keys = [
            (item.product_name, item.product_version, item.revision) for item in self.attachments
        ]
        if keys != sorted(set(keys)):
            raise ValueError("COMPOSITE_ELIGIBILITY_ATTACHMENTS_NONCANONICAL")
        expected = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("COMPOSITE_ELIGIBILITY_PROPOSAL_CONTENT_MISMATCH")
        self.content_hash = expected
        return self


class MonthlyPolicyApproval(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyPolicyApproval"] = "CompositeMonthlyPolicyApproval"
    product_version: Literal["v1"] = "v1"
    evidence_kind: Literal["SYNTHETIC_UNSIGNED"] = "SYNTHETIC_UNSIGNED"
    official_activation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    proposal: MonthlyPolicyProposal
    approved_by: Identity
    approved_at: UtcInstant
    content_hash: str = ""

    @model_validator(mode="after")
    def require_independent_prospective_approval(self) -> MonthlyPolicyApproval:
        self.proposal = MonthlyPolicyProposal.model_validate(self.proposal.model_dump(mode="json"))
        if self.approved_by == self.proposal.proposed_by:
            raise ValueError("COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN")
        approved = datetime.fromisoformat(self.approved_at)
        if approved < datetime.fromisoformat(self.proposal.proposed_at):
            raise ValueError("COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL")
        first, _ = month_window(self.proposal.policy.month)
        if approved.date().isoformat() >= first:
            raise ValueError("COMPOSITE_ELIGIBILITY_RETROSPECTIVE_POLICY_FORBIDDEN")
        expected = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("COMPOSITE_ELIGIBILITY_APPROVAL_CONTENT_MISMATCH")
        self.content_hash = expected
        return self
