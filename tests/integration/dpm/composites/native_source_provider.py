"""Synthetic retained-wire HTTP fixture, never a Core IAM or bank qualification claim.

Public A/C fixture bytes and handwritten observations are reused as data. The HTTP
handler checks the existing context protocol independently and records both readers.
"""

import base64
import hashlib
import hmac
import json
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.infrastructure.composites.native_assembly_configuration import NativeAssemblyConfiguration
from tests.integration.dpm.network_runtime import NativeCompositeRuntimeConfiguration
from tests.unit.dpm.infrastructure.test_core_source_reader import fixture, response
from tests.unit.dpm.infrastructure.test_controlled_assembly_verifier import expected_observations
from tests.unit.dpm.infrastructure.test_composite_configured_sources import signed
from tests.composite_staged_eligibility_helpers import synthetic_verification
from src.core.composite_eligibility.verification import VerificationRequest

MONTHLY_SEED = bytes(range(32))
POLICY_SEED = bytes(range(32, 64))
CAPABILITIES = (
    "source_data.portfolio_financial_source_cut.read",
    "source_data.portfolio_historical_registry.read",
)
CREDENTIALS = {
    "SYNTHETIC_NATIVE_ASSEMBLY_AUTH": "synthetic-assembly-only",
    "SYNTHETIC_NATIVE_VERIFICATION_AUTH": "synthetic-verification-only",
    "SYNTHETIC_NATIVE_POLICY_AUTH": "synthetic-policy-only",
}


def public_key(seed, kid):
    key = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes_raw()
    return {"kid": kid, "x": base64.urlsafe_b64encode(key).rstrip(b"=").decode()}


def deployment_material(key_file: Path, origin="https://core.test", *, now=None, policy=False):
    financial, records, roots = fixture()
    expected = expected_observations()
    instant = now or datetime.now(UTC)
    local = origin.startswith("http://")

    def reader(role):
        return {
            "tenant_id": "tenant",
            "endpoint": origin,
            "credential_env": f"SYNTHETIC_NATIVE_{role.upper()}_AUTH",
            "authentication_mode": "core_enterprise_hmac_v1",
            "allow_local_http": local,
            "page_size": 2,
            "attempts": 1,
        }

    def authorization(role):
        return {
            "tenant_id": "tenant",
            "origin": origin,
            "service_identity": "lotus-manage",
            "actor_id": "synthetic-" + role,
            "role": "DPM_SOURCE_READER",
            "key_id": "synthetic-" + role,
            "capabilities": list(CAPABILITIES),
            "credential_env": f"SYNTHETIC_NATIVE_{role.upper()}_AUTH",
            "allow_local_http": local,
        }

    expected_digest = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                expected.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )
    material = {
        "adapter": "CONTROLLED_SYNTHETIC_NATIVE_ASSEMBLY_V2",
        "financial": financial.model_dump(mode="json"),
        "reader": reader("assembly"),
        "assembly_authorization": authorization("assembly"),
        "verification_authorization": authorization("verification"),
        "verifier_key_file": str(key_file),
        "verification": {
            "financial": financial.model_dump(mode="json"),
            "reader": reader("verification"),
            "expected_observations_digest": expected_digest,
            "trust": {
                "tenant_id": "tenant",
                "issuer": "urn:synthetic:monthly:D",
                "receipt_issuer_id": "synthetic-monthly-receipt",
                "principal_id": "synthetic-monthly-verifier",
                "audience": "lotus-manage",
                "purpose": "COMPOSITE_MONTHLY_SOURCE_CUT",
                "operation": "verification",
                "evidence_posture": "SYNTHETIC_NON_CERTIFYING",
                "verifier_key": public_key(MONTHLY_SEED, "synthetic-monthly"),
                "key_valid_from": (instant - timedelta(minutes=1)).isoformat(),
                "key_valid_to": (instant + timedelta(minutes=10)).isoformat(),
                "source_principal_ids": ["synthetic-core-producer"],
                "source_keys": [],
            },
            "revocation": {
                "revision": "synthetic-current-r1",
                "checked_at": (instant - timedelta(seconds=1)).isoformat(),
                "expires_at": (instant + timedelta(seconds=299)).isoformat(),
                "revoked_credentials": [],
                "revoked_subjects": [],
                "revoked_key_digests": [],
            },
        },
    }
    if policy:
        material["policy_verification"] = {
            "bindings": [
                {
                    "operation": "verification",
                    "tenant_id": "tenant",
                    "owner_service": "fixture",
                    "endpoint": origin + "/policy",
                    "allow_local_http": local,
                    "issuer": "urn:synthetic:policy:D",
                    "receipt_issuer_id": "synthetic-fixture-issuer",
                    "principal_id": "synthetic-policy-verifier",
                    "credential_env": "SYNTHETIC_NATIVE_POLICY_AUTH",
                    "keys": [public_key(POLICY_SEED, "test-key")],
                    "evidence_posture": "SYNTHETIC_NON_CERTIFYING",
                    "verification_purposes": [
                        "ELIGIBILITY_POLICY",
                        "ELIGIBILITY_POLICY_EVALUATION",
                    ],
                }
            ]
        }
    return material, records, roots, expected


def _require_context(headers, path, state):
    role = headers.get("X-Actor-Id", "").removeprefix("synthetic-")
    if role not in {"assembly", "verification"} or "Authorization" in headers:
        raise ValueError("synthetic reader authority")
    if path not in {
        "/integration/portfolio-historical-registries/query",
        "/integration/financial-source-cuts/query",
    }:
        raise ValueError("synthetic reader target")
    fields = (
        "X-Enterprise-Auth-Key-Id",
        "X-Service-Identity",
        "X-Actor-Id",
        "X-Tenant-Id",
        "X-Role",
        "X-Correlation-Id",
        "X-Enterprise-Auth-Timestamp",
    )
    if any(
        len(headers.get_all(name, [])) != 1
        for name in (*fields, "X-Capabilities", "X-Enterprise-Auth-Signature")
    ):
        raise ValueError("synthetic duplicate authority")
    caps = ",".join(sorted(set(part.strip() for part in headers["X-Capabilities"].split(","))))
    if (headers[fields[0]], headers[fields[1]], headers[fields[3]], headers[fields[4]], caps) != (
        "synthetic-" + role,
        "lotus-manage",
        "tenant",
        "DPM_SOURCE_READER",
        ",".join(CAPABILITIES),
    ) or abs(int(time.time()) - int(headers[fields[-1]])) > 300:
        raise ValueError("synthetic context mismatch")
    context = "\n".join(
        ("lotus-enterprise-auth-context-v1", *(headers[name].strip() for name in fields), caps)
    ).encode("utf-8")
    secret = state["credentials"][f"SYNTHETIC_NATIVE_{role.upper()}_AUTH"]
    signature = hmac.digest(secret.encode("utf-8"), context, "sha256").hex()
    if not hmac.compare_digest(signature, headers["X-Enterprise-Auth-Signature"]):
        raise ValueError("synthetic signature mismatch")
    return role


@contextmanager
def native_source_provider(tmp_path):
    """Owned local listener and read-only synthetic signer; caller owns PG/API runtime."""
    state = {"calls": [], "deny": set(), "credentials": dict(CREDENTIALS), "redirect": False}
    records, roots, config = {}, {}, None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if self.path == "/policy":
                binding = config.policy_verification.bindings[0]
                if (
                    self.headers.get("Authorization")
                    != "Bearer " + CREDENTIALS[binding.credential_env]
                ):
                    self.send_error(403)
                    return
                request = json.loads(body)
                payload = synthetic_verification(
                    VerificationRequest.model_validate(request)
                ).model_dump(mode="json")
                payload["verifier_id"] = binding.principal_id
                key = Ed25519PrivateKey.from_private_bytes(POLICY_SEED)
                result = {
                    "owner_service": binding.owner_service,
                    "payload": payload,
                    "credential": signed(key, binding, request, payload),
                }
            else:
                try:
                    role = _require_context(self.headers, self.path, state)
                except (KeyError, ValueError):
                    self.send_error(403)
                    return
                state["calls"].append((role, self.path, json.loads(body)))
                if role in state["deny"]:
                    self.send_error(503)
                    return
                if state["redirect"]:
                    self.send_response(307)
                    self.send_header("Location", "/forbidden-redirect")
                    self.end_headers()
                    return
                result = response(
                    httpx.Request("POST", "http://fixture" + self.path, content=body),
                    records,
                    roots,
                )
            encoded = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    key_file = tmp_path / "synthetic-monthly-key.raw"
    key_file.write_bytes(MONTHLY_SEED)
    key_file.chmod(0o444)
    material, records, roots, expected = deployment_material(
        key_file, f"http://127.0.0.1:{server.server_port}", policy=True
    )
    config = NativeAssemblyConfiguration.model_validate_json(json.dumps(material))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield (
            NativeCompositeRuntimeConfiguration(config.model_dump_json(), dict(CREDENTIALS)),
            state,
            expected,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(10)
        key_file.chmod(0o600)
        assert not thread.is_alive()
