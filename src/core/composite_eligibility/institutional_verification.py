"""Original institutional artifact identity, distinct from current admission and caller grants."""

from datetime import datetime, timedelta
from typing import Literal, Protocol

from pydantic import Field, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import (
    Digest,
    EvidenceBinding,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_definition_versions import (
    CompositeInstitutionalAuthorityClaims,
    DpmCompositeDefinitionV2,
)
from src.core.composite_eligibility.observations import UtcInstant
from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest


class InstitutionalAttestationArtifact(StrictAuthorityModel):
    """Original content-addressed approval body; the signature is separate from its digest."""

    product_name: Literal["CompositeAuthorityAttestationArtifact"] = (
        "CompositeAuthorityAttestationArtifact"
    )
    product_version: Literal["v1"] = "v1"
    issuer_id: Identity
    attestation_id: Identity
    revision: Identity
    claims: CompositeInstitutionalAuthorityClaims
    subject_binding: EvidenceBinding
    evaluation_approval_binding: EvidenceBinding
    content_hash: str = ""

    @model_validator(mode="after")
    def require_original_content(self) -> "InstitutionalAttestationArtifact":
        expected = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("COMPOSITE_ATTESTATION_ARTIFACT_CONTENT_MISMATCH")
        self.content_hash = expected
        return self


class InstitutionalVerificationRequest(StrictAuthorityModel):
    """Explicit v2 request; it does not change the v1 claims-digest contract."""

    product_name: Literal["CompositeInstitutionalVerificationRequest"] = (
        "CompositeInstitutionalVerificationRequest"
    )
    product_version: Literal["v2"] = "v2"
    purpose: Literal["COMPOSITE_ECONOMIC_AUTHORITY_PROFILE"] = (
        "COMPOSITE_ECONOMIC_AUTHORITY_PROFILE"
    )
    definition: DpmCompositeDefinitionV2
    subject_binding: EvidenceBinding
    evaluation_approval_binding: EvidenceBinding

    @model_validator(mode="after")
    def require_institutional_scope(self) -> "InstitutionalVerificationRequest":
        self.definition = DpmCompositeDefinitionV2.model_validate(
            self.definition.model_dump(mode="json")
        )
        if (
            self.definition.authority_approval.evidence_kind
            != "INSTITUTIONAL_ATTESTATION_REFERENCE"
        ):
            raise ValueError("COMPOSITE_ATTESTATION_REFERENCE_REQUIRED")
        if self.subject_binding.product_name != "CompositeEligibilitySubject" or (
            self.evaluation_approval_binding.product_name != "CompositeSubjectEvaluationApproval"
            or self.definition.source_authority.payload.eligibility_evaluation_binding
            != self.evaluation_approval_binding
        ):
            raise ValueError("COMPOSITE_ATTESTATION_SCOPE_MISMATCH")
        return self


class InstitutionalVerificationContent(StrictAuthorityModel):
    """Fresh verifier result must retain an independently signed original approval artifact."""

    product_name: Literal[
        "CompositeInstitutionalVerificationResult", "CompositeEvidenceVerificationReceipt"
    ]
    product_version: Literal["v2"] = "v2"
    posture: Literal["QUALIFIED_RECEIPT"] = "QUALIFIED_RECEIPT"
    request: InstitutionalVerificationRequest
    artifact: InstitutionalAttestationArtifact
    original_credential: str = Field(min_length=1, max_length=16384)
    verifier_id: Identity
    issuer_id: Identity

    @model_validator(mode="after")
    def require_resolved_original(self) -> "InstitutionalVerificationContent":
        self.request = InstitutionalVerificationRequest.model_validate(
            self.request.model_dump(mode="json")
        )
        self.artifact = InstitutionalAttestationArtifact.model_validate(
            self.artifact.model_dump(mode="json")
        )
        approval = self.request.definition.authority_approval
        if approval.evidence_kind != "INSTITUTIONAL_ATTESTATION_REFERENCE":
            raise ValueError("COMPOSITE_ATTESTATION_REFERENCE_REQUIRED")
        reference = approval.attestation
        artifact = self.artifact
        if (
            reference.issuer_id,
            reference.attestation_id,
            reference.revision,
            reference.digest,
            approval.claims,
            self.request.subject_binding,
            self.request.evaluation_approval_binding,
        ) != (
            artifact.issuer_id,
            artifact.attestation_id,
            artifact.revision,
            artifact.content_hash,
            artifact.claims,
            artifact.subject_binding,
            artifact.evaluation_approval_binding,
        ):
            raise ValueError("COMPOSITE_ATTESTATION_ORIGINAL_MISMATCH")
        return self


class InstitutionalVerificationResult(InstitutionalVerificationContent):
    product_name: Literal["CompositeInstitutionalVerificationResult"] = (
        "CompositeInstitutionalVerificationResult"
    )


class InstitutionalAdmissionProof(StrictAuthorityModel):
    """Server-retained trust provenance; not an institutional approval or authorization grant."""

    configuration_digest: Digest
    signer_key_digest: Digest
    verifier_key_digest: Digest
    revocation_revision: Identity
    revocation_digest: Digest
    revocation_checked_at: UtcInstant
    revocation_expires_at: UtcInstant
    admitted_at: UtcInstant
    verifier_credential: str = Field(min_length=1, max_length=16384)

    @model_validator(mode="after")
    def require_current_admission(self) -> "InstitutionalAdmissionProof":
        checked = datetime.fromisoformat(self.revocation_checked_at)
        expiry = datetime.fromisoformat(self.revocation_expires_at)
        admitted = datetime.fromisoformat(self.admitted_at)
        if not checked <= admitted < expiry or expiry > checked + timedelta(minutes=5):
            raise ValueError("COMPOSITE_ATTESTATION_ADMISSION_WINDOW_INVALID")
        return self


class InstitutionalVerificationReceipt(InstitutionalVerificationContent):
    product_name: Literal["CompositeEvidenceVerificationReceipt"] = (
        "CompositeEvidenceVerificationReceipt"
    )
    admission: InstitutionalAdmissionProof
    content_hash: str = ""

    @model_validator(mode="after")
    def require_admission_content(self) -> "InstitutionalVerificationReceipt":
        expected = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("COMPOSITE_ATTESTATION_RECEIPT_CONTENT_MISMATCH")
        self.content_hash = expected
        return self


class InstitutionalEvidenceVerifier(Protocol):
    def verify(
        self, request: InstitutionalVerificationRequest
    ) -> InstitutionalVerificationReceipt | None: ...
    def verify_related(self, request: VerificationRequest) -> VerificationReceipt | None: ...


def require_bound_related_artifact(receipt: VerificationReceipt) -> None:
    """Fresh admission and immutable v2 custody require the same exact artifact identity."""
    binding = receipt.request.binding
    if binding is None or (receipt.artifact_revision, receipt.artifact_digest) != (
        binding.revision,
        binding.digest,
    ):
        raise ValueError("COMPOSITE_ATTESTATION_RELATED_ARTIFACT_MISMATCH")


class UnavailableInstitutionalEvidenceVerifier:
    def verify(
        self, request: InstitutionalVerificationRequest
    ) -> InstitutionalVerificationReceipt | None:
        return None

    def verify_related(self, request: VerificationRequest) -> VerificationReceipt | None:
        return None
