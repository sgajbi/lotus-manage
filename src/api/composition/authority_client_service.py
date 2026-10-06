from __future__ import annotations

from src.infrastructure.advise_authority import (
    LotusAdviseAuthorityClient,
    LotusAdviseAuthorityUnavailableError,
)
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
    LotusRiskAuthorityUnavailableError,
)

AdviseAuthorityClient = LotusAdviseAuthorityClient
AdviseAuthorityUnavailableError = LotusAdviseAuthorityUnavailableError
RiskAuthorityClient = LotusRiskAuthorityClient
RiskAuthorityUnavailableError = LotusRiskAuthorityUnavailableError

__all__ = [
    "AdviseAuthorityClient",
    "AdviseAuthorityUnavailableError",
    "RiskAuthorityClient",
    "RiskAuthorityUnavailableError",
]
