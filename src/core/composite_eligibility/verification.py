"""Typed verification boundary; schemas and caller headers do not qualify evidence."""

from datetime import date
from typing import Literal, Protocol

from pydantic import model_validator

from src.core.composite_authority_models import (
    Digest,
    EvidenceBinding,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_eligibility.staged_subject import bind_content

VerificationPurpose = Literal[
    "ELIGIBILITY_POLICY",
    "ELIGIBILITY_POLICY_EVALUATION",
    "COMPOSITE_ECONOMIC_AUTHORITY_PROFILE",
    "RETURN_METHOD_CALENDAR",
    "PROVIDER_REGISTRATION",
]


class VerificationRequest(StrictAuthorityModel):
    purpose: VerificationPurpose
    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    subject_content_hash: Digest
    claims_digest: Digest
    effective_from: str
    effective_to: str
    binding: EvidenceBinding | None = None
    source_product: Identity | None = None

    @model_validator(mode="after")
    def require_effective_window(self) -> "VerificationRequest":
        first = date.fromisoformat(self.effective_from)
        last = date.fromisoformat(self.effective_to)
        if last < first:
            raise ValueError("COMPOSITE_SUBJECT_VERIFICATION_WINDOW_INVALID")
        return self


class VerificationReceipt(StrictAuthorityModel):
    product_name: Literal["CompositeEvidenceVerificationReceipt"] = (
        "CompositeEvidenceVerificationReceipt"
    )
    product_version: Literal["v1"] = "v1"
    posture: Literal["SYNTHETIC_NON_CERTIFYING", "QUALIFIED_RECEIPT"]
    request: VerificationRequest
    verifier_id: Identity
    issuer_id: Identity
    artifact_revision: Identity
    artifact_digest: Digest
    content_hash: str = ""

    @model_validator(mode="after")
    def require_receipt_content(self) -> "VerificationReceipt":
        bind_content(self)
        return self


class CompositeEvidenceVerifier(Protocol):
    def verify(self, request: VerificationRequest) -> VerificationReceipt | None:
        """Return a server-resolved receipt, never an echoed request flag."""


class UnavailableCompositeEvidenceVerifier:
    def verify(self, request: VerificationRequest) -> VerificationReceipt | None:
        return None


def require_verification(
    verifier: CompositeEvidenceVerifier, request: VerificationRequest
) -> VerificationReceipt:
    result = verifier.verify(request)
    if result is None:
        raise ValueError("COMPOSITE_SUBJECT_VERIFICATION_UNAVAILABLE")
    result = VerificationReceipt.model_validate(result.model_dump(mode="json"))
    if result.request != request:
        raise ValueError("COMPOSITE_SUBJECT_VERIFICATION_BINDING_MISMATCH")
    return result
