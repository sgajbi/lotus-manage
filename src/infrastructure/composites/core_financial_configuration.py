"""Closed deployment pins for the bounded, unverified native source preparation."""

from typing import Annotated, Literal, Self
from urllib.parse import urlsplit
import ipaddress

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

from src.core.composite_authority_models import Digest, Identity
from src.core.composite_eligibility.observations import Currency
from src.core.composite_eligibility.policy import month_window


def _opaque_identity(value: str) -> str:
    if value != value.strip() or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise ValueError("CORE_CUSTODY_IDENTITY_INVALID")
    return value


OpaqueIdentity = Annotated[
    str, Field(min_length=1, max_length=128), AfterValidator(_opaque_identity)
]


class ClosedSourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class CoreCutAddress(ClosedSourceModel):
    """Internal address, not a Core request DTO or an authorization grant."""

    source_system: OpaqueIdentity
    registry_scope_id: OpaqueIdentity
    source_cut_id: OpaqueIdentity
    revision: Annotated[StrictInt, Field(ge=1)]
    content_hash: Digest


class CoreMemberBinding(ClosedSourceModel):
    """Explicit provider mapping; native portfolio identities are never rewritten."""

    portfolio_id: Identity
    provider_namespace: OpaqueIdentity
    source_member_id: OpaqueIdentity
    provider_id: Identity
    financial_cut: CoreCutAddress


class CoreFinancialConfiguration(ClosedSourceModel):
    """No endpoint, key, credential, approval or qualification can be selected here."""

    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    strategy_code: Identity
    month: str
    reporting_currency: Currency
    registry: CoreCutAddress
    observation_cut_id: Identity
    observation_revision: Identity
    members: tuple[CoreMemberBinding, ...] = Field(max_length=1000)

    @field_validator("month")
    @classmethod
    def exact_month(cls, value: str) -> str:
        month_window(value)
        return value

    @model_validator(mode="after")
    def exact_member_mapping(self) -> Self:
        ids = [member.portfolio_id for member in self.members]
        keys = [(member.provider_namespace, member.source_member_id) for member in self.members]
        if ids != sorted(set(ids)) or len(set(keys)) != len(keys):
            raise ValueError("CORE_CUSTODY_MEMBER_MAPPING_AMBIGUOUS")
        return self


class CoreReaderConfiguration(ClosedSourceModel):
    """Dedicated deployment-only retained-read transport; it contains no trust enrollment."""

    tenant_id: Identity
    endpoint: str = Field(min_length=1, max_length=2048)
    credential_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    authentication_mode: Literal["bearer", "core_enterprise_hmac_v1"] = "bearer"
    allow_local_http: bool = False
    page_size: Annotated[StrictInt, Field(ge=1, le=500)] = 100
    attempts: Annotated[StrictInt, Field(ge=1, le=3)] = 1
    maximum_response_bytes: Annotated[StrictInt, Field(ge=1024, le=8_000_000)] = 2_000_000

    @model_validator(mode="after")
    def pinned_endpoint(self) -> Self:
        url = urlsplit(self.endpoint)
        if not url.hostname or any((url.username, url.password, url.query, url.fragment)):
            raise ValueError("CORE_READER_ENDPOINT_INVALID")
        local = False
        try:
            local = ipaddress.ip_address(url.hostname).is_loopback
        except ValueError:
            pass
        if url.scheme != "https" and not (url.scheme == "http" and local and self.allow_local_http):
            raise ValueError("CORE_READER_TLS_REQUIRED")
        if url.path not in ("", "/"):
            raise ValueError("CORE_READER_BASE_ENDPOINT_REQUIRED")
        return self
