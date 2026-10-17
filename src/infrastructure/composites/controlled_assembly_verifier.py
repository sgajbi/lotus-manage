"""Fresh controlled monthly admission under independently provisioned deployment trust.

This internal adapter is inactive without configuration and a matching signer. D owns
authenticated Core client composition, operator trust and secret lifecycle; synthetic
proofs here confer no supplier, bank, financial or production authority.
"""

from __future__ import annotations

import base64
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Self
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import Field, model_validator

from src.core.common.artifact_credentials import verified_artifact
from src.core.common.canonical import canonical_json, hash_canonical_payload
from src.core.composite_authority_models import Digest, Identity
from src.core.composite_eligibility.native_source_custody import NativeInstant
from src.core.composite_eligibility.native_source_verification import (
    MonthlySourceAdmissionContext,
    MonthlySourceAdmissionProof,
    MonthlySourceVerificationResult,
    MonthlySourceVerifierKey,
    NativeAssemblyVerification,
)
from src.core.composite_eligibility.policy import MonthlyPolicyScope, month_window
from src.core.composite_eligibility.source import MonthlyEligibilitySourceRequest
from src.core.composite_eligibility.source_assembly import assembly_verification_request
from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest
from src.infrastructure.composites.core_financial_configuration import (
    ClosedSourceModel,
    CoreFinancialConfiguration,
    CoreReaderConfiguration,
)
from src.infrastructure.composites.core_financial_sources import CoreMonthlyEligibilitySource
from src.infrastructure.composites.core_source_reader import CoreHttpRetainedReader
from src.infrastructure.composites.native_source_configuration import key_digest
from src.infrastructure.composites.source_configuration import SourceKey


def current_utc_time() -> datetime:
    return datetime.now(UTC)


def _raw_key(key: SourceKey) -> bytes:
    return base64.urlsafe_b64decode(key.x + "=")


class ControlledAssemblyVerifierTrust(ClosedSourceModel):
    tenant_id: Identity
    issuer: str = Field(min_length=1, max_length=256)
    receipt_issuer_id: Identity
    principal_id: Identity
    audience: Literal["lotus-manage"]
    purpose: Literal["COMPOSITE_MONTHLY_SOURCE_CUT"]
    operation: Literal["verification"]
    evidence_posture: Literal["SYNTHETIC_NON_CERTIFYING"]
    verifier_key: SourceKey
    key_valid_from: NativeInstant
    key_valid_to: NativeInstant
    source_principal_ids: tuple[Identity, ...] = Field(min_length=1, max_length=1000)
    source_keys: tuple[SourceKey, ...] = Field(max_length=1000)

    @model_validator(mode="after")
    def require_independent_trust(self) -> Self:
        principals = self.source_principal_ids
        if (
            not urlsplit(self.issuer).scheme
            or datetime.fromisoformat(self.key_valid_from)
            >= datetime.fromisoformat(self.key_valid_to)
            or len(set(principals)) != len(principals)
            or len({key.kid for key in self.source_keys}) != len(self.source_keys)
        ):
            raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_TRUST_INVALID")
        if self.principal_id in principals or any(
            _raw_key(key) == _raw_key(self.verifier_key) for key in self.source_keys
        ):
            raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_VERIFIER_NOT_INDEPENDENT")
        return self


class ControlledAssemblyRevocationSnapshot(ClosedSourceModel):
    revision: Identity
    checked_at: NativeInstant
    expires_at: NativeInstant
    revoked_credentials: tuple[Identity, ...] = Field(max_length=1000)
    revoked_subjects: tuple[Identity, ...] = Field(max_length=1000)
    revoked_key_digests: tuple[Digest, ...] = Field(max_length=1000)

    @model_validator(mode="after")
    def require_bounded_window(self) -> Self:
        checked, expires = map(datetime.fromisoformat, (self.checked_at, self.expires_at))
        if not checked < expires <= checked + timedelta(minutes=5):
            raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_REVOCATION_WINDOW")
        return self


class ControlledAssemblyVerifierConfiguration(ClosedSourceModel):
    financial: CoreFinancialConfiguration
    reader: CoreReaderConfiguration
    expected_observations_digest: Digest
    trust: ControlledAssemblyVerifierTrust
    revocation: ControlledAssemblyRevocationSnapshot

    @model_validator(mode="after")
    def require_same_tenant(self) -> Self:
        if not self.financial.tenant_id == self.reader.tenant_id == self.trust.tenant_id:
            raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_TENANT_CONFIGURATION")
        return self


@dataclass(frozen=True)
class _CurrentCredentialBinding:
    """Fresh trust comes from configuration, never the proof's retained admission."""

    issuer: str
    principal_id: str
    tenant_id: str
    keys: tuple[SourceKey, ...]
    revoked_credentials: tuple[str, ...]
    revoked_subjects: tuple[str, ...]
    operation: str
    evidence_posture: str


def _binding(config: ControlledAssemblyVerifierConfiguration) -> _CurrentCredentialBinding:
    trust, revocation = config.trust, config.revocation
    return _CurrentCredentialBinding(
        trust.issuer,
        trust.principal_id,
        trust.tenant_id,
        (trust.verifier_key,),
        revocation.revoked_credentials,
        revocation.revoked_subjects,
        trust.operation,
        trust.evidence_posture,
    )


def _require_current(config: ControlledAssemblyVerifierConfiguration, now: datetime) -> None:
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_CLOCK_INVALID")
    trust, revocation = config.trust, config.revocation
    if (
        not datetime.fromisoformat(trust.key_valid_from)
        <= now
        < datetime.fromisoformat(trust.key_valid_to)
    ):
        raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_KEY_WINDOW")
    if (
        not datetime.fromisoformat(revocation.checked_at)
        <= now
        < datetime.fromisoformat(revocation.expires_at)
    ):
        raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_REVOCATION_WINDOW")
    principals = (trust.principal_id, *trust.source_principal_ids)
    keys = (trust.verifier_key, *trust.source_keys)
    if set(principals).intersection(revocation.revoked_subjects) or any(
        key.revoked or key_digest(_raw_key(key)) in revocation.revoked_key_digests for key in keys
    ):
        raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_REVOKED")


def _source_request(
    config: ControlledAssemblyVerifierConfiguration,
) -> MonthlyEligibilitySourceRequest:
    financial = config.financial
    return MonthlyEligibilitySourceRequest(
        scope=MonthlyPolicyScope(
            tenant_id=financial.tenant_id,
            composite_id=financial.composite_id,
            definition_version=financial.definition_version,
            strategy_code=financial.strategy_code,
        ),
        month=financial.month,
        source_cut_id=financial.observation_cut_id,
        owner_service="lotus-manage",
        expected_source_revision=financial.observation_revision,
        expected_content_hash=config.expected_observations_digest,
        expected_portfolio_ids=tuple(member.portfolio_id for member in financial.members),
        reporting_currency=financial.reporting_currency,
    )


def _require_scope(
    config: ControlledAssemblyVerifierConfiguration, request: VerificationRequest
) -> None:
    financial = config.financial
    if (
        request.purpose,
        request.source_product,
        request.tenant_id,
        request.composite_id,
        request.definition_version,
        request.effective_from,
        request.effective_to,
    ) != (
        config.trust.purpose,
        "CompositeMonthlyEligibilityAssembly",
        financial.tenant_id,
        financial.composite_id,
        financial.definition_version,
        *month_window(financial.month),
    ):
        raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_REQUEST_SCOPE")


def _admission(
    config: ControlledAssemblyVerifierConfiguration, now: datetime
) -> MonthlySourceAdmissionContext:
    trust, revocation = config.trust, config.revocation
    key = MonthlySourceVerifierKey.model_validate(trust.verifier_key.model_dump(mode="json"))
    return MonthlySourceAdmissionContext(
        configuration_digest=hash_canonical_payload(config.model_dump(mode="json")),
        issuer=trust.issuer,
        audience=trust.audience,
        principal_id=trust.principal_id,
        tenant_id=trust.tenant_id,
        purpose=trust.purpose,
        operation=trust.operation,
        evidence_posture=trust.evidence_posture,
        verifier_key=key,
        verifier_key_digest=hash_canonical_payload(key.model_dump(mode="json")),
        revocation_revision=revocation.revision,
        revocation_digest=hash_canonical_payload(revocation.model_dump(mode="json")),
        revocation_checked_at=revocation.checked_at,
        revocation_expires_at=revocation.expires_at,
        admitted_at=now.astimezone(UTC).isoformat(),
        current_revocation_status="CLEAR",
    )


def _encoded(document: Any) -> str:
    raw = canonical_json(document).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _credential(
    result: MonthlySourceVerificationResult,
    config: ControlledAssemblyVerifierConfiguration,
    signer: Ed25519PrivateKey,
    now: datetime,
) -> str:
    trust = config.trust
    digests = {
        "request_digest": hash_canonical_payload(result.receipt.request.model_dump(mode="json")),
        "payload_digest": hash_canonical_payload(result.model_dump(mode="json")),
    }
    credential_id = hash_canonical_payload(digests)
    if credential_id in config.revocation.revoked_credentials:
        raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_CREDENTIAL_REVOKED")
    expiry = min(
        math.floor(datetime.fromisoformat(value).timestamp())
        for value in (trust.key_valid_to, config.revocation.expires_at)
    )
    if not math.floor(now.timestamp()) <= now.timestamp() < expiry:
        raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_CREDENTIAL_WINDOW")
    claims = {
        "iss": trust.issuer,
        "aud": trust.audience,
        "sub": trust.principal_id,
        "tenant": trust.tenant_id,
        "principal_kind": "service",
        "jti": credential_id,
        "nbf": math.floor(now.timestamp()),
        "exp": expiry,
        "operation": trust.operation,
        "evidence_posture": trust.evidence_posture,
        **digests,
    }
    signing_input = (
        _encoded({"alg": "EdDSA", "kid": trust.verifier_key.kid, "typ": "JWT"})
        + "."
        + _encoded(claims)
    )
    signature = base64.urlsafe_b64encode(signer.sign(signing_input.encode("ascii"))).rstrip(b"=")
    return signing_input + "." + signature.decode("ascii")


class ControlledAssemblyVerifier:
    """Own each reconstruction and return one immutable receipt/proof pair."""

    def __init__(
        self,
        configuration: ControlledAssemblyVerifierConfiguration | None,
        client: httpx.Client,
        *,
        signer: Ed25519PrivateKey | None = None,
        clock: Callable[[], datetime] = current_utc_time,
    ) -> None:
        self.configuration, self.client = configuration, client
        self.signer, self.clock = signer, clock

    def verify_with_proof(self, request: VerificationRequest) -> NativeAssemblyVerification | None:
        if self.configuration is None or self.signer is None:
            return None
        try:
            config = ControlledAssemblyVerifierConfiguration.model_validate_json(
                self.configuration.model_dump_json(warnings="error"), strict=True
            )
            request = VerificationRequest.model_validate_json(
                request.model_dump_json(warnings="error"), strict=True
            )
        except ValueError as exc:
            raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_CONFIGURATION_OR_REQUEST_INVALID") from exc
        _require_scope(config, request)
        _require_current(config, self.clock())
        if self.signer.public_key().public_bytes_raw() != _raw_key(config.trust.verifier_key):
            raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_SIGNER_MISMATCH")
        reader = CoreHttpRetainedReader(
            config.reader, self.client, members=config.financial.members
        )
        source = CoreMonthlyEligibilitySource(
            config.financial, reader, verifier=None, controlled_synthetic=True
        )
        assembly = source.assemble(_source_request(config))
        if assembly is None:
            return None
        rebuilt = assembly_verification_request(assembly)
        if rebuilt != request:
            raise ValueError("COMPOSITE_NATIVE_ASSEMBLY_REQUEST_MISMATCH")
        now = self.clock()
        _require_current(config, now)
        receipt = VerificationReceipt(
            posture=config.trust.evidence_posture,
            request=rebuilt,
            verifier_id=config.trust.principal_id,
            issuer_id=config.trust.receipt_issuer_id,
            artifact_revision=assembly.observations.source_revision,
            artifact_digest=assembly.native_custody.content_hash,
        )
        result = MonthlySourceVerificationResult(
            receipt=receipt,
            native_custody_digest=assembly.native_custody.content_hash,
            admission=_admission(config, now),
        )
        credential = _credential(result, config, self.signer, now)
        verified_artifact(
            credential,
            binding=_binding(config),
            request=rebuilt.model_dump(mode="json"),
            payload=result.model_dump(mode="json"),
            now=now.timestamp(),
        )
        pair = NativeAssemblyVerification(
            receipt, MonthlySourceAdmissionProof(result=result, verifier_credential=credential)
        )
        current = self.clock()
        _require_current(config, current)
        verified_artifact(
            credential,
            binding=_binding(config),
            request=rebuilt.model_dump(mode="json"),
            payload=result.model_dump(mode="json"),
            now=current.timestamp(),
        )
        return pair
