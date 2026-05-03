import os
from typing import AsyncIterator

from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient, LotusRiskAuthorityConfig


_MANDATE_REPOSITORY = InMemoryDpmMandateRepository()
_CONSTRUCTION_REPOSITORY = InMemoryConstructionRepository()


async def get_db_session() -> AsyncIterator[None]:
    """Stub for Database Session (RFC-0005). To be replaced with actual AsyncPG session."""
    yield None


def get_mandate_repository() -> DpmMandateRepository:
    """Return the mandate repository used by RFC-0038 APIs.

    The default local profile is in-memory so the API remains usable in developer and test
    runtimes. Production wiring can replace this dependency with the Postgres-backed repository
    once the deployment profile injects a managed connection provider.
    """

    return _MANDATE_REPOSITORY


def get_construction_repository() -> ConstructionRepository:
    """Return the RFC-0039 construction repository for local and test runtimes."""

    return _CONSTRUCTION_REPOSITORY


def get_risk_authority_client() -> LotusRiskAuthorityClient | None:
    """Return a lotus-risk authority client when risk integration is configured."""

    base_url = os.getenv("DPM_RISK_BASE_URL", "").strip()
    if not base_url:
        return None
    return LotusRiskAuthorityClient(config=LotusRiskAuthorityConfig(base_url=base_url))
