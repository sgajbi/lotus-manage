"""Opt-in ordinary Core execution context; Core owns route capability admission."""

from collections.abc import Callable, Generator, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import os
import time
from uuid import uuid4

import httpx

from src.infrastructure.core_context_signature import context_signature
from src.infrastructure.core_sourcing.errors import DpmCoreResolverError


class CoreExecutionError(DpmCoreResolverError):
    """Bounded refusal without caller/configuration/credential values."""


def context_value(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or len(value) > 128
        or not value.isascii()
        or not value.isprintable()
        or "," in value
        or "*" in value
    ):
        raise CoreExecutionError("INVALID_CORE_EXECUTION_CONTEXT")
    return value


def _scope(raw: str) -> tuple[str, ...]:
    values = json.loads(raw)
    if (
        not isinstance(values, list)
        or not values
        or len(values) > 128
        or any(not isinstance(value, str) for value in values)
    ):
        raise CoreExecutionError("INVALID_CORE_EXECUTION_SCOPE")
    admitted = tuple(sorted(context_value(value) for value in values))
    if len(set(admitted)) != len(admitted):
        raise CoreExecutionError("INVALID_CORE_EXECUTION_SCOPE")
    return admitted


def _origin(value: str) -> str:
    try:
        url = httpx.URL(value)
        invalid = (
            url.scheme not in {"http", "https"},
            not url.host,
            bool(url.userinfo),
            bool(url.query),
            bool(url.fragment),
            url.path != "/",
            any(ord(char) <= 32 or ord(char) == 127 for char in value),
            any(marker in value for marker in ("@", "#", "?", "\\")),
        )
        if any(invalid):
            raise ValueError
        return str(url).rstrip("/")
    except (httpx.InvalidURL, ValueError):
        raise CoreExecutionError("INVALID_CORE_EXECUTION_ORIGIN") from None


@dataclass(frozen=True)
class CoreExecutionPolicy:
    key_id: str
    service_identity: str
    actor_id: str
    role: str
    allowed_tenants: tuple[str, ...]
    capabilities: tuple[str, ...]
    qcp_origin: str
    query_origin: str

    @property
    def partition(self) -> str:
        return "ordinary-core:" + hashlib.sha256(repr(self).encode("utf-8")).hexdigest()


def load_core_execution_policy(
    base_url: str,
    query_base_url: str | None,
    *,
    environment: Mapping[str, str] | None = None,
) -> CoreExecutionPolicy | None:
    env = os.environ if environment is None else environment
    enabled = env.get("CORE_EXECUTION_ENABLED", "false").strip().lower()
    if enabled in {"false", "0"}:
        return None
    if enabled not in {"true", "1"}:
        raise CoreExecutionError("INVALID_CORE_EXECUTION_ENABLEMENT")
    try:
        secret = env["CORE_EXECUTION_SECRET"]
        if not secret or secret != secret.strip():
            raise ValueError
        qcp, query = _origin(base_url), _origin(query_base_url or "")
        if qcp == query:
            raise ValueError
        return CoreExecutionPolicy(
            key_id=context_value(env["CORE_EXECUTION_KEY_ID"]),
            service_identity=context_value(env["CORE_EXECUTION_SERVICE_IDENTITY"]),
            actor_id=context_value(env["CORE_EXECUTION_ACTOR_ID"]),
            role=context_value(env["CORE_EXECUTION_ROLE"]),
            allowed_tenants=_scope(env["CORE_EXECUTION_ALLOWED_TENANTS"]),
            capabilities=_scope(env["CORE_EXECUTION_CAPABILITIES"]),
            qcp_origin=qcp,
            query_origin=query,
        )
    except (KeyError, ValueError, TypeError, CoreExecutionError):
        raise CoreExecutionError("INVALID_CORE_EXECUTION_CONFIGURATION") from None


class OrdinaryCoreReadAuth(httpx.Auth):
    """Fresh request context; explicit query origin never receives HMAC credentials."""

    def __init__(
        self,
        policy: CoreExecutionPolicy,
        *,
        credential_resolver: Callable[[str], str | None] = os.getenv,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.policy = policy
        self._credential_resolver = credential_resolver
        self._clock = clock

    def validate_target(self, url: str) -> None:
        if (
            any(ord(char) <= 32 or ord(char) == 127 for char in url)
            or "\\" in url
            or "/../" in url
            or "/./" in url
            or "#" in url
        ):
            raise CoreExecutionError("CORE_EXECUTION_TARGET_REFUSED")

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        target = request.url
        origin = _origin(str(target.copy_with(path="/", query=None, fragment=None)))
        if (
            origin not in {self.policy.qcp_origin, self.policy.query_origin}
            or target.userinfo
            or target.fragment
            or request.method not in {"GET", "POST"}
            or b"%" in target.raw_path.split(b"?")[0]
            or "\\" in str(target)
        ):
            raise CoreExecutionError("CORE_EXECUTION_TARGET_REFUSED")
        headers = self._admitted_headers(request)
        if origin == self.policy.qcp_origin:
            headers.update(self._signed_headers(headers))
        request.headers.pop("Cookie", None)
        request.headers.update(headers)
        response = yield request
        if 300 <= response.status_code < 400:
            raise CoreExecutionError("CORE_EXECUTION_REDIRECT_REFUSED")

    def _admitted_headers(self, request: httpx.Request) -> dict[str, str]:
        for name in request.headers:
            if name in {
                "authorization",
                "proxy-authorization",
                "x-service-identity",
                "x-actor-id",
                "x-role",
                "x-capabilities",
                "x-caller-capabilities",
            } or name.startswith("x-enterprise-auth-"):
                raise CoreExecutionError("CORE_EXECUTION_CALLER_AUTHORITY_REFUSED")
            if (
                name in {"x-tenant-id", "x-correlation-id"}
                and len(request.headers.get_list(name)) != 1
            ):
                raise CoreExecutionError("CORE_EXECUTION_AMBIGUOUS_CONTEXT")
        tenant = context_value(request.headers.get("X-Tenant-Id", ""))
        if tenant not in self.policy.allowed_tenants:
            raise CoreExecutionError("CORE_EXECUTION_TENANT_REFUSED")
        return {
            "X-Tenant-Id": tenant,
            "X-Correlation-Id": context_value(
                request.headers.get("X-Correlation-Id") or uuid4().hex
            ),
        }

    def _signed_headers(self, admitted: dict[str, str]) -> dict[str, str]:
        try:
            now = self._clock()
            secret = self._credential_resolver("CORE_EXECUTION_SECRET")
            if (
                type(now) not in (int, float)
                or not math.isfinite(now)
                or now < 0
                or type(secret) is not str
                or not secret
                or secret != secret.strip()
            ):
                raise ValueError
            headers = {
                **admitted,
                "X-Enterprise-Auth-Key-Id": self.policy.key_id,
                "X-Service-Identity": self.policy.service_identity,
                "X-Actor-Id": self.policy.actor_id,
                "X-Role": self.policy.role,
                "X-Capabilities": ",".join(self.policy.capabilities),
                "X-Enterprise-Auth-Timestamp": str(int(now)),
            }
            headers["X-Enterprise-Auth-Signature"] = context_signature(headers, secret)
            return headers
        except Exception:
            raise CoreExecutionError("CORE_EXECUTION_CREDENTIAL_UNAVAILABLE") from None
