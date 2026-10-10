"""Explicitly synthetic independent provider; ephemeral keys and observed revocation time."""

import base64
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.historical_policy import (
    HistoricalPolicyMapping,
    HistoricalPolicyTrust,
    HistoricalPolicyVerification,
    HistoricalPolicyVerificationRequest,
)
from src.infrastructure.composites.historical_configuration import HistoricalPolicyConfiguration
from tests.integration.dpm.https_runtime import trusted_https_server


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class ObservedHistoricalProvider:
    def __init__(self, mapping):
        self.signer, self.verifier = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        raw = base64.b64decode(mapping.raw_original_base64)
        wire = mapping.model_dump(mode="json")
        wire["reference"]["signing_contract"] = "CONTROLLED_PROVIDER_RAW_BYTES_V1"
        wire["original_credential"] = base64.b64encode(self.signer.sign(raw)).decode()
        self.mapping = HistoricalPolicyMapping.model_validate(wire | {"content_hash": ""})
        self.trust = HistoricalPolicyTrust(
            tenant_id=mapping.policy.scope.tenant_id,
            signing_contract=self.mapping.reference.signing_contract,
            signer_principal_id="synthetic-original-signer",
            verifier_principal_id="synthetic-independent-provider",
            signer_key_digest=self.key_digest(self.signer),
            verifier_key_digest=self.key_digest(self.verifier),
            configuration_digest=hash_canonical_payload({"controlled": "provider-trust-profile"}),
            posture="SYNTHETIC_NON_CERTIFYING",
        )
        # Observed before requests, not copied/backdated from their requested_at.
        self.checked_at = utc_now()

    @staticmethod
    def key_digest(key):
        return (
            "sha256:"
            + hashlib.sha256(
                key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            ).hexdigest()
        )

    def verify(self, request):
        raw = base64.b64decode(self.mapping.raw_original_base64)
        self.signer.public_key().verify(base64.b64decode(self.mapping.original_credential), raw)
        wire = dict(
            product_name="CompositeHistoricalPolicyVerification",
            product_version="v1",
            posture=self.trust.posture,
            original_signature_status="VERIFIED_AT_ORIGINAL_APPROVAL",
            current_revocation_status="CLEAR",
            request=request.model_dump(mode="json"),
            mapping=self.mapping.model_dump(mode="json"),
            verifier_id="synthetic-provider",
            signer_principal_id=self.trust.signer_principal_id,
            verifier_principal_id=self.trust.verifier_principal_id,
            configuration_digest=self.trust.configuration_digest,
            signer_key_digest=self.trust.signer_key_digest,
            verifier_key_digest=self.trust.verifier_key_digest,
            verifier_public_key_base64=base64.b64encode(
                self.verifier.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            ).decode(),
            revocation_revision="synthetic-observed-empty-r1",
            revocation_digest=hash_canonical_payload(
                {"revoked": [], "checked_at": self.checked_at}
            ),
            checked_at=self.checked_at,
            admitted_at=utc_now(),
            expires_at=(datetime.fromisoformat(self.checked_at) + timedelta(minutes=5))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
        )
        wire["verifier_credential"] = base64.b64encode(
            self.verifier.sign(hash_canonical_payload(wire).encode())
        ).decode()
        return HistoricalPolicyVerification.model_validate(wire)


@contextmanager
def historical_provider(tmp_path, monkeypatch, mapping):
    provider = ObservedHistoricalProvider(mapping)
    state = {"calls": [], "responses": [], "failure": None}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            assert self.path == "/historical"
            assert self.headers["Authorization"] == "Bearer synthetic-provider-only"
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["calls"].append(request)
            if state["failure"] == "unavailable":
                self.send_response(503)
                self.end_headers()
                return
            result = provider.verify(HistoricalPolicyVerificationRequest.model_validate(request))
            wire = result.model_dump(mode="json")
            if state["failure"] == "signature":
                wire["verifier_credential"] = base64.b64encode(bytes(64)).decode()
            if state["failure"] == "revoked":
                wire["current_revocation_status"] = "REVOKED"
            raw = json.dumps(wire).encode()
            if state["failure"] == "duplicate":
                raw = raw[:-1] + b',"product_version":"v1"}'
            state["responses"].append(raw.decode())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    with trusted_https_server(Handler, tmp_path, monkeypatch) as server:
        configuration = HistoricalPolicyConfiguration(
            endpoint=f"https://127.0.0.1:{server.server_port}/historical",
            credential_env="SYNTHETIC_HISTORICAL_PROVIDER_AUTH",
            trust=provider.trust,
        )
        monkeypatch.setenv(configuration.credential_env, "synthetic-provider-only")
        try:
            yield configuration.model_dump_json(), state, provider
        finally:
            (tmp_path / "historical-provider-exchange.json").write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
