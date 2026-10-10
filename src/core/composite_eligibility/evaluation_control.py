"""Immutable evaluated-source custody and independent monthly membership control."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import Digest, Identity, StrictAuthorityModel
from src.core.composite_eligibility.approval import (
    MonthlyPolicyApproval,
    MonthlyPolicyApprovalVariant,
    decode_policy_approval,
)
from src.core.composite_eligibility.historical_policy import (
    HistoricalMonthlyPolicyApproval,
    HistoricalPolicyVerification,
)
from src.core.composite_eligibility.evaluation import (
    MonthlyEligibilityEvaluation,
    evaluate_monthly_eligibility,
)
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations, UtcInstant
from src.core.composite_eligibility.policy import month_window
from src.core.composite_eligibility.source_assembly import (
    VerifiedMonthlySourceAssembly,
    retained_source_assembly,
)
from src.core.composite_universe import DpmCompositeUniverseAttestation


def _publication_marker_schema(schema: dict[str, Any]) -> None:
    """Omission permits old custody; explicit null is not a supported marker."""
    schema.pop("default", None)


class MonthlyEvaluationProposalContent(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEvaluationProposal"] = (
        "CompositeMonthlyEvaluationProposal"
    )
    product_version: Literal["v1", "v2", "v3", "v4"]
    evaluation_revision: Identity
    target_membership_revision: Identity
    parent_membership_revision: Identity
    parent_membership_content_hash: Digest
    policy_approval: MonthlyPolicyApprovalVariant
    universe: DpmCompositeUniverseAttestation
    observations: MonthlyEligibilityObservations
    source_assembly_evidence: VerifiedMonthlySourceAssembly | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    publication_evidence_version: Literal["v1"] | SkipJsonSchema[None] = Field(
        default=None,
        exclude_if=lambda value: value is None,
        json_schema_extra=_publication_marker_schema,
    )
    evaluation: MonthlyEligibilityEvaluation
    proposed_by: Identity
    proposed_at: UtcInstant
    correlation_id: Identity
    content_hash: str = ""

    @model_validator(mode="before")
    @classmethod
    def require_supported_publication_evidence_version(cls, wire: object) -> object:
        if (
            isinstance(wire, dict)
            and "publication_evidence_version" in wire
            and wire["publication_evidence_version"] is None
        ):
            raise ValueError("COMPOSITE_ELIGIBILITY_PUBLICATION_EVIDENCE_VERSION_INVALID")
        return wire

    @model_validator(mode="after")
    def require_reproducible_bound_evaluation(self) -> MonthlyEvaluationProposalContent:
        self.policy_approval = decode_policy_approval(self.policy_approval.model_dump(mode="json"))
        self.universe = DpmCompositeUniverseAttestation.model_validate(
            self.universe.model_dump(mode="json")
        )
        self.observations = MonthlyEligibilityObservations.model_validate(
            self.observations.model_dump(mode="json")
        )
        self.source_assembly_evidence = retained_source_assembly(
            self.source_assembly_evidence, self.observations
        )
        self.evaluation = MonthlyEligibilityEvaluation.model_validate(
            self.evaluation.model_dump(mode="json")
        )
        _require_universe_binding(self)
        if self.proposed_at != self.evaluation.evaluated_at:
            raise ValueError("COMPOSITE_ELIGIBILITY_PROPOSAL_CLOCK_MISMATCH")
        recomputed = evaluate_monthly_eligibility(
            self.policy_approval.proposal.policy,
            self.observations,
            evaluated_at=self.proposed_at,
            universe_content_hash=self.universe.content_hash,
        )
        if recomputed != self.evaluation:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_RECOMPUTATION_MISMATCH")
        if self.target_membership_revision == self.parent_membership_revision:
            raise ValueError("COMPOSITE_ELIGIBILITY_TARGET_REVISION_REUSED")
        expected = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_CONTENT_MISMATCH")
        self.content_hash = expected
        return self


class MonthlyEvaluationProposal(MonthlyEvaluationProposalContent):
    """Frozen ordinary monthly evaluation wire and digest."""

    product_version: Literal["v1"] = "v1"
    policy_approval: MonthlyPolicyApproval


class HistoricalMonthlyProposalContent(MonthlyEvaluationProposalContent):
    policy_approval: HistoricalMonthlyPolicyApproval
    operation_verification: HistoricalPolicyVerification

    @model_validator(mode="after")
    def require_current_policy_verification(self) -> "HistoricalMonthlyProposalContent":
        require_operation_verification(
            self,
            self.operation_verification,
            "EVALUATION_PROPOSAL",
            self.proposed_by,
            self.proposed_at,
        )
        return self


class HistoricalMonthlyEvaluationProposal(HistoricalMonthlyProposalContent):
    product_version: Literal["v3"] = "v3"


def require_operation_verification(
    proposal: MonthlyEvaluationProposalContent,
    proof: HistoricalPolicyVerification,
    operation: str,
    actor: str,
    instant: str,
) -> None:
    if not isinstance(proposal.policy_approval, HistoricalMonthlyPolicyApproval):
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_REQUEST_MISMATCH")
    proof = HistoricalPolicyVerification.model_validate(proof.model_dump(mode="json"))
    if datetime.fromisoformat(instant) < datetime.fromisoformat(
        proposal.policy_approval.approved_at
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL")
    if proof.mapping != proposal.policy_approval.verification.mapping:
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_MAPPING_MISMATCH")
    intent = (
        hash_canonical_payload(
            proposal.model_dump(mode="json", exclude={"content_hash", "operation_verification"})
        )
        if operation == "EVALUATION_PROPOSAL"
        else proposal.content_hash
    )
    request = proof.request
    if (
        request.operation,
        request.revision,
        request.actor_id,
        request.requested_at,
        request.intent_digest,
    ) != (operation, proposal.evaluation_revision, actor, instant, intent):
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_INTENT_MISMATCH")


def _require_universe_binding(proposal: MonthlyEvaluationProposalContent) -> None:
    scope = proposal.policy_approval.proposal.policy.scope
    universe = proposal.universe
    first, last = month_window(proposal.policy_approval.proposal.policy.month)
    if universe.coverage_from > first or universe.coverage_to < last:
        raise ValueError("COMPOSITE_ELIGIBILITY_UNIVERSE_WINDOW_INCOMPLETE")
    if (
        universe.tenant_id,
        universe.composite_id,
        universe.definition_version,
        universe.membership_revision,
        universe.membership_content_hash,
    ) != (
        scope.tenant_id,
        scope.composite_id,
        scope.definition_version,
        proposal.parent_membership_revision,
        proposal.parent_membership_content_hash,
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_UNIVERSE_BINDING_MISMATCH")
    if proposal.observations.expected_portfolio_ids != universe.expected_portfolio_ids:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_UNIVERSE_MISMATCH")
    _require_observation_product_binding(proposal)


def _require_observation_product_binding(proposal: MonthlyEvaluationProposalContent) -> None:
    """Keep independently pinned source-product identity separate from universe admission."""
    products = [
        item
        for item in proposal.universe.source_products
        if item.product_name == proposal.observations.product_name
        and item.contract_version == proposal.observations.product_version
        and item.authority_scope == "POLICY_INPUT"
    ]
    if len(products) != 1:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_REFERENCE_UNAVAILABLE")
    product = products[0]
    if (product.source_cut_id, product.source_watermark, product.content_hash) != (
        proposal.observations.source_cut_id,
        proposal.observations.source_revision,
        hash_canonical_payload(proposal.observations.model_dump(mode="json")),
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_SOURCE_BINDING_MISMATCH")


def evaluation_key(proposal: MonthlyEvaluationProposalContent) -> tuple[str, str, str, str]:
    """Canonical custody scope shared by storage adapters."""
    scope = proposal.policy_approval.proposal.policy.scope
    return (
        scope.tenant_id,
        scope.composite_id,
        scope.definition_version,
        proposal.evaluation_revision,
    )


def monthly_evaluation_approval_claims_hash(
    proposal: MonthlyEvaluationProposalContent,
    *,
    approved_by: str,
    approved_at: str,
) -> str:
    return hash_canonical_payload(
        {
            "purpose": "COMPOSITE_MONTHLY_MEMBERSHIP_APPROVAL",
            "proposal_content_hash": proposal.content_hash,
            "approved_by": approved_by,
            "approved_at": approved_at,
        }
    )


class MonthlyEvaluationApprovalContent(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEvaluationApproval"] = (
        "CompositeMonthlyEvaluationApproval"
    )
    product_version: Literal["v1", "v2", "v3", "v4"]
    evidence_kind: Literal["SYNTHETIC_UNSIGNED"] = "SYNTHETIC_UNSIGNED"
    official_activation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    proposal: MonthlyEvaluationProposalContent
    approved_by: Identity
    approved_at: UtcInstant
    claims_digest: Digest
    membership_content_hash: Digest
    published_universe_content_hash: Digest
    content_hash: str = ""

    @model_validator(mode="after")
    def require_independent_exact_approval(self) -> MonthlyEvaluationApprovalContent:
        self.proposal = type(self.proposal).model_validate(self.proposal.model_dump(mode="json"))
        if self.approved_by == self.proposal.proposed_by:
            raise ValueError("COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN")
        if datetime.fromisoformat(self.approved_at) < datetime.fromisoformat(
            self.proposal.proposed_at
        ):
            raise ValueError("COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL")
        expected_claims = monthly_evaluation_approval_claims_hash(
            self.proposal,
            approved_by=self.approved_by,
            approved_at=self.approved_at,
        )
        if self.claims_digest != expected_claims:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_CLAIMS_MISMATCH")
        expected = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_CONTENT_MISMATCH")
        self.content_hash = expected
        return self


class MonthlyEvaluationApproval(MonthlyEvaluationApprovalContent):
    """Frozen ordinary approval; only the ordinary proposal is admissible."""

    product_version: Literal["v1"] = "v1"
    proposal: MonthlyEvaluationProposal


class HistoricalMonthlyApprovalContent(MonthlyEvaluationApprovalContent):
    operation_verification: HistoricalPolicyVerification

    @model_validator(mode="after")
    def require_current_policy_verification(self) -> "HistoricalMonthlyApprovalContent":
        require_operation_verification(
            self.proposal,
            self.operation_verification,
            "EVALUATION_APPROVAL",
            self.approved_by,
            self.approved_at,
        )
        return self


class HistoricalMonthlyEvaluationApproval(HistoricalMonthlyApprovalContent):
    product_version: Literal["v3"] = "v3"
    proposal: HistoricalMonthlyEvaluationProposal
