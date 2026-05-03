from typing import AsyncIterator

from src.core.mandate_repository import DpmMandateRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository


_MANDATE_REPOSITORY = InMemoryDpmMandateRepository()


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
