"""Independent current admission of source-signed controlled originals; no source signer custody."""

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.controlled_scenario import (
    ControlledScenarioVerification,
    ControlledScenarioVerificationRequest,
)
from src.core.composite_eligibility.historical_policy import (
    HistoricalPolicyTrust,
    HistoricalPolicyVerificationRequest,
)
from src.infrastructure.composites.controlled_original_policy import verified_controlled_original
from src.infrastructure.composites.native_source_configuration import (
    NativeHistoricalConfiguration,
    key_digest,
    read_custody_file,
)


@dataclass(frozen=True)
class NativeControlledHistoricalVerifier:
    configuration: NativeHistoricalConfiguration

    @property
    def trust(self) -> HistoricalPolicyTrust:
        return self.configuration.trust

    def verify(
        self, request: HistoricalPolicyVerificationRequest | ControlledScenarioVerificationRequest
    ) -> ControlledScenarioVerification:
        configuration = NativeHistoricalConfiguration.model_validate(
            self.configuration.model_dump(mode="json")
        )
        now = datetime.now(UTC)
        request = ControlledScenarioVerificationRequest.model_validate(
            request.model_dump(mode="json")
        )
        self._require_current_request(configuration, request, now)
        mapping = verified_controlled_original(configuration, request, now)
        if (
            mapping.policy.scope,
            mapping.policy.month,
            mapping.eligibility_policy_version,
            mapping.reporting_currency,
        ) != (
            request.scope,
            request.month,
            request.eligibility_policy_version,
            request.reporting_currency,
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_MAPPING_MISMATCH")
        private = Ed25519PrivateKey.from_private_bytes(
            read_custody_file(Path(configuration.verifier_key_file), 32, secret=True)
        )
        public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        if key_digest(public) != self.trust.verifier_key_digest:
            raise ValueError("COMPOSITE_NATIVE_VERIFIER_KEY_MISMATCH")
        admitted = datetime.now(UTC)
        self._require_current_request(configuration, request, admitted)
        wire = {
            "product_name": "CompositeHistoricalPolicyVerification",
            "product_version": "v2",
            "posture": "SYNTHETIC_NON_CERTIFYING",
            "original_signature_status": "VERIFIED_AT_ACTUAL_ISSUANCE",
            "signature_semantics": "SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE",
            "current_revocation_status": "CLEAR",
            "request": request.model_dump(mode="json"),
            "mapping": mapping.model_dump(mode="json"),
            "verifier_id": configuration.verifier_id,
            "signer_principal_id": self.trust.signer_principal_id,
            "verifier_principal_id": self.trust.verifier_principal_id,
            "configuration_digest": self.trust.configuration_digest,
            "signer_key_digest": self.trust.signer_key_digest,
            "verifier_key_digest": self.trust.verifier_key_digest,
            "verifier_public_key_base64": base64.b64encode(public).decode(),
            "revocation_revision": configuration.revocation.revision,
            "revocation_digest": hash_canonical_payload(
                configuration.revocation.model_dump(mode="json")
            ),
            "checked_at": configuration.revocation.checked_at,
            "expires_at": configuration.revocation.expires_at,
            "admitted_at": admitted.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        }
        credential = private.sign(hash_canonical_payload(wire).encode())
        return ControlledScenarioVerification.model_validate(
            {**wire, "verifier_credential": base64.b64encode(credential).decode()}
        )

    @staticmethod
    def _require_current_request(
        configuration: NativeHistoricalConfiguration,
        request: ControlledScenarioVerificationRequest,
        now: datetime,
    ) -> None:
        trust, revoked = configuration.trust, configuration.revocation
        if (
            request.scope.tenant_id != trust.tenant_id
            or request.reference.signing_contract != configuration.adapter
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_TRUST_MISMATCH")
        revoked.require_current(datetime.fromisoformat(request.requested_at), now)
        if (
            {trust.signer_principal_id, trust.verifier_principal_id}
            & set(revoked.revoked_principals)
            or {trust.signer_key_digest, trust.verifier_key_digest}
            & set(revoked.revoked_key_digests)
            or request.reference.raw_digest in revoked.revoked_original_digests
        ):
            raise ValueError("COMPOSITE_NATIVE_HISTORICAL_REVOKED")
