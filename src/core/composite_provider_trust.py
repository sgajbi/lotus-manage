"""Provider trust port: registration references do not establish source authority."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class CompositeProviderTrustRequest:
    tenant_id: str
    provider_id: str
    registry_revision: str
    registry_digest: str
    source_product: str
    effective_from: str
    effective_to: str


@dataclass(frozen=True)
class CompositeProviderTrustResolution:
    posture: Literal["UNAVAILABLE", "SYNTHETIC_TEST_ONLY"]
    reason_code: str
    registration_digest: str | None = None


class CompositeProviderTrustPort(Protocol):
    def resolve(self, request: CompositeProviderTrustRequest) -> CompositeProviderTrustResolution:
        """Resolve server-owned registration within exact tenant/product/time scope."""


class UnavailableCompositeProviderTrust:
    def resolve(self, request: CompositeProviderTrustRequest) -> CompositeProviderTrustResolution:
        return CompositeProviderTrustResolution(
            "UNAVAILABLE", "COMPOSITE_PROVIDER_TRUST_UNAVAILABLE"
        )
