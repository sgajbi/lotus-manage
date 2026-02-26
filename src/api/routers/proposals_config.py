import os
from typing import cast

from src.core.proposals.repository import ProposalRepository
from src.infrastructure.proposals import PostgresProposalRepository


def proposal_store_backend_name() -> str:
    backend = os.getenv("PROPOSAL_STORE_BACKEND", "POSTGRES").strip().upper()
    if backend != "POSTGRES":
        raise RuntimeError("PROPOSAL_STORE_BACKEND_UNSUPPORTED")
    return backend


def proposal_postgres_dsn() -> str:
    return os.getenv("PROPOSAL_POSTGRES_DSN", "").strip()


def _postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [
        ConnectionError,
        OSError,
        TimeoutError,
        TypeError,
        ValueError,
    ]
    try:
        import psycopg
    except ImportError:
        pass
    else:
        types.append(psycopg.Error)
    return tuple(types)


def build_repository() -> ProposalRepository:
    _ = proposal_store_backend_name()
    dsn = proposal_postgres_dsn()
    if not dsn:
        raise RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")
    try:
        return cast(ProposalRepository, PostgresProposalRepository(dsn=dsn))
    except RuntimeError:
        raise
    except _postgres_connection_exception_types() as exc:
        raise RuntimeError("PROPOSAL_POSTGRES_CONNECTION_FAILED") from exc
