"""Core-owned enterprise context HMAC-v1 wire representation."""

from collections.abc import Mapping
import hmac


def context_bytes(headers: Mapping[str, str]) -> bytes:
    normalized = {key.lower(): value.strip() for key, value in headers.items()}
    capabilities = sorted(
        {
            value.strip()
            for value in normalized.get("x-capabilities", "").split(",")
            if value.strip()
        }
    )
    canonical = "\n".join(
        (
            "lotus-enterprise-auth-context-v1",
            *(
                normalized.get(name, "")
                for name in (
                    "x-enterprise-auth-key-id",
                    "x-service-identity",
                    "x-actor-id",
                    "x-tenant-id",
                    "x-role",
                    "x-correlation-id",
                    "x-enterprise-auth-timestamp",
                )
            ),
            ",".join(capabilities),
        )
    )
    return canonical.encode("utf-8")


def context_signature(headers: Mapping[str, str], secret: str) -> str:
    return hmac.digest(secret.encode("utf-8"), context_bytes(headers), "sha256").hex()
