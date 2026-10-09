"""First-membership projection and exact subject-to-definition finalization."""

from datetime import datetime
import json
from typing import Any, Literal, TypedDict, Sequence

from pydantic import Field, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import Digest, EvidenceBinding, StrictAuthorityModel
from src.core.composite_definition_versions import DpmCompositeDefinitionV2
from src.core.composite_eligibility.policy import month_window
from src.core.composite_eligibility.publication import monthly_decisions
from src.core.composite_eligibility.staged_controls import (
    SubjectEvaluationApproval,
    SubjectEvaluationProposal,
)
from src.core.composite_eligibility.staged_subject import EligibilitySubject, bind_content
from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest
from src.core.composite_eligibility.institutional_verification import (
    InstitutionalVerificationRequest,
    InstitutionalVerificationReceipt,
    require_bound_related_artifact,
)
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_universe import DpmCompositeUniverseAttestation


def initial_projection(
    proposal: SubjectEvaluationProposal, claims: str, actor: str, instant: str
) -> tuple[DpmCompositeMembershipRevision, DpmCompositeUniverseAttestation]:
    subject = proposal.policy_approval.proposal.subject
    first, last = month_window(subject.month)
    if (
        subject.universe.posture != "COMPLETE"
        or proposal.evaluation.declared_universe_coverage != "COMPLETE"
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE")
    if datetime.fromisoformat(proposal.observations.source_generated_at).date().isoformat() <= last:
        raise ValueError("COMPOSITE_ELIGIBILITY_PUBLICATION_SOURCE_NOT_FINALIZED")
    revision = DpmCompositeMembershipRevision(
        tenant_id=subject.tenant_id,
        composite_id=subject.composite_id,
        definition_version=subject.definition_version,
        membership_revision=proposal.target_membership_revision,
        policy_version=subject.eligibility_policy_version,
        source_cut_id=subject.universe.source_cut_id,
        decisions=monthly_decisions(
            proposal.evaluation, proposal.observations, claims, first, last
        ),
        decided_by=actor,
        decided_at=datetime.fromisoformat(instant),
        correlation_id=subject.correlation_id,
    )
    universe = DpmCompositeUniverseAttestation(
        tenant_id=subject.tenant_id,
        composite_id=subject.composite_id,
        definition_version=subject.definition_version,
        membership_revision=revision.membership_revision,
        membership_content_hash=revision.content_hash,
        attestation_version=proposal.evaluation_revision,
        coverage_from=first,
        coverage_to=last,
        policy_version=subject.eligibility_policy_version,
        source_cut_id=subject.universe.source_cut_id,
        source_products=[*subject.universe.source_products, proposal.observation_binding],
        posture="COMPLETE",
        expected_portfolio_ids=[member.member_id for member in subject.universe.members],
        expected_portfolio_count=len(subject.universe.members),
        observed_portfolio_count=len(subject.universe.members),
        attested_at=datetime.fromisoformat(instant),
        attested_by=actor,
        correlation_id=subject.correlation_id,
    )
    return revision, universe


class SubjectFinalizationContent(StrictAuthorityModel):
    product_name: Literal["CompositeEligibilityFinalization"] = "CompositeEligibilityFinalization"
    product_version: Literal["v1", "v2"]
    official_activation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    subject: EligibilitySubject
    evaluation_approval: SubjectEvaluationApproval
    definition: DpmCompositeDefinitionV2
    verifications: Sequence[VerificationReceipt | InstitutionalVerificationReceipt] = Field(
        min_length=3, max_length=258
    )
    content_hash: str = ""

    @model_validator(mode="after")
    def require_joined_content(self) -> "SubjectFinalizationContent":
        self.subject = EligibilitySubject.model_validate(self.subject.model_dump(mode="json"))
        self.evaluation_approval = SubjectEvaluationApproval.model_validate(
            self.evaluation_approval.model_dump(mode="json")
        )
        self.definition = DpmCompositeDefinitionV2.model_validate(
            self.definition.model_dump(mode="json")
        )
        if self.evaluation_approval.proposal.policy_approval.proposal.subject != self.subject:
            raise ValueError("COMPOSITE_SUBJECT_APPROVAL_BINDING_MISMATCH")
        require_definition_subject(self.definition, self.subject, self.evaluation_approval)
        self._require_verifications()
        revision, universe = initial_projection(
            self.evaluation_approval.proposal,
            self.evaluation_approval.claims_digest,
            self.evaluation_approval.approved_by,
            self.evaluation_approval.approved_at,
        )
        if (revision.content_hash, universe.content_hash) != (
            self.evaluation_approval.membership_content_hash,
            self.evaluation_approval.universe_content_hash,
        ):
            raise ValueError("COMPOSITE_SUBJECT_PROJECTION_MISMATCH")
        bind_content(self)
        return self

    def _require_verifications(self) -> None:
        """Keep verification identity checks separate from canonical publication projection."""
        requests: list[VerificationRequest | InstitutionalVerificationRequest] = list(
            finalization_verification_requests(self.definition, self.subject)
        )
        if self.product_version == "v2":
            requests[0] = institutional_finalization_request(
                self.definition, self.subject, self.evaluation_approval
            )
            if not isinstance(self.verifications[0], InstitutionalVerificationReceipt) or any(
                item.posture != "QUALIFIED_RECEIPT" for item in self.verifications
            ):
                raise ValueError("COMPOSITE_SUBJECT_INSTITUTIONAL_VERIFICATION_UNAVAILABLE")
        if [receipt.request for receipt in self.verifications] != requests:
            raise ValueError("COMPOSITE_SUBJECT_FINAL_VERIFICATION_MISMATCH")
        if self.product_version == "v2":
            self._require_related_verifications()
        if (
            self.definition.authority_approval.evidence_kind
            == "INSTITUTIONAL_ATTESTATION_REFERENCE"
            and (self.verifications[0].posture != "QUALIFIED_RECEIPT")
        ):
            raise ValueError("COMPOSITE_SUBJECT_INSTITUTIONAL_VERIFICATION_UNAVAILABLE")

    def _require_related_verifications(self) -> None:
        for receipt in self.verifications[1:]:
            if not isinstance(receipt, VerificationReceipt):
                raise ValueError("COMPOSITE_SUBJECT_FINAL_VERIFICATION_MISMATCH")
            require_bound_related_artifact(receipt)


class SubjectFinalization(SubjectFinalizationContent):
    product_version: Literal["v1"] = "v1"
    verifications: list[VerificationReceipt] = Field(min_length=3, max_length=258)


class InstitutionalSubjectFinalization(SubjectFinalizationContent):
    product_version: Literal["v2"] = "v2"
    verifications: list[VerificationReceipt | InstitutionalVerificationReceipt] = Field(
        min_length=3, max_length=258
    )


SubjectFinalizationRecord = SubjectFinalization | InstitutionalSubjectFinalization


def institutional_finalization_request(
    definition: DpmCompositeDefinitionV2,
    subject: EligibilitySubject,
    approval: SubjectEvaluationApproval,
) -> InstitutionalVerificationRequest:
    return InstitutionalVerificationRequest(
        definition=definition,
        subject_binding=EvidenceBinding(
            product_name=subject.product_name,
            product_version=subject.product_version,
            revision=subject.subject_revision,
            digest=subject.content_hash,
        ),
        evaluation_approval_binding=EvidenceBinding(
            product_name=approval.product_name,
            product_version=approval.product_version,
            revision=approval.proposal.evaluation_revision,
            digest=approval.content_hash,
        ),
    )


def decode_subject_finalization(wire: dict[str, Any]) -> SubjectFinalizationRecord:
    version = wire.get("product_version", "v1")
    if version == "v1":
        return SubjectFinalization.model_validate(wire)
    if version == "v2":
        return InstitutionalSubjectFinalization.model_validate(wire)
    raise ValueError("COMPOSITE_SUBJECT_FINALIZATION_VERSION_UNSUPPORTED")


class _VerificationScope(TypedDict):
    tenant_id: str
    composite_id: str
    definition_version: str
    subject_content_hash: str
    effective_from: str
    effective_to: str


def finalization_verification_requests(
    definition: DpmCompositeDefinitionV2, subject: EligibilitySubject
) -> list[VerificationRequest]:
    profile = definition.source_authority.payload
    base: _VerificationScope = {
        "tenant_id": subject.tenant_id,
        "composite_id": subject.composite_id,
        "definition_version": subject.definition_version,
        "subject_content_hash": subject.content_hash,
        "effective_from": profile.effective_from,
        "effective_to": profile.effective_to,
    }
    method = profile.return_method_binding
    requests = [
        VerificationRequest(
            **base,
            purpose="COMPOSITE_ECONOMIC_AUTHORITY_PROFILE",
            claims_digest=hash_canonical_payload(
                definition.authority_approval.claims.model_dump(mode="json")
            ),
        ),
        VerificationRequest(
            **base, purpose="RETURN_METHOD_CALENDAR", claims_digest=method.digest, binding=method
        ),
    ]
    providers = {provider.provider_id: provider for provider in profile.providers}
    for selection in profile.selections:
        provider = providers[selection.provider_id]
        binding = EvidenceBinding(
            product_name="CompositeProviderRegistration",
            product_version="v1",
            revision=provider.registry_revision,
            digest=provider.registry_digest,
        )
        material = {
            "provider": provider.model_dump(mode="json"),
            "source_product": selection.source_product,
            "effective_from": selection.effective_from,
            "effective_to": selection.effective_to,
        }
        scoped: _VerificationScope = {
            **base,
            "effective_from": selection.effective_from,
            "effective_to": selection.effective_to,
        }
        requests.append(
            VerificationRequest(
                **scoped,
                purpose="PROVIDER_REGISTRATION",
                binding=binding,
                source_product=selection.source_product,
                claims_digest=hash_canonical_payload(material),
            )
        )
    return requests


def require_definition_subject(
    definition: DpmCompositeDefinitionV2,
    subject: EligibilitySubject,
    approval: SubjectEvaluationApproval,
) -> None:
    fields = (
        "tenant_id",
        "composite_id",
        "definition_version",
        "display_name",
        "strategy_code",
        "reporting_currency",
        "inception_date",
        "termination_date",
        "eligibility_policy_version",
        "created_by",
        "created_at",
        "correlation_id",
    )
    if any(getattr(definition, field) != getattr(subject, field) for field in fields):
        raise ValueError("COMPOSITE_SUBJECT_DEFINITION_BINDING_MISMATCH")
    profile = definition.source_authority.payload
    first, last = month_window(subject.month)
    if (profile.effective_from, profile.effective_to, profile.member_identities) != (
        first,
        last,
        subject.universe.members,
    ):
        raise ValueError("COMPOSITE_SUBJECT_PROFILE_BINDING_MISMATCH")
    binding = EvidenceBinding(
        product_name=approval.product_name,
        product_version=approval.product_version,
        revision=approval.proposal.evaluation_revision,
        digest=approval.content_hash,
    )
    if profile.eligibility_evaluation_binding != binding:
        raise ValueError("COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH")


def authority_approval_follows_evaluation(
    definition: DpmCompositeDefinitionV2, approval: SubjectEvaluationApproval
) -> bool:
    """Diagnose chronology without changing immutable historical decoding or hashes."""
    return datetime.fromisoformat(
        definition.authority_approval.claims.approved_at
    ) >= datetime.fromisoformat(approval.approved_at)


class SubjectFinalizationReceiptContent(StrictAuthorityModel):
    product_name: Literal["CompositeEligibilityFinalizationReceipt"] = (
        "CompositeEligibilityFinalizationReceipt"
    )
    product_version: Literal["v1", "v2"]
    finalization: SubjectFinalizationRecord
    publication_sequence: int = Field(ge=1)
    membership_content_hash: Digest
    universe_content_hash: Digest
    completeness: Literal["UNVERIFIED"] = "UNVERIFIED"
    content_hash: str = ""

    @model_validator(mode="after")
    def require_receipt_projection(self) -> "SubjectFinalizationReceiptContent":
        self.finalization = decode_subject_finalization(self.finalization.model_dump(mode="json"))
        approval = self.finalization.evaluation_approval
        if (self.membership_content_hash, self.universe_content_hash) != (
            approval.membership_content_hash,
            approval.universe_content_hash,
        ):
            raise ValueError("COMPOSITE_SUBJECT_RECEIPT_BINDING_MISMATCH")
        bind_content(self)
        return self


class SubjectFinalizationReceipt(SubjectFinalizationReceiptContent):
    product_version: Literal["v1"] = "v1"
    finalization: SubjectFinalization


class InstitutionalSubjectFinalizationReceipt(SubjectFinalizationReceiptContent):
    product_version: Literal["v2"] = "v2"
    finalization: InstitutionalSubjectFinalization


SubjectFinalizationProof = SubjectFinalizationReceipt | InstitutionalSubjectFinalizationReceipt


def decode_subject_receipt(wire: dict[str, Any] | str) -> SubjectFinalizationProof:
    payload = json.loads(wire) if isinstance(wire, str) else wire
    if not isinstance(payload, dict):
        raise ValueError("COMPOSITE_SUBJECT_FINALIZATION_WIRE_INVALID")
    version = payload.get("product_version", "v1")
    if version == "v1":
        return SubjectFinalizationReceipt.model_validate(payload)
    if version == "v2":
        return InstitutionalSubjectFinalizationReceipt.model_validate(payload)
    raise ValueError("COMPOSITE_SUBJECT_FINALIZATION_VERSION_UNSUPPORTED")


def finalization_receipt(
    finalization: SubjectFinalizationRecord,
    publication_sequence: int,
    membership_content_hash: str,
    universe_content_hash: str,
) -> SubjectFinalizationProof:
    wire = dict(
        product_version=finalization.product_version,
        finalization=finalization.model_dump(mode="json"),
        publication_sequence=publication_sequence,
        membership_content_hash=membership_content_hash,
        universe_content_hash=universe_content_hash,
    )
    return decode_subject_receipt(wire)
