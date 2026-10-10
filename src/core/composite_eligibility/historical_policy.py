"""Normalized historical policy admission; original formats remain source-owned."""

import base64
import hashlib
from datetime import datetime, timedelta
from typing import Literal, Protocol

from pydantic import Field, model_validator
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import (
    Digest,
    EvidenceBinding,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_eligibility.observations import UtcInstant
from src.core.composite_eligibility.policy import (
    MonthlyPolicyScope,
    ResolvedMonthlyPolicy,
    month_window,
)


class HistoricalContent(StrictAuthorityModel):
    content_hash: str = ""


def bind_historical_content(model: HistoricalContent) -> None:
    expected = hash_canonical_payload(model.model_dump(mode="json", exclude={"content_hash"}))
    if model.content_hash and model.content_hash != expected:
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_CONTENT_MISMATCH")
    model.content_hash = expected


class HistoricalPolicyReference(StrictAuthorityModel):
    issuer_id: Identity
    artifact_id: Identity
    revision: Identity
    raw_digest: Digest
    signing_contract: Identity


class HistoricalPolicyMapping(HistoricalContent):
    """Verified mapping is separate from the bytes and original signature format."""

    reference: HistoricalPolicyReference
    raw_original_base64: str = Field(min_length=4, max_length=2_800_000)
    original_credential: str = Field(min_length=1, max_length=16384)
    policy: ResolvedMonthlyPolicy
    eligibility_policy_version: Identity
    reporting_currency: str = Field(pattern=r"^[A-Z]{3}$")
    attachments: list[EvidenceBinding] = Field(min_length=1, max_length=20)
    original_proposed_by: Identity
    original_proposed_at: UtcInstant
    original_approved_by: Identity
    original_approved_at: UtcInstant
    content_hash: str = ""

    @model_validator(mode="after")
    def require_original_mapping(self) -> "HistoricalPolicyMapping":
        try:
            raw = base64.b64decode(self.raw_original_base64, validate=True)
        except ValueError as exc:
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_RAW_INVALID") from exc
        if (
            not raw
            or len(raw) > 2_000_000
            or base64.b64encode(raw).decode() != self.raw_original_base64
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_RAW_INVALID")
        if "sha256:" + hashlib.sha256(raw).hexdigest() != self.reference.raw_digest:
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_RAW_MISMATCH")
        self.policy = ResolvedMonthlyPolicy.model_validate(self.policy.model_dump(mode="json"))
        proposed, approved = (
            datetime.fromisoformat(self.original_proposed_at),
            datetime.fromisoformat(self.original_approved_at),
        )
        first, _ = month_window(self.policy.month)
        if proposed > approved or approved.date().isoformat() >= first:
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_ORIGINAL_CLOCK_INVALID")
        if self.original_proposed_by == self.original_approved_by:
            raise ValueError("COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN")
        keys = [
            (item.product_name, item.product_version, item.revision) for item in self.attachments
        ]
        if keys != sorted(set(keys)):
            raise ValueError("COMPOSITE_ELIGIBILITY_ATTACHMENTS_NONCANONICAL")
        bind_historical_content(self)
        return self


class HistoricalPolicyVerificationRequest(StrictAuthorityModel):
    product_name: Literal["CompositeHistoricalPolicyVerificationRequest"] = (
        "CompositeHistoricalPolicyVerificationRequest"
    )
    product_version: Literal["v1"] = "v1"
    purpose: Literal["COMPOSITE_HISTORICAL_MONTHLY_POLICY_ADMISSION"] = (
        "COMPOSITE_HISTORICAL_MONTHLY_POLICY_ADMISSION"
    )
    operation: Literal[
        "POLICY_PROPOSAL", "POLICY_APPROVAL", "EVALUATION_PROPOSAL", "EVALUATION_APPROVAL"
    ]
    reference: HistoricalPolicyReference
    scope: MonthlyPolicyScope
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    eligibility_policy_version: Identity
    reporting_currency: str = Field(pattern=r"^[A-Z]{3}$")
    revision: Identity
    actor_id: Identity
    requested_at: UtcInstant
    intent_digest: Digest


class HistoricalPolicyVerification(HistoricalContent):
    """Only a trusted server port may supply this independently verified mapping."""

    product_name: Literal["CompositeHistoricalPolicyVerification"] = (
        "CompositeHistoricalPolicyVerification"
    )
    product_version: Literal["v1"] = "v1"
    posture: Literal["SYNTHETIC_NON_CERTIFYING", "QUALIFIED_RECEIPT"]
    original_signature_status: Literal["VERIFIED_AT_ORIGINAL_APPROVAL"]
    current_revocation_status: Literal["CLEAR"]
    request: HistoricalPolicyVerificationRequest
    mapping: HistoricalPolicyMapping
    verifier_id: Identity
    signer_principal_id: Identity
    verifier_principal_id: Identity
    configuration_digest: Digest
    signer_key_digest: Digest
    verifier_key_digest: Digest
    verifier_public_key_base64: str = Field(min_length=44, max_length=44)
    revocation_revision: Identity
    revocation_digest: Digest
    checked_at: UtcInstant
    expires_at: UtcInstant
    admitted_at: UtcInstant
    verifier_credential: str = Field(min_length=1, max_length=16384)
    content_hash: str = ""

    @model_validator(mode="after")
    def require_exact_mapping_and_admission(self) -> "HistoricalPolicyVerification":
        self.mapping = HistoricalPolicyMapping.model_validate(self.mapping.model_dump(mode="json"))
        request, mapping = self.request, self.mapping
        if (
            request.reference,
            request.scope,
            request.month,
            request.eligibility_policy_version,
            request.reporting_currency,
        ) != (
            mapping.reference,
            mapping.policy.scope,
            mapping.policy.month,
            mapping.eligibility_policy_version,
            mapping.reporting_currency,
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_MAPPING_MISMATCH")
        if (
            self.signer_principal_id == self.verifier_principal_id
            or self.signer_key_digest == self.verifier_key_digest
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_INDEPENDENCE_REQUIRED")
        checked, admitted, expiry = map(
            datetime.fromisoformat, (self.checked_at, self.admitted_at, self.expires_at)
        )
        requested = datetime.fromisoformat(request.requested_at)
        if requested < datetime.fromisoformat(mapping.original_approved_at):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_ORIGINAL_CLOCK_INVALID")
        if not checked <= requested <= admitted < expiry or expiry > checked + timedelta(minutes=5):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_ADMISSION_WINDOW_INVALID")
        self.require_verifier_signature()
        bind_historical_content(self)
        return self

    def require_verifier_signature(self) -> None:
        try:
            key = base64.b64decode(self.verifier_public_key_base64, validate=True)
            if "sha256:" + hashlib.sha256(key).hexdigest() != self.verifier_key_digest:
                raise ValueError("verifier key digest differs")
            credential = base64.b64decode(self.verifier_credential, validate=True)
            unsigned = self.model_dump(mode="json", exclude={"content_hash", "verifier_credential"})
            Ed25519PublicKey.from_public_bytes(key).verify(
                credential, hash_canonical_payload(unsigned).encode()
            )
        except (ValueError, InvalidSignature) as exc:
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_VERIFIER_SIGNATURE_INVALID") from exc


class HistoricalPolicyTrust(StrictAuthorityModel):
    tenant_id: Identity
    signing_contract: Identity
    signer_principal_id: Identity
    verifier_principal_id: Identity
    signer_key_digest: Digest
    verifier_key_digest: Digest
    configuration_digest: Digest
    posture: Literal["SYNTHETIC_NON_CERTIFYING", "QUALIFIED_RECEIPT"]


class HistoricalPolicyAdmissionPort(Protocol):
    @property
    def trust(self) -> HistoricalPolicyTrust | None: ...

    def verify(
        self, request: HistoricalPolicyVerificationRequest
    ) -> HistoricalPolicyVerification | None:
        """Verify actual original format and return independently attested normalized mapping."""


class UnavailableHistoricalPolicyAdmission:
    trust: HistoricalPolicyTrust | None = None

    def verify(
        self, request: HistoricalPolicyVerificationRequest
    ) -> HistoricalPolicyVerification | None:
        return None


def admitted_historical_policy(
    port: HistoricalPolicyAdmissionPort, request: HistoricalPolicyVerificationRequest
) -> HistoricalPolicyVerification:
    result = port.verify(request)
    if result is None:
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_ADMISSION_UNAVAILABLE")
    result = HistoricalPolicyVerification.model_validate(result.model_dump(mode="json"))
    if result.request != request:
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_REQUEST_MISMATCH")
    trust = port.trust
    if trust is None or (
        trust.tenant_id,
        trust.signing_contract,
        trust.signer_principal_id,
        trust.verifier_principal_id,
        trust.signer_key_digest,
        trust.verifier_key_digest,
        trust.configuration_digest,
        trust.posture,
    ) != (
        request.scope.tenant_id,
        request.reference.signing_contract,
        result.signer_principal_id,
        result.verifier_principal_id,
        result.signer_key_digest,
        result.verifier_key_digest,
        result.configuration_digest,
        result.posture,
    ):
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_TRUST_MISMATCH")
    return result


class HistoricalMonthlyPolicyProposal(HistoricalContent):
    product_name: Literal["CompositeMonthlyPolicyProposal"] = "CompositeMonthlyPolicyProposal"
    product_version: Literal["v2"] = "v2"
    proposal_revision: Identity
    eligibility_policy_version: Identity
    policy: ResolvedMonthlyPolicy
    attachments: list[EvidenceBinding] = Field(min_length=1, max_length=20)
    proposed_by: Identity
    proposed_at: UtcInstant
    verification: HistoricalPolicyVerification
    content_hash: str = ""

    @model_validator(mode="after")
    def require_present_admission(self) -> "HistoricalMonthlyPolicyProposal":
        proof = HistoricalPolicyVerification.model_validate(
            self.verification.model_dump(mode="json")
        )
        request, mapping = proof.request, proof.mapping
        if (self.policy, self.attachments, self.eligibility_policy_version) != (
            mapping.policy,
            mapping.attachments,
            mapping.eligibility_policy_version,
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_MAPPING_MISMATCH")
        if (request.operation, request.revision, request.actor_id, request.requested_at) != (
            "POLICY_PROPOSAL",
            self.proposal_revision,
            self.proposed_by,
            self.proposed_at,
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_REQUEST_MISMATCH")
        expected = hash_canonical_payload(
            {
                "reference": mapping.reference.model_dump(mode="json"),
                "proposal_revision": self.proposal_revision,
            }
        )
        if request.intent_digest != expected:
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_INTENT_MISMATCH")
        bind_historical_content(self)
        return self


class HistoricalMonthlyPolicyApproval(HistoricalContent):
    product_name: Literal["CompositeMonthlyPolicyApproval"] = "CompositeMonthlyPolicyApproval"
    product_version: Literal["v2"] = "v2"
    evidence_kind: Literal["VERIFIED_HISTORICAL_MAPPING"] = "VERIFIED_HISTORICAL_MAPPING"
    official_activation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    proposal: HistoricalMonthlyPolicyProposal
    approved_by: Identity
    approved_at: UtcInstant
    verification: HistoricalPolicyVerification
    content_hash: str = ""

    @model_validator(mode="after")
    def require_independent_current_approval(self) -> "HistoricalMonthlyPolicyApproval":
        self.proposal = HistoricalMonthlyPolicyProposal.model_validate(
            self.proposal.model_dump(mode="json")
        )
        proof = HistoricalPolicyVerification.model_validate(
            self.verification.model_dump(mode="json")
        )
        request = proof.request
        if self.approved_by == self.proposal.proposed_by:
            raise ValueError("COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN")
        if datetime.fromisoformat(self.approved_at) < datetime.fromisoformat(
            self.proposal.proposed_at
        ):
            raise ValueError("COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL")
        if proof.mapping != self.proposal.verification.mapping or (
            request.operation,
            request.revision,
            request.actor_id,
            request.requested_at,
            request.intent_digest,
        ) != (
            "POLICY_APPROVAL",
            self.proposal.proposal_revision,
            self.approved_by,
            self.approved_at,
            self.proposal.content_hash,
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_REQUEST_MISMATCH")
        bind_historical_content(self)
        return self
