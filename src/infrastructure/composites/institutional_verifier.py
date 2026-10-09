"""Independent original-artifact verification plus fresh deployment-pinned admission."""

from dataclasses import dataclass
from datetime import datetime

import httpx

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.institutional_verification import (
    InstitutionalAdmissionProof,
    InstitutionalVerificationRequest,
    InstitutionalVerificationResult,
    InstitutionalVerificationReceipt,
    require_bound_related_artifact,
)
from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest
from src.infrastructure.composites.configured_sources import (
    CompositeSourceTransport,
    ConfiguredCompositeEvidenceVerifier,
)
from src.infrastructure.composites.institutional_configuration import (
    InstitutionalVerificationConfiguration,
)
from src.infrastructure.composites.source_configuration import CompositeSourceConfiguration
from src.infrastructure.composites.source_credentials import verified_artifact


@dataclass(frozen=True)
class ConfiguredInstitutionalEvidenceVerifier:
    configuration: InstitutionalVerificationConfiguration
    client: httpx.Client

    def _transport(self) -> CompositeSourceTransport:
        self.configuration.require_current()
        return CompositeSourceTransport(
            CompositeSourceConfiguration(
                bindings=(self.configuration.verifier,),
                timeout_seconds=self.configuration.timeout_seconds,
                maximum_response_bytes=self.configuration.maximum_response_bytes,
            ),
            self.client,
        )

    def verify_related(self, request: VerificationRequest) -> VerificationReceipt | None:
        if request.purpose not in {"RETURN_METHOD_CALENDAR", "PROVIDER_REGISTRATION"}:
            return None
        result = ConfiguredCompositeEvidenceVerifier(self._transport()).verify(request)
        self.configuration.require_current()
        if result is not None:
            require_bound_related_artifact(result)
            if result.artifact_digest in self.configuration.revocation.revoked_artifact_digests:
                raise ValueError("COMPOSITE_ATTESTATION_RELATED_ARTIFACT_MISMATCH")
        return result

    def verify(
        self, request: InstitutionalVerificationRequest
    ) -> InstitutionalVerificationReceipt | None:
        request = InstitutionalVerificationRequest.model_validate(request.model_dump(mode="json"))
        configuration = self.configuration
        tenant = request.definition.tenant_id
        if tenant != configuration.signer.tenant_id:
            return None
        resolved = self._transport().resolve_signed(
            tenant_id=tenant, operation="verification", request=request.model_dump(mode="json")
        )
        if resolved is None:
            return None
        payload, verifier_credential = resolved
        result = InstitutionalVerificationResult.model_validate(payload)
        if (
            result.request != request
            or result.issuer_id != configuration.verifier.receipt_issuer_id
            or result.verifier_id != configuration.verifier.principal_id
            or result.artifact.issuer_id != configuration.signer.issuer_id
        ):
            raise ValueError("COMPOSITE_ATTESTATION_VERIFIER_SCOPE_MISMATCH")
        now = configuration.require_current()
        artifact = result.artifact
        approved = datetime.fromisoformat(artifact.claims.approved_at)
        if (
            approved > now
            or artifact.content_hash in configuration.revocation.revoked_artifact_digests
        ):
            raise ValueError("COMPOSITE_ATTESTATION_ORIGINAL_UNAVAILABLE")
        # Verify original signed bytes at their preserved approval instant; revocation is CURRENT.
        # A fresh transport signature alone never satisfies this independent original signature.
        verified_artifact(
            result.original_credential,
            binding=configuration.signer,
            request={"attestation_id": artifact.attestation_id, "revision": artifact.revision},
            payload=artifact.model_dump(mode="json"),
            now=approved.timestamp(),
        )
        proof = InstitutionalAdmissionProof(
            configuration_digest=hash_canonical_payload(configuration.model_dump(mode="json")),
            signer_key_digest=hash_canonical_payload(
                [key.model_dump(mode="json") for key in configuration.signer.keys]
            ),
            verifier_key_digest=hash_canonical_payload(
                [key.model_dump(mode="json") for key in configuration.verifier.keys]
            ),
            revocation_revision=configuration.revocation.revision,
            revocation_digest=hash_canonical_payload(
                configuration.revocation.model_dump(mode="json")
            ),
            revocation_checked_at=configuration.revocation.checked_at,
            revocation_expires_at=configuration.revocation.expires_at,
            admitted_at=now.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            verifier_credential=verifier_credential,
        )
        return InstitutionalVerificationReceipt(
            **result.model_dump(mode="json", exclude={"product_name"}), admission=proof
        )
