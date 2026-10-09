"""Deployment-enrolled Composite readers; trusted ingress assertions, not bank IAM."""

import json
import os
import re
from collections.abc import Mapping

READ_ROLE = "REPORT_COMPOSITE_READER"
READ_CAPABILITY = "manage.read"
GRANTS_ENV = "DPM_COMPOSITE_READ_SERVICE_GRANTS_JSON"
_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}"
_ROOT = r"/api/v1/rebalance/composites/"
_DEFINITION = _ROOT + _SEGMENT + r"/definitions/" + _SEGMENT
_RESOLVER = re.compile(_DEFINITION + r"/eligibility-evidence/resolve")
_READ_PATHS = tuple(
    re.compile(pattern)
    for pattern in (
        _DEFINITION + r"/membership/" + _SEGMENT,
        _DEFINITION + r"/membership/" + _SEGMENT + r"/universe-attestations/" + _SEGMENT,
        _DEFINITION + r"/monthly-eligibility/evaluations/" + _SEGMENT,
        _ROOT + r"publications/[1-9][0-9]*",
    )
)
IDENTITY_HEADERS = (
    "x-service-identity",
    "x-actor-id",
    "x-tenant-id",
    "x-role",
    "x-capabilities",
    "x-correlation-id",
)


def _single_assertion(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not any(char.isspace() or char == "," for char in value)
    )


def _grants() -> list[dict[str, str]]:
    try:
        grants = json.loads(os.getenv(GRANTS_ENV, "[]"))
    except json.JSONDecodeError:
        return []
    keys = {"service_identity", "actor_id", "tenant_id"}
    if not isinstance(grants, list) or any(
        not isinstance(grant, dict)
        or set(grant) != keys
        or not all(_single_assertion(value) for value in grant.values())
        for grant in grants
    ):
        return []
    identities = [grant["service_identity"] for grant in grants]
    return grants if len(set(identities)) == len(identities) else []


def is_composite_read_service(headers: Mapping[str, str]) -> bool:
    """Recognize malformed asserted reader roles/known identities before admission."""
    roles = {part.strip() for part in headers.get("x-role", "").split(",")}
    identities = {part.strip() for part in headers.get("x-service-identity", "").split(",")}
    return READ_ROLE in roles or bool(
        identities.intersection(grant["service_identity"] for grant in _grants())
    )


def composite_read_failure(method: str, path: str, headers: Mapping[str, str]) -> str | None:
    if any(not _single_assertion(headers.get(name)) for name in IDENTITY_HEADERS):
        return "composite_read_identity_required"
    if headers["x-role"] != READ_ROLE:
        return "composite_read_role_forbidden"
    if headers["x-capabilities"] != READ_CAPABILITY:
        return "composite_read_capability_required"
    if not any(
        headers["x-service-identity"] == grant["service_identity"]
        and headers["x-actor-id"] == grant["actor_id"]
        and headers["x-tenant-id"] == grant["tenant_id"]
        for grant in _grants()
    ):
        return "composite_read_service_grant_required"
    if method == "POST" and _RESOLVER.fullmatch(path):
        return None
    if method == "GET" and any(pattern.fullmatch(path) for pattern in _READ_PATHS):
        return None
    return "composite_read_operation_forbidden"
