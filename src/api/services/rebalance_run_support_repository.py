from __future__ import annotations

from typing import cast

from src.core.common.postgres_errors import (
    postgres_connection_exception_types as common_postgres_connection_exception_types,
)
from src.core.rebalance_runs.repository import DpmRunRepository
from src.infrastructure.rebalance_runs import (
    PostgresDpmRunRepository,
)


def build_repository(dsn: str) -> DpmRunRepository:
    if not dsn:
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED")
    try:
        return cast(DpmRunRepository, PostgresDpmRunRepository(dsn=dsn))
    except RuntimeError:
        raise
    except postgres_connection_exception_types() as exc:
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED") from exc


def postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    return common_postgres_connection_exception_types()


__all__ = [
    "build_repository",
    "postgres_connection_exception_types",
    "PostgresDpmRunRepository",
]
