"""Deployment-owned source locations and issuer keys; requests cannot select trust."""

import ipaddress
import base64
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from src.core.composite_authority_models import Identity
from src.core.composite_eligibility.verification import VerificationPurpose

SourceOperation = Literal["candidates", "observations", "verification"]


class SourceKey(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kid: Identity
    kty: Literal["OKP"] = "OKP"
    crv: Literal["Ed25519"] = "Ed25519"
    alg: Literal["EdDSA"] = "EdDSA"
    x: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    revoked: bool = False

    @field_validator("x")
    @classmethod
    def require_canonical_key(cls, value: str) -> str:
        raw = base64.urlsafe_b64decode(value + "=")
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != value:
            raise ValueError("COMPOSITE_SOURCE_KEY_NONCANONICAL")
        return value


class SourceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: SourceOperation
    tenant_id: Identity
    owner_service: Identity
    endpoint: str = Field(min_length=1, max_length=2048)
    issuer: str = Field(min_length=1, max_length=256)
    receipt_issuer_id: Identity | None = None
    principal_id: Identity
    credential_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    keys: tuple[SourceKey, ...] = Field(min_length=1, max_length=8)
    revoked_credentials: tuple[Identity, ...] = ()
    revoked_subjects: tuple[Identity, ...] = ()
    evidence_posture: Literal["SYNTHETIC_NON_CERTIFYING", "QUALIFIED_RECEIPT"]
    verification_purposes: tuple[VerificationPurpose, ...] = ()
    allow_local_http: bool = False

    @model_validator(mode="after")
    def require_verifier_binding(self) -> "SourceBinding":
        if self.evidence_posture == "QUALIFIED_RECEIPT" and self.operation != "verification":
            raise ValueError("COMPOSITE_SOURCE_QUALIFIED_OPERATION_FORBIDDEN")
        if not urlsplit(self.issuer).scheme:
            raise ValueError("COMPOSITE_SOURCE_ISSUER_URI_REQUIRED")
        if (self.operation == "verification") != (self.receipt_issuer_id is not None):
            raise ValueError("COMPOSITE_SOURCE_RECEIPT_ISSUER_INVALID")
        if (self.operation == "verification") != bool(self.verification_purposes):
            raise ValueError("COMPOSITE_SOURCE_VERIFICATION_PURPOSES_INVALID")
        if len(set(self.verification_purposes)) != len(self.verification_purposes):
            raise ValueError("COMPOSITE_SOURCE_VERIFICATION_PURPOSES_INVALID")
        return self

    @model_validator(mode="after")
    def require_pinned_transport(self) -> "SourceBinding":
        url = urlsplit(self.endpoint)
        if not url.hostname or any((url.username, url.password, url.fragment, url.query)):
            raise ValueError("COMPOSITE_SOURCE_ENDPOINT_INVALID")
        local = False
        try:
            local = ipaddress.ip_address(url.hostname).is_loopback
        except ValueError:
            pass
        if url.scheme != "https" and not (
            url.scheme == "http"
            and local
            and self.allow_local_http
            and self.evidence_posture == "SYNTHETIC_NON_CERTIFYING"
        ):
            raise ValueError("COMPOSITE_SOURCE_TLS_REQUIRED")
        if len({key.kid for key in self.keys}) != len(self.keys):
            raise ValueError("COMPOSITE_SOURCE_DUPLICATE_KEY")
        return self


class CompositeSourceConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    bindings: tuple[SourceBinding, ...] = Field(min_length=1, max_length=60)
    timeout_seconds: float = Field(default=2, ge=0.1, le=30)
    attempts: int = Field(default=1, ge=1, le=3)
    maximum_response_bytes: int = Field(default=2_000_000, ge=1024, le=8_000_000)

    @model_validator(mode="after")
    def require_unique_independent_bindings(self) -> "CompositeSourceConfiguration":
        pairs = [(item.tenant_id, item.operation) for item in self.bindings]
        if len(set(pairs)) != len(pairs):
            raise ValueError("COMPOSITE_SOURCE_DUPLICATE_BINDING")
        for verifier in (item for item in self.bindings if item.operation == "verification"):
            sources = [
                item
                for item in self.bindings
                if item.tenant_id == verifier.tenant_id and item.operation != "verification"
            ]
            if any(
                item.principal_id == verifier.principal_id
                or {key.x for key in item.keys} & {key.x for key in verifier.keys}
                for item in sources
            ):
                raise ValueError("COMPOSITE_SOURCE_VERIFIER_NOT_INDEPENDENT")
        return self

    def binding(self, tenant_id: str, operation: SourceOperation) -> SourceBinding | None:
        return next(
            (
                item
                for item in self.bindings
                if (item.tenant_id, item.operation) == (tenant_id, operation)
            ),
            None,
        )
