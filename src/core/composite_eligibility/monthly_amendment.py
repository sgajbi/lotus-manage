"""Explicit immutable source correction claims; no retrospective policy authority."""

from __future__ import annotations

from typing import Any, Literal
from datetime import datetime

from pydantic import Field, model_validator

from src.core.composite_authority_models import (
    BusinessDate,
    Digest,
    EvidenceBinding,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_eligibility.evaluation_control import (
    MonthlyEvaluationApprovalContent,
    MonthlyEvaluationApproval,
    MonthlyEvaluationProposalContent,
    MonthlyEvaluationProposal,
    HistoricalMonthlyEvaluationProposal,
    HistoricalMonthlyEvaluationApproval,
    HistoricalMonthlyProposalContent,
    HistoricalMonthlyApprovalContent,
)
from src.core.composite_eligibility.approval import MonthlyPolicyApproval
from src.core.composite_eligibility.policy import month_window


class MonthlyApprovalBinding(StrictAuthorityModel):
    """Versioned monthly approval identity, separate from frozen authority bindings."""

    product_name: Literal["CompositeMonthlyEvaluationApproval"] = (
        "CompositeMonthlyEvaluationApproval"
    )
    product_version: Literal["v1", "v2"]
    revision: Identity
    digest: Digest


class MonthlyReceiptBinding(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEligibilityPublicationReceipt"] = (
        "CompositeMonthlyEligibilityPublicationReceipt"
    )
    product_version: Literal["v1", "v2"]
    revision: Identity
    digest: Digest


class MonthlySourceAmendmentContent(StrictAuthorityModel):
    correction_kind: Literal["SOURCE_CORRECTION"]
    predecessor_approval_binding: MonthlyApprovalBinding | HistoricalMonthlyApprovalBinding
    predecessor_receipt_binding: MonthlyReceiptBinding | HistoricalMonthlyReceiptBinding
    original_approval_binding: MonthlyApprovalBinding | HistoricalMonthlyApprovalBinding
    expected_authority_binding: MonthlyApprovalBinding | HistoricalMonthlyApprovalBinding
    projection_parent_membership_binding: EvidenceBinding
    expected_current_publication_sequence: int = Field(gt=0)
    affected_from: BusinessDate
    affected_to: BusinessDate
    reason_code: Identity
    reason: str = Field(min_length=1, max_length=2048)
    evidence_bindings: list[EvidenceBinding] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def require_explicit_unambiguous_claims(self) -> "MonthlySourceAmendmentContent":
        if not self.reason.strip():
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_REASON_REQUIRED")
        if self.expected_authority_binding != self.predecessor_approval_binding:
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_AUTHORITY_MISMATCH")
        if self.predecessor_receipt_binding.revision != self.predecessor_approval_binding.revision:
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_PREDECESSOR_MISMATCH")
        if (
            self.predecessor_receipt_binding.product_version
            != self.predecessor_approval_binding.product_version
        ):
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_PREDECESSOR_VERSION_MISMATCH")
        if self.projection_parent_membership_binding.product_name != "CompositeMembership":
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_PROJECTION_PARENT_INVALID")
        identities = [
            (item.product_name, item.product_version, item.revision)
            for item in self.evidence_bindings
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_EVIDENCE_AMBIGUOUS")
        return self


class HistoricalMonthlyApprovalBinding(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEvaluationApproval"] = (
        "CompositeMonthlyEvaluationApproval"
    )
    product_version: Literal["v3", "v4"]
    revision: Identity
    digest: Digest


class HistoricalMonthlyReceiptBinding(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEligibilityPublicationReceipt"] = (
        "CompositeMonthlyEligibilityPublicationReceipt"
    )
    product_version: Literal["v3", "v4"]
    revision: Identity
    digest: Digest


class MonthlySourceAmendment(MonthlySourceAmendmentContent):
    predecessor_approval_binding: MonthlyApprovalBinding
    predecessor_receipt_binding: MonthlyReceiptBinding
    original_approval_binding: MonthlyApprovalBinding
    expected_authority_binding: MonthlyApprovalBinding


class HistoricalMonthlySourceAmendment(MonthlySourceAmendmentContent):
    predecessor_approval_binding: HistoricalMonthlyApprovalBinding
    predecessor_receipt_binding: HistoricalMonthlyReceiptBinding
    original_approval_binding: HistoricalMonthlyApprovalBinding
    expected_authority_binding: HistoricalMonthlyApprovalBinding

    @model_validator(mode="after")
    def require_historical_root(self) -> "HistoricalMonthlySourceAmendment":
        if self.original_approval_binding.product_version != "v3":
            raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_ORIGINAL_MISMATCH")
        return self


class MonthlyAmendmentProposalContent(MonthlyEvaluationProposalContent):
    amendment: MonthlySourceAmendment | HistoricalMonthlySourceAmendment

    def require_parent_clock(self, decided_at: datetime) -> None:
        if datetime.fromisoformat(self.proposed_at) < decided_at:
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_CLOCK_MISMATCH")

    @model_validator(mode="after")
    def require_complete_month_projection(self) -> "MonthlyAmendmentProposalContent":
        if (self.amendment.affected_from, self.amendment.affected_to) != month_window(
            self.evaluation.month
        ):
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_WINDOW_MISMATCH")
        parent = self.amendment.projection_parent_membership_binding
        if (parent.revision, parent.digest) != (
            self.parent_membership_revision,
            self.parent_membership_content_hash,
        ):
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_PROJECTION_PARENT_MISMATCH")
        if self.evaluation_revision in {
            self.amendment.predecessor_approval_binding.revision,
            self.amendment.original_approval_binding.revision,
        }:
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_REVISION_REUSED")
        if self.publication_evidence_version != "v1" or self.source_assembly_evidence is None:
            raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_SOURCE_EVIDENCE_REQUIRED")
        return self


class MonthlyAmendmentProposal(MonthlyAmendmentProposalContent):
    product_version: Literal["v2"] = "v2"
    policy_approval: MonthlyPolicyApproval
    amendment: MonthlySourceAmendment


class HistoricalMonthlyAmendmentProposal(
    HistoricalMonthlyProposalContent, MonthlyAmendmentProposalContent
):
    product_version: Literal["v4"] = "v4"
    amendment: HistoricalMonthlySourceAmendment


class MonthlyAmendmentApprovalContent(MonthlyEvaluationApprovalContent):
    proposal: MonthlyAmendmentProposalContent


class MonthlyAmendmentApproval(MonthlyAmendmentApprovalContent):
    product_version: Literal["v2"] = "v2"
    proposal: MonthlyAmendmentProposal


class HistoricalMonthlyAmendmentApproval(
    HistoricalMonthlyApprovalContent, MonthlyAmendmentApprovalContent
):
    product_version: Literal["v4"] = "v4"
    proposal: HistoricalMonthlyAmendmentProposal


MonthlyProposal = (
    MonthlyEvaluationProposal
    | MonthlyAmendmentProposal
    | HistoricalMonthlyEvaluationProposal
    | HistoricalMonthlyAmendmentProposal
)
MonthlyApproval = (
    MonthlyEvaluationApproval
    | MonthlyAmendmentApproval
    | HistoricalMonthlyEvaluationApproval
    | HistoricalMonthlyAmendmentApproval
)
MonthlyCorrectionApproval = MonthlyAmendmentApproval | HistoricalMonthlyAmendmentApproval


def decode_monthly_proposal(wire: dict[str, Any]) -> MonthlyProposal:
    """Select an explicit contract; absent version retains ordinary historical behavior."""
    version = wire.get("product_version", "v1")
    if version == "v1":
        return MonthlyEvaluationProposal.model_validate(wire)
    if version == "v2":
        return MonthlyAmendmentProposal.model_validate(wire)
    if version == "v3":
        return HistoricalMonthlyEvaluationProposal.model_validate(wire)
    if version == "v4":
        return HistoricalMonthlyAmendmentProposal.model_validate(wire)
    raise ValueError("COMPOSITE_MONTHLY_EVALUATION_VERSION_UNSUPPORTED")


def decode_monthly_approval(wire: dict[str, Any]) -> MonthlyApproval:
    version = wire.get("product_version", "v1")
    if version == "v1":
        return MonthlyEvaluationApproval.model_validate(wire)
    if version == "v2":
        return MonthlyAmendmentApproval.model_validate(wire)
    if version == "v3":
        return HistoricalMonthlyEvaluationApproval.model_validate(wire)
    if version == "v4":
        return HistoricalMonthlyAmendmentApproval.model_validate(wire)
    raise ValueError("COMPOSITE_MONTHLY_APPROVAL_VERSION_UNSUPPORTED")
