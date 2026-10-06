from __future__ import annotations

from src.api.composition import authority_client_service
from src.api.composition.authority_client_service import (
    AdviseAuthorityClient,
    AdviseAuthorityUnavailableError,
    RiskAuthorityClient,
    RiskAuthorityUnavailableError,
)
from src.infrastructure.advise_authority import (
    LotusAdviseAuthorityClient,
    LotusAdviseAuthorityUnavailableError,
)
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
    LotusRiskAuthorityUnavailableError,
)
from src.core import integration_ports
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError


def test_authority_client_service_exports_aliases() -> None:
    assert AdviseAuthorityClient is LotusAdviseAuthorityClient
    assert AdviseAuthorityUnavailableError is LotusAdviseAuthorityUnavailableError
    assert RiskAuthorityClient is LotusRiskAuthorityClient
    assert RiskAuthorityUnavailableError is LotusRiskAuthorityUnavailableError
    assert authority_client_service.__all__ == [
        "AdviseAuthorityClient",
        "AdviseAuthorityUnavailableError",
        "RiskAuthorityClient",
        "RiskAuthorityUnavailableError",
    ]


def test_domain_errors_retain_adapter_exception_identity() -> None:
    assert integration_ports.AdviseAuthorityUnavailableError is LotusAdviseAuthorityUnavailableError
    assert integration_ports.RiskAuthorityUnavailableError is LotusRiskAuthorityUnavailableError
    assert integration_ports.CoreResolverError is DpmCoreResolverError
    assert integration_ports.CoreResolverUnavailableError is DpmCoreResolverUnavailableError
    assert issubclass(
        integration_ports.CoreResolverUnavailableError, integration_ports.CoreResolverError
    )
