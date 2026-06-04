from __future__ import annotations

import os

from src.core.rebalance_runs.repository import DpmRunRepository
from src.api.services import rebalance_run_support_repository
from src.api.services.service_config import env_csv_set, env_flag, env_int, env_non_negative_int


def artifact_store_mode() -> str:
    mode = os.getenv("DPM_ARTIFACT_STORE_MODE", "DERIVED").strip().upper()
    return "PERSISTED" if mode == "PERSISTED" else "DERIVED"


def supportability_store_backend_name() -> str:
    backend = os.getenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES").strip().upper()
    if backend != "POSTGRES":
        raise RuntimeError("DPM_SUPPORTABILITY_STORE_BACKEND_UNSUPPORTED")
    return backend


def supportability_postgres_dsn() -> str:
    return os.getenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "").strip()


def build_repository() -> DpmRunRepository:
    _ = supportability_store_backend_name()
    dsn = supportability_postgres_dsn()
    if not dsn:
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED")
    try:
        return rebalance_run_support_repository.build_repository(dsn=dsn)
    except rebalance_run_support_repository.postgres_connection_exception_types() as exc:
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED") from exc


def postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    return rebalance_run_support_repository.postgres_connection_exception_types()


def _postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    return postgres_connection_exception_types()


__all__ = [
    "artifact_store_mode",
    "DpmRunRepository",
    "build_repository",
    "env_csv_set",
    "env_flag",
    "env_int",
    "env_non_negative_int",
    "postgres_connection_exception_types",
    "supportability_postgres_dsn",
    "supportability_store_backend_name",
]
