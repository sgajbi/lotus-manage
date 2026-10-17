"""Retained signed native result integrity, never standalone deployment admission.

An embedded key can validate internally consistent signed content, including content
created by a self-selected key. Previously admitted status requires retrieval of the
original proof under server-owned immutable proposal/approval custody. Fresh
verify_with_proof implementations must use independent deployment policy, current
server time/revocation and independent reads; this module cannot issue that grant.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from src.core.common.artifact_credentials import CredentialKey, verified_artifact
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import Digest, Identity
from src.core.composite_eligibility.native_source_custody import NativeInstant, NativeModel
from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest


class MonthlySourceVerifierKey(NativeModel):
    kid: Identity
    kty: Literal["OKP"] = "OKP"
    crv: Literal["Ed25519"] = "Ed25519"
    alg: Literal["EdDSA"] = "EdDSA"
    x: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    revoked: Literal[False] = False

    @model_validator(mode="after")
    def require_canonical_key(self) -> MonthlySourceVerifierKey:
        raw = base64.urlsafe_b64decode(self.x + "=")
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != self.x:
            raise ValueError("COMPOSITE_SOURCE_KEY_NONCANONICAL")
        return self


class MonthlySourceAdmissionContext(NativeModel):
    configuration_digest: Digest
    issuer: str = Field(min_length=1, max_length=256)
    audience: Literal["lotus-manage"] = "lotus-manage"
    principal_id: Identity
    tenant_id: Identity
    purpose: Literal["COMPOSITE_MONTHLY_SOURCE_CUT"] = "COMPOSITE_MONTHLY_SOURCE_CUT"
    operation: Literal["verification"] = "verification"
    evidence_posture: Literal["SYNTHETIC_NON_CERTIFYING"] = "SYNTHETIC_NON_CERTIFYING"
    verifier_key: MonthlySourceVerifierKey
    verifier_key_digest: Digest
    revocation_revision: Identity
    revocation_digest: Digest
    revocation_checked_at: NativeInstant
    revocation_expires_at: NativeInstant
    admitted_at: NativeInstant
    current_revocation_status: Literal["CLEAR"] = "CLEAR"

    @model_validator(mode="after")
    def require_retained_public_snapshot(self) -> MonthlySourceAdmissionContext:
        if not urlsplit(self.issuer).scheme:
            raise ValueError("COMPOSITE_SOURCE_ISSUER_URI_REQUIRED")
        if self.verifier_key_digest != hash_canonical_payload(
            self.verifier_key.model_dump(mode="json")
        ):
            raise ValueError("COMPOSITE_NATIVE_VERIFIER_KEY_DIGEST_MISMATCH")
        checked, admitted, expires = (
            datetime.fromisoformat(value)
            for value in (self.revocation_checked_at, self.admitted_at, self.revocation_expires_at)
        )
        if not checked <= admitted < expires <= checked + timedelta(minutes=5):
            raise ValueError("COMPOSITE_NATIVE_REVOCATION_WINDOW_INVALID")
        return self

    @property
    def keys(self) -> tuple[CredentialKey, ...]:
        return (self.verifier_key,)

    @property
    def revoked_credentials(self) -> tuple[str, ...]:
        return ()

    @property
    def revoked_subjects(self) -> tuple[str, ...]:
        return ()


class MonthlySourceVerificationResult(NativeModel):
    product_name: Literal["CompositeMonthlySourceVerificationResult"] = (
        "CompositeMonthlySourceVerificationResult"
    )
    product_version: Literal["v1"] = "v1"
    receipt: VerificationReceipt
    native_custody_digest: Digest
    admission: MonthlySourceAdmissionContext

    def __getattribute__(self, name: str) -> Any:
        value = super().__getattribute__(name)
        # Legacy receipts remain mutable globally; this retained boundary owns its
        # canonical instance and exposes only detached receipt/request/binding copies.
        if name == "receipt" and isinstance(value, VerificationReceipt):
            return value.model_copy(deep=True)
        return value

    @model_validator(mode="after")
    def require_result_binding(self) -> MonthlySourceVerificationResult:
        receipt = VerificationReceipt.model_validate(self.receipt.model_dump(mode="json"))
        admission = self.admission
        if (
            receipt.posture != admission.evidence_posture
            or receipt.request.purpose != admission.purpose
            or receipt.verifier_id != admission.principal_id
            or receipt.request.tenant_id != admission.tenant_id
            or receipt.artifact_digest != self.native_custody_digest
            or receipt.request.source_product != "CompositeMonthlyEligibilityAssembly"
        ):
            raise ValueError("COMPOSITE_NATIVE_RESULT_BINDING_MISMATCH")
        object.__setattr__(self, "receipt", receipt)
        return self


class MonthlySourceAdmissionProof(NativeModel):
    product_name: Literal["CompositeMonthlySourceAdmissionProof"] = (
        "CompositeMonthlySourceAdmissionProof"
    )
    product_version: Literal["v1"] = "v1"
    result: MonthlySourceVerificationResult
    verifier_credential: str = Field(min_length=1, max_length=16384)
    content_hash: str = ""

    @model_validator(mode="after")
    def require_signed_content_integrity(self) -> MonthlySourceAdmissionProof:
        """Validate original signed content only; an embedded key is not enrollment."""
        result = self.result
        # Revalidate nested constructed/copied models at the retained boundary.
        result = MonthlySourceVerificationResult.model_validate(result.model_dump(mode="json"))
        object.__setattr__(self, "result", result)
        verified_artifact(
            self.verifier_credential,
            binding=result.admission,
            request=result.receipt.request.model_dump(mode="json"),
            payload=result.model_dump(mode="json"),
            now=datetime.fromisoformat(result.admission.admitted_at).timestamp(),
        )
        digest = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != digest:
            raise ValueError("COMPOSITE_NATIVE_PROOF_CONTENT_MISMATCH")
        object.__setattr__(self, "content_hash", digest)
        return self


@dataclass(frozen=True)
class NativeAssemblyVerification:
    """One immutable pair; the configured owner must freshly admit before returning it."""

    receipt: VerificationReceipt
    proof: MonthlySourceAdmissionProof

    def __getattribute__(self, name: str) -> Any:
        value = super().__getattribute__(name)
        if name == "receipt" and isinstance(value, VerificationReceipt):
            return value.model_copy(deep=True)
        return value

    def __post_init__(self) -> None:
        proof = MonthlySourceAdmissionProof.model_validate(self.proof.model_dump(mode="json"))
        receipt = VerificationReceipt.model_validate(self.receipt.model_dump(mode="json"))
        if proof.result.receipt != receipt:
            raise ValueError("COMPOSITE_NATIVE_PAIRED_RECEIPT_MISMATCH")
        object.__setattr__(self, "receipt", receipt)
        object.__setattr__(self, "proof", proof)


class NativeAssemblyVerifier(Protocol):
    def verify_with_proof(self, request: VerificationRequest) -> NativeAssemblyVerification | None:
        """Use independent deployment policy/current clock/reads; never proof-selected trust."""
