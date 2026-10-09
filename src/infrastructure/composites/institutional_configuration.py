"""Separate deployment-owned institutional verifier and original-signer trust; no caller grants."""

from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.composite_authority_models import Identity, Digest
from src.core.composite_eligibility.observations import UtcInstant
from src.infrastructure.composites.source_configuration import SourceBinding, SourceKey


class AttestationSignerBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tenant_id: Identity
    issuer: str = Field(min_length=1, max_length=256)
    issuer_id: Identity
    principal_id: Identity
    keys: tuple[SourceKey, ...] = Field(min_length=1, max_length=8)
    revoked_credentials: tuple[Identity, ...]
    revoked_subjects: tuple[Identity, ...]
    operation: Literal["attestation"] = "attestation"
    evidence_posture: Literal["QUALIFIED_RECEIPT"] = "QUALIFIED_RECEIPT"

    @model_validator(mode="after")
    def require_pinned_issuer(self) -> "AttestationSignerBinding":
        if not urlsplit(self.issuer).scheme or len({key.kid for key in self.keys}) != len(
            self.keys
        ):
            raise ValueError("COMPOSITE_ATTESTATION_SIGNER_INVALID")
        return self


class InstitutionalRevocationSnapshot(BaseModel):
    """Deployment supplies current authoritative status, including explicit empty revocations."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    revision: Identity
    checked_at: UtcInstant
    expires_at: UtcInstant
    revoked_artifact_digests: tuple[Digest, ...]

    def require_current(self, now: datetime) -> None:
        checked, expiry = (
            datetime.fromisoformat(self.checked_at),
            datetime.fromisoformat(self.expires_at),
        )
        if not checked <= now < expiry or expiry > checked + timedelta(minutes=5):
            raise ValueError("COMPOSITE_ATTESTATION_REVOCATION_UNAVAILABLE")


class InstitutionalVerificationConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    verifier: SourceBinding
    signer: AttestationSignerBinding
    revocation: InstitutionalRevocationSnapshot
    timeout_seconds: float = Field(default=2, ge=0.1, le=30)
    maximum_response_bytes: int = Field(default=2_000_000, ge=1024, le=8_000_000)

    @model_validator(mode="after")
    def require_independent_qualified_verifier(self) -> "InstitutionalVerificationConfiguration":
        verifier, signer = self.verifier, self.signer
        if (
            verifier.operation != "verification"
            or verifier.evidence_posture != "QUALIFIED_RECEIPT"
            or not {
                "COMPOSITE_ECONOMIC_AUTHORITY_PROFILE",
                "RETURN_METHOD_CALENDAR",
                "PROVIDER_REGISTRATION",
            }
            <= set(verifier.verification_purposes)
            or set(verifier.verification_purposes)
            - {
                "COMPOSITE_ECONOMIC_AUTHORITY_PROFILE",
                "RETURN_METHOD_CALENDAR",
                "PROVIDER_REGISTRATION",
            }
            or verifier.tenant_id != signer.tenant_id
            or verifier.principal_id == signer.principal_id
            or {key.x for key in verifier.keys} & {key.x for key in signer.keys}
            or verifier.allow_local_http
            or not {"revoked_credentials", "revoked_subjects"} <= verifier.model_fields_set
        ):
            raise ValueError("COMPOSITE_ATTESTATION_CONFIGURATION_INVALID")
        return self

    def require_current(self) -> datetime:
        now = datetime.now(timezone.utc)
        self.revocation.require_current(now)
        return now
