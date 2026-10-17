"""Closed deployment composition for controlled native monthly evidence only."""

import base64
from pathlib import Path
from typing import Literal, Self

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import Field, model_validator

from src.infrastructure.composites.controlled_assembly_verifier import (
    ControlledAssemblyVerifierConfiguration,
)
from src.infrastructure.composites.core_financial_configuration import (
    ClosedSourceModel,
    CoreFinancialConfiguration,
    CoreReaderConfiguration,
)
from src.infrastructure.composites.core_source_authentication import (
    CoreSourceAuthenticationPolicy,
)
from src.infrastructure.composites.native_source_configuration import read_custody_file
from src.infrastructure.composites.source_configuration import (
    CompositeSourceConfiguration,
    SourceBinding,
)


class NativeAssemblyConfiguration(ClosedSourceModel):
    """No secret values or caller-selected trust; A and C rebuild the same financial cut."""

    adapter: Literal["CONTROLLED_SYNTHETIC_NATIVE_ASSEMBLY_V2"]
    financial: CoreFinancialConfiguration
    reader: CoreReaderConfiguration
    verification: ControlledAssemblyVerifierConfiguration
    assembly_authorization: CoreSourceAuthenticationPolicy
    verification_authorization: CoreSourceAuthenticationPolicy
    verifier_key_file: str = Field(min_length=1, max_length=2048)
    timeout_seconds: float = Field(default=2, ge=0.1, le=30)
    policy_verification: CompositeSourceConfiguration | None = None

    @model_validator(mode="after")
    def require_matching_deployment_policies(self) -> Self:
        if self.financial != self.verification.financial:
            raise ValueError("COMPOSITE_NATIVE_FINANCIAL_CONFIGURATION_MISMATCH")
        for reader, authorization in (
            (self.reader, self.assembly_authorization),
            (self.verification.reader, self.verification_authorization),
        ):
            _require_reader_authorization(reader, authorization, self.financial.tenant_id)
        if not Path(self.verifier_key_file).is_absolute():
            raise ValueError("COMPOSITE_NATIVE_SIGNER_PATH_INVALID")
        if self.policy_verification is not None:
            self._require_separate_policy_channel()
        return self

    def _require_separate_policy_channel(self) -> None:
        assert self.policy_verification is not None
        for binding in self.policy_verification.bindings:
            self._require_policy_binding(binding)

    def _require_policy_binding(self, binding: SourceBinding) -> None:
        trust = self.verification.trust
        if (
            binding.operation != "verification"
            or binding.tenant_id != self.financial.tenant_id
            or binding.evidence_posture != "SYNTHETIC_NON_CERTIFYING"
            or "COMPOSITE_MONTHLY_SOURCE_CUT" in binding.verification_purposes
            or binding.principal_id in (*trust.source_principal_ids, trust.principal_id)
            or {key.x for key in binding.keys}
            & {key.x for key in (*trust.source_keys, trust.verifier_key)}
        ):
            raise ValueError("COMPOSITE_NATIVE_POLICY_CHANNEL_NOT_SEPARATE")


def _require_reader_authorization(
    reader: CoreReaderConfiguration, authorization: CoreSourceAuthenticationPolicy, tenant_id: str
) -> None:
    if (
        reader.tenant_id != tenant_id
        or reader.tenant_id != authorization.tenant_id
        or httpx.URL(reader.endpoint) != httpx.URL(authorization.origin)
        or reader.authentication_mode != "core_enterprise_hmac_v1"
        or reader.credential_env != authorization.credential_env
        or reader.allow_local_http != authorization.allow_local_http
    ):
        raise ValueError("COMPOSITE_NATIVE_READER_AUTH_CONFIGURATION_MISMATCH")


def native_monthly_signer(configuration: NativeAssemblyConfiguration) -> Ed25519PrivateKey | None:
    """Missing mounted custody is unavailable; unsafe or mismatched custody refuses."""
    try:
        raw = read_custody_file(Path(configuration.verifier_key_file), 32, secret=True)
    except ValueError as exc:
        if str(exc) == "COMPOSITE_NATIVE_CUSTODY_UNAVAILABLE":
            return None
        raise
    if len(raw) != 32:
        raise ValueError("COMPOSITE_NATIVE_SIGNER_SIZE_INVALID")
    signer = Ed25519PrivateKey.from_private_bytes(raw)
    public = base64.urlsafe_b64encode(signer.public_key().public_bytes_raw()).rstrip(b"=").decode()
    if public != configuration.verification.trust.verifier_key.x:
        raise ValueError("COMPOSITE_NATIVE_SIGNER_MISMATCH")
    return signer
