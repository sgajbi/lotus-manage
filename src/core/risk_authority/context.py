"""Credential-free, immutable context for the local Risk consumer pilot."""

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.common.canonical import hash_canonical_payload

RiskAuthorityOperation = Literal["concentration", "regime_scenario", "risk_event_cohort"]


class RiskAuthorityGrant(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    operation: RiskAuthorityOperation
    capability: str = Field(min_length=1)

    @field_validator("capability")
    @classmethod
    def valid_capability(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", value):
            raise ValueError("Risk capability must be an explicit single policy token")
        return value


class RiskAuthorityContext(BaseModel):
    """Admitted local claims, not a verified principal or revocable bank grant."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    authority_basis: Literal["caller_asserted_header_trust"] = "caller_asserted_header_trust"
    actor_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    service_identity: str = Field(min_length=1)
    policy_fingerprint: str = Field(min_length=1)
    grants: tuple[RiskAuthorityGrant, ...] = ()

    @field_validator("actor_id", "tenant_id", "role", "correlation_id", "service_identity")
    @classmethod
    def valid_identity(cls, value: str) -> str:
        if (
            value != value.strip()
            or not value.isascii()
            or not value.isprintable()
            or value.lower() in {"unknown", "default"}
        ):
            raise ValueError("Risk authority requires actual non-placeholder admission claims")
        return value

    def fingerprint(self) -> str:
        return hash_canonical_payload(self.model_dump(mode="json"))


class RiskAuthorityPolicy(BaseModel):
    """Deployment-owned operation mapping; no default capabilities or identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    service_identity: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    grants: tuple[RiskAuthorityGrant, ...]

    @model_validator(mode="after")
    def complete_mapping(self) -> Self:
        if len(self.grants) != 3 or {grant.operation for grant in self.grants} != {
            "concentration",
            "regime_scenario",
            "risk_event_cohort",
        }:
            raise ValueError("Risk policy must map every protected operation exactly once")
        return self

    def fingerprint(self) -> str:
        return hash_canonical_payload(self.model_dump(mode="json"))

    def headers(
        self,
        *,
        context: RiskAuthorityContext | None,
        operation: RiskAuthorityOperation,
        correlation_id: str | None,
    ) -> dict[str, str]:
        if context is None or context.policy_fingerprint != self.fingerprint():
            raise ValueError("LOTUS_RISK_AUTHORITY_CONTEXT_UNAVAILABLE")
        grant = next((grant for grant in self.grants if grant.operation == operation), None)
        if grant is None or grant not in context.grants:
            raise ValueError("LOTUS_RISK_AUTHORITY_CAPABILITY_DENIED")
        if context.service_identity != self.service_identity or not correlation_id:
            raise ValueError("LOTUS_RISK_AUTHORITY_CONTEXT_INVALID")
        return {
            "X-Actor-Id": context.actor_id,
            "X-Tenant-Id": context.tenant_id,
            "X-Role": context.role,
            "X-Correlation-Id": correlation_id,
            "X-Service-Identity": self.service_identity,
            "X-Capabilities": grant.capability,
        }
