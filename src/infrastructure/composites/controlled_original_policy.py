"""One signed synthetic scenario format; actual issuance is never historical bank approval."""

import base64
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import Field

from src.core.composite_authority_models import EvidenceBinding, Identity, StrictAuthorityModel
from src.core.composite_eligibility.controlled_scenario import (
    ControlledScenarioPolicyMapping,
    ControlledScenarioVerificationRequest,
)
from src.core.composite_eligibility.observations import UtcInstant
from src.core.composite_eligibility.policy import ResolvedMonthlyPolicy
from src.infrastructure.composites.native_source_configuration import (
    NativeHistoricalConfiguration,
    public_key_bytes,
    read_custody_file,
    strict_controlled_json,
)


class ControlledPolicyOriginal(StrictAuthorityModel):
    format: Literal["CONTROLLED_SYNTHETIC_POLICY_V1"]
    posture: Literal["SYNTHETIC_NON_CERTIFYING"]
    purpose: Literal["COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION"]
    signature_semantics: Literal["SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE"]
    issuer_id: Identity
    artifact_id: Identity
    revision: Identity
    signer_principal_id: Identity
    actual_issued_at: UtcInstant
    policy: ResolvedMonthlyPolicy
    eligibility_policy_version: Identity
    reporting_currency: str = Field(pattern=r"^[A-Z]{3}$")
    attachments: list[EvidenceBinding] = Field(min_length=1, max_length=20)
    scenario_proposed_by: Identity
    scenario_proposed_at: UtcInstant
    scenario_approved_by: Identity
    scenario_approved_at: UtcInstant


class ControlledPolicyEnvelope(StrictAuthorityModel):
    raw_original_base64: str = Field(min_length=4, max_length=2_800_000)
    original_credential: str = Field(min_length=88, max_length=88)


def verified_controlled_original(
    configuration: NativeHistoricalConfiguration,
    request: ControlledScenarioVerificationRequest,
    now: datetime,
) -> ControlledScenarioPolicyMapping:
    location = Path(configuration.originals_directory) / (
        request.reference.raw_digest[7:] + ".json"
    )
    envelope = ControlledPolicyEnvelope.model_validate(
        strict_controlled_json(read_custody_file(location, 2_810_000))
    )
    raw = base64.b64decode(envelope.raw_original_base64, validate=True)
    if (
        not raw
        or len(raw) > 2_000_000
        or ("sha256:" + hashlib.sha256(raw).hexdigest() != request.reference.raw_digest)
    ):
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_RAW_MISMATCH")
    _verify_source_signature(configuration, envelope, raw)
    original = ControlledPolicyOriginal.model_validate(strict_controlled_json(raw))
    _require_original_identity(configuration, request, original, now)
    return ControlledScenarioPolicyMapping(
        reference=request.reference,
        actual_issued_at=original.actual_issued_at,
        raw_original_base64=envelope.raw_original_base64,
        original_credential=envelope.original_credential,
        policy=original.policy,
        eligibility_policy_version=original.eligibility_policy_version,
        reporting_currency=original.reporting_currency,
        attachments=original.attachments,
        scenario_proposed_by=original.scenario_proposed_by,
        scenario_proposed_at=original.scenario_proposed_at,
        scenario_approved_by=original.scenario_approved_by,
        scenario_approved_at=original.scenario_approved_at,
    )


def _verify_source_signature(
    configuration: NativeHistoricalConfiguration, envelope: ControlledPolicyEnvelope, raw: bytes
) -> None:
    try:
        signature = base64.b64decode(envelope.original_credential, validate=True)
        if base64.b64encode(signature).decode() != envelope.original_credential:
            raise ValueError("Noncanonical signature")
        Ed25519PublicKey.from_public_bytes(
            public_key_bytes(configuration.source_public_key_base64)
        ).verify(signature, raw)
    except (ValueError, InvalidSignature) as exc:
        raise ValueError("COMPOSITE_NATIVE_ORIGINAL_SIGNATURE_INVALID") from exc


def _require_original_identity(
    configuration: NativeHistoricalConfiguration,
    request: ControlledScenarioVerificationRequest,
    original: ControlledPolicyOriginal,
    now: datetime,
) -> None:
    if (
        original.issuer_id,
        original.artifact_id,
        original.revision,
        original.format,
        original.signer_principal_id,
    ) != (
        request.reference.issuer_id,
        request.reference.artifact_id,
        request.reference.revision,
        request.reference.signing_contract,
        configuration.trust.signer_principal_id,
    ):
        raise ValueError("COMPOSITE_NATIVE_ORIGINAL_IDENTITY_MISMATCH")
    issued = datetime.fromisoformat(original.actual_issued_at)
    if not (
        datetime.fromisoformat(configuration.source_key_valid_from)
        <= issued
        < datetime.fromisoformat(configuration.source_key_valid_to)
        and datetime.fromisoformat(original.scenario_approved_at) <= issued <= now
        and issued <= datetime.fromisoformat(request.requested_at)
    ):
        raise ValueError("COMPOSITE_NATIVE_ORIGINAL_ISSUANCE_INVALID")
