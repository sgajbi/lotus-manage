"""Existing Core context HMAC-v1 for explicitly configured retained reads.

Owning clients must use follow_redirects=False. Auth flows cannot prevent an
arbitrary client's internal redirects from forwarding custom context headers.
The signature binds context only, not the route/body, replay, grants or bank IAM.
"""

from collections.abc import Callable, Generator, Mapping
import hmac
import math
import os
import time
from typing import Annotated, Literal, Self
from uuid import uuid4

import httpx
from pydantic import AfterValidator, Field, TypeAdapter, field_validator, model_validator

from src.core.composite_authority_models import Identity
from src.infrastructure.composites.core_financial_configuration import (
    ClosedSourceModel,
    CoreReaderConfiguration,
)

CoreReadCapability = Literal[
    "source_data.portfolio_historical_registry.read",
    "source_data.portfolio_financial_source_cut.read",
]
_CAPABILITIES = frozenset(
    (
        "source_data.portfolio_historical_registry.read",
        "source_data.portfolio_financial_source_cut.read",
    )
)
_PATHS = frozenset(
    (
        b"/integration/portfolio-historical-registries/query",
        b"/integration/financial-source-cuts/query",
    )
)
_SIGNED_FIELDS = (
    "x-enterprise-auth-key-id",
    "x-service-identity",
    "x-actor-id",
    "x-tenant-id",
    "x-role",
    "x-correlation-id",
    "x-enterprise-auth-timestamp",
)
_AUTHORITY_HEADERS = frozenset(
    (
        *_SIGNED_FIELDS,
        "x-capabilities",
        "x-caller-capabilities",
        "x-enterprise-auth-signature",
        "authorization",
        "proxy-authorization",
    )
)


def _clean_identity(value: str) -> str:
    if value != value.strip() or not value.isascii() or not value.isprintable():
        raise ValueError("CORE_SOURCE_AUTH_IDENTITY_INVALID")
    return value


HeaderIdentity = Annotated[Identity, AfterValidator(_clean_identity)]


class CoreSourceAuthenticationPolicy(ClosedSourceModel):
    """Public ASCII transport assertions; credentials are only environment references."""

    origin: str = Field(min_length=1, max_length=2048)
    tenant_id: HeaderIdentity
    service_identity: Literal["lotus-manage"]
    actor_id: HeaderIdentity
    role: HeaderIdentity
    key_id: HeaderIdentity
    capabilities: tuple[CoreReadCapability, ...] = Field(min_length=2, max_length=2)
    credential_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    allow_local_http: bool = False

    @field_validator("capabilities")
    @classmethod
    def exact_read_capabilities(
        cls, value: tuple[CoreReadCapability, ...]
    ) -> tuple[CoreReadCapability, ...]:
        if frozenset(value) != _CAPABILITIES:
            raise ValueError("CORE_SOURCE_AUTH_CAPABILITIES_INVALID")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def pinned_origin(self) -> Self:
        CoreReaderConfiguration(
            tenant_id=self.tenant_id,
            endpoint=self.origin,
            credential_env=self.credential_env,
            authentication_mode="core_enterprise_hmac_v1",
            allow_local_http=self.allow_local_http,
        )
        try:
            httpx.URL(self.origin)
        except httpx.InvalidURL:
            raise ValueError("CORE_SOURCE_AUTH_ORIGIN_INVALID") from None
        return self


def _context_bytes(headers: Mapping[str, str]) -> bytes:
    """Core's exact nine LF-separated UTF-8 lines, without a trailing LF."""
    normalized = {str(key).lower(): str(value).strip() for key, value in headers.items()}
    capabilities = sorted(
        {part.strip() for part in normalized.get("x-capabilities", "").split(",") if part.strip()}
    )
    return "\n".join(
        (
            "lotus-enterprise-auth-context-v1",
            *(normalized.get(name, "") for name in _SIGNED_FIELDS),
            ",".join(capabilities),
        )
    ).encode("utf-8")


def _signature(headers: Mapping[str, str], secret: str) -> str:
    return hmac.digest(secret.encode("utf-8"), _context_bytes(headers), "sha256").hex()


def _policy(configuration: CoreSourceAuthenticationPolicy | None) -> CoreSourceAuthenticationPolicy:
    if configuration is None:
        raise ValueError("CORE_SOURCE_AUTH_POLICY_UNAVAILABLE")
    try:
        if set(configuration.__dict__) - set(CoreSourceAuthenticationPolicy.model_fields):
            raise ValueError
        return CoreSourceAuthenticationPolicy.model_validate_json(
            configuration.model_dump_json(warnings="error")
        )
    except (TypeError, ValueError):
        raise ValueError("CORE_SOURCE_AUTH_POLICY_INVALID") from None


def _require_target(request: httpx.Request, policy: CoreSourceAuthenticationPolicy) -> None:
    target, origin = request.url, httpx.URL(policy.origin)
    if (
        request.method != "POST"
        or (target.scheme, target.host, target.port) != (origin.scheme, origin.host, origin.port)
        or target.username
        or target.password
        or target.query
        or target.fragment
        or "#" in str(target)
        or target.raw_path not in _PATHS
    ):
        raise ValueError("CORE_SOURCE_AUTH_TARGET_FORBIDDEN")


def _require_owned_headers(request: httpx.Request, policy: CoreSourceAuthenticationPolicy) -> None:
    for name in request.headers:
        if name not in _AUTHORITY_HEADERS and not name.startswith("x-enterprise-auth-"):
            continue
        values = request.headers.get_list(name)
        if len(values) != 1:
            raise ValueError("CORE_SOURCE_AUTH_DUPLICATE_AUTHORITY")
        if name == "x-tenant-id":
            if values[0].strip() != policy.tenant_id:
                raise ValueError("CORE_SOURCE_AUTH_TENANT_MISMATCH")
        else:
            raise ValueError("CORE_SOURCE_AUTH_CALLER_AUTHORITY_FORBIDDEN")


def _new_correlation_id() -> str:
    return uuid4().hex


class CoreRetainedReadAuth(httpx.Auth):
    """Fresh context signing; D must separately enforce client follow_redirects=False."""

    def __init__(
        self,
        policy: CoreSourceAuthenticationPolicy | None,
        *,
        credential_resolver: Callable[[str], str | None] = os.getenv,
        clock: Callable[[], float] = time.time,
        correlation_id_factory: Callable[[], str] = _new_correlation_id,
    ) -> None:
        self._policy = policy
        self._credential_resolver = credential_resolver
        self._clock = clock
        self._correlation_id_factory = correlation_id_factory

    def _signed_headers(self, policy: CoreSourceAuthenticationPolicy) -> dict[str, str]:
        try:
            now = self._clock()
            if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
                raise ValueError
            correlation = TypeAdapter(HeaderIdentity).validate_python(
                self._correlation_id_factory(), strict=True
            )
        except Exception:
            raise ValueError("CORE_SOURCE_AUTH_CONTEXT_INVALID") from None
        headers = {
            "X-Enterprise-Auth-Key-Id": policy.key_id,
            "X-Service-Identity": policy.service_identity,
            "X-Actor-Id": policy.actor_id,
            "X-Tenant-Id": policy.tenant_id,
            "X-Role": policy.role,
            "X-Correlation-Id": correlation,
            "X-Enterprise-Auth-Timestamp": str(int(now)),
            "X-Capabilities": ",".join(policy.capabilities),
        }
        try:
            secret = self._credential_resolver(policy.credential_env)
            if type(secret) is not str or not secret or secret != secret.strip():
                raise ValueError
            headers["X-Enterprise-Auth-Signature"] = _signature(headers, secret)
        except Exception:
            raise ValueError("CORE_SOURCE_AUTH_CREDENTIAL_UNAVAILABLE") from None
        return headers

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        policy = _policy(self._policy)
        _require_target(request, policy)
        _require_owned_headers(request, policy)
        # HTTPX has merged pooled defaults and cookies into this request.
        request.headers.pop("Cookie", None)
        request.headers.update(self._signed_headers(policy))
        response = yield request
        if 300 <= response.status_code < 400:
            raise ValueError("CORE_SOURCE_AUTH_REDIRECT_REFUSED")
