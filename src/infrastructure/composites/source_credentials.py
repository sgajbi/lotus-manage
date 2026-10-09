"""Platform principal-credential Ed25519 wire verification for synthetic sources.

Uses the governed compact JWS, pinned OKP/Ed25519 JWKS and refusal order from
lotus-platform/platform-contracts/principal-credential. This boundary binds an
artifact to a service credential; it does not resolve a bank principal or grant.
Deployment bindings are limited to synthetic non-certifying evidence.
"""

import base64
import binascii
import json
import time
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.core.common.canonical import hash_canonical_payload
from src.infrastructure.composites.source_configuration import SourceBinding


def _decode(segment: str) -> bytes:
    return base64.b64decode(segment + "=" * (-len(segment) % 4), altchars=b"-_", validate=True)


def _trusted_key(header: Any, binding: SourceBinding) -> Ed25519PublicKey:
    if not isinstance(header, dict) or header.get("alg") != "EdDSA":
        raise ValueError("malformed_credential")
    if set(header) - {"alg", "kid", "typ"}:
        raise ValueError("malformed_credential")
    key = next(
        (key for key in binding.keys if key.kid == header.get("kid") and not key.revoked), None
    )
    if key is None:
        raise ValueError("unknown_key_id")
    return Ed25519PublicKey.from_public_bytes(_decode(key.x))


def _verified_claims(credential: str, binding: SourceBinding) -> dict[str, Any]:
    try:
        parts = credential.split(".")
        if len(parts) != 3 or not all(parts):
            raise ValueError("malformed_credential")
        header = json.loads(_decode(parts[0]))
        _trusted_key(header, binding).verify(
            _decode(parts[2]), f"{parts[0]}.{parts[1]}".encode("ascii")
        )
        claims = json.loads(_decode(parts[1]))
        if not isinstance(claims, dict):
            raise ValueError("malformed_credential")
    except InvalidSignature as exc:
        raise ValueError("present_but_unverified") from exc
    except (binascii.Error, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("malformed_credential") from exc
    return claims


def _require_issuer_and_audience(claims: dict[str, Any], binding: SourceBinding) -> None:
    if claims.get("iss") != binding.issuer:
        raise ValueError("wrong_issuer")
    audience = claims.get("aud")
    if audience != "lotus-manage" and not (
        isinstance(audience, list)
        and "lotus-manage" in audience
        and all(isinstance(item, str) for item in audience)
    ):
        raise ValueError("wrong_audience")


def _require_current_window(claims: dict[str, Any], current: float) -> None:
    expiry, start = claims.get("exp"), claims.get("nbf", 0)
    if type(expiry) is not int or type(start) is not int or current >= expiry or current < start:
        raise ValueError("expired_credential")


def _require_bound_principal(claims: dict[str, Any], binding: SourceBinding) -> None:
    if (
        claims.get("jti") in binding.revoked_credentials
        or claims.get("sub") in binding.revoked_subjects
    ):
        raise ValueError("revoked_principal")
    if not isinstance(claims.get("jti"), str) or not claims["jti"]:
        raise ValueError("malformed_credential")
    if (claims.get("sub"), claims.get("tenant"), claims.get("principal_kind")) != (
        binding.principal_id,
        binding.tenant_id,
        "service",
    ) or "act" in claims:
        raise ValueError("COMPOSITE_SOURCE_PRINCIPAL_MISMATCH")


def verified_artifact(
    credential: str,
    *,
    binding: SourceBinding,
    request: dict[str, Any],
    payload: dict[str, Any],
    now: float | None = None,
) -> None:
    """Verify signed bytes before inspecting claims; never trust a nominated keyset."""
    claims = _verified_claims(credential, binding)
    _require_issuer_and_audience(claims, binding)
    _require_current_window(claims, time.time() if now is None else now)
    _require_bound_principal(claims, binding)
    if (
        claims.get("operation"),
        claims.get("request_digest"),
        claims.get("payload_digest"),
        claims.get("evidence_posture"),
    ) != (
        binding.operation,
        hash_canonical_payload(request),
        hash_canonical_payload(payload),
        binding.evidence_posture,
    ):
        raise ValueError("COMPOSITE_SOURCE_ARTIFACT_BINDING_MISMATCH")
