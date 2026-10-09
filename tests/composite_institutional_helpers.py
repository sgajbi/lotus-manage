"""Controlled keys/artifacts for verification mechanism tests; never bank or native-history proof."""

import base64
import json
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.core.composite_definition_versions import DpmCompositeDefinitionV2
from src.core.composite_eligibility.institutional_verification import (
    InstitutionalAttestationArtifact,
)
from src.core.composite_eligibility.staged_publication import institutional_finalization_request
from src.infrastructure.composites.institutional_configuration import (
    InstitutionalVerificationConfiguration,
)
from tests.composite_authority_helpers import independent_digest
from tests.composite_staged_eligibility_helpers import finalization_material


def encoded(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def utc(value):
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def sign_artifact(key, binding, request, payload, *, at=None, change=None, header_change=None):
    """Independent test writer over exact compact bytes and independently computed digests."""
    instant = (at or datetime.now(timezone.utc)).timestamp()
    claims = dict(
        iss=binding.issuer,
        aud="lotus-manage",
        sub=binding.principal_id,
        tenant=binding.tenant_id,
        principal_kind="service",
        jti="controlled-credential",
        nbf=int(instant) - 1,
        exp=int(instant) + 120,
        operation=binding.operation,
        evidence_posture=binding.evidence_posture,
        request_digest=independent_digest(request),
        payload_digest=independent_digest(payload),
    ) | (change or {})
    header = dict(alg="EdDSA", kid="controlled-key", typ="JWT") | (header_change or {})
    segments = [
        encoded(json.dumps(item, separators=(",", ":")).encode()) for item in (header, claims)
    ]
    signing_input = ".".join(segments)
    return signing_input + "." + encoded(key.sign(signing_input.encode("ascii")))


def institutional_material():
    subject, controls, finalization = finalization_material()
    approval = controls[-1]
    wire = finalization.definition.model_dump(mode="json")
    claims = wire["authority_approval"]["claims"]
    claims["schema_version"] = "composite-authority-approval-claims.v1"
    request_binding = dict(
        product_name=subject.product_name,
        product_version="v1",
        revision=subject.subject_revision,
        digest=subject.content_hash,
    )
    approval_binding = dict(
        product_name=approval.product_name,
        product_version="v1",
        revision=approval.proposal.evaluation_revision,
        digest=approval.content_hash,
    )
    artifact = InstitutionalAttestationArtifact(
        issuer_id="controlled-original-issuer",
        attestation_id="controlled-attestation",
        revision="controlled-original.r1",
        claims=claims,
        subject_binding=request_binding,
        evaluation_approval_binding=approval_binding,
    )
    wire["authority_approval"] = dict(
        evidence_kind="INSTITUTIONAL_ATTESTATION_REFERENCE",
        claims=claims,
        official_activation="UNAVAILABLE",
        attestation=dict(
            contract_version="composite-authority-attestation.v1",
            issuer_id=artifact.issuer_id,
            attestation_id=artifact.attestation_id,
            revision=artifact.revision,
            digest=artifact.content_hash,
        ),
    )
    wire["content_hash"] = independent_digest(
        {name: value for name, value in wire.items() if name != "content_hash"}
    )
    definition = DpmCompositeDefinitionV2.model_validate(wire)
    return (
        subject,
        controls,
        definition,
        artifact,
        institutional_finalization_request(definition, subject, approval),
    )


def configuration_material():
    source, verifier = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    now = datetime.now(timezone.utc)

    def keys(key):
        return [
            dict(
                kid="controlled-key",
                x=encoded(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
            )
        ]

    configuration = InstitutionalVerificationConfiguration.model_validate(
        dict(
            verifier=dict(
                operation="verification",
                tenant_id="synthetic-tenant",
                owner_service="controlled-verifier",
                endpoint="https://controlled-verifier.test/verification",
                issuer="urn:controlled:verifier",
                receipt_issuer_id="controlled-verifier-issuer",
                principal_id="controlled-verifier",
                credential_env="CONTROLLED_779_CREDENTIAL",
                keys=keys(verifier),
                revoked_credentials=[],
                revoked_subjects=[],
                evidence_posture="QUALIFIED_RECEIPT",
                verification_purposes=[
                    "COMPOSITE_ECONOMIC_AUTHORITY_PROFILE",
                    "RETURN_METHOD_CALENDAR",
                    "PROVIDER_REGISTRATION",
                ],
            ),
            signer=dict(
                tenant_id="synthetic-tenant",
                issuer="urn:controlled:original",
                issuer_id="controlled-original-issuer",
                principal_id="controlled-original-signer",
                keys=keys(source),
                revoked_credentials=[],
                revoked_subjects=[],
            ),
            revocation=dict(
                revision="controlled-revocation.r1",
                checked_at=utc(now - timedelta(seconds=1)),
                expires_at=utc(now + timedelta(seconds=120)),
                revoked_artifact_digests=[],
            ),
        )
    )
    return configuration, source, verifier


def authority_result(configuration, signer, request, artifact):
    original = sign_artifact(
        signer,
        configuration.signer,
        dict(attestation_id=artifact.attestation_id, revision=artifact.revision),
        artifact.model_dump(mode="json"),
        at=datetime.fromisoformat(artifact.claims.approved_at),
    )
    return dict(
        product_name="CompositeInstitutionalVerificationResult",
        product_version="v2",
        posture="QUALIFIED_RECEIPT",
        request=request.model_dump(mode="json"),
        artifact=artifact.model_dump(mode="json"),
        original_credential=original,
        verifier_id=configuration.verifier.principal_id,
        issuer_id=configuration.verifier.receipt_issuer_id,
    )
