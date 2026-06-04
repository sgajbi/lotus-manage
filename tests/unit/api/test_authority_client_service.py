from __future__ import annotations

from src.api.services import authority_client_service
from src.api.services.authority_client_service import (
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
