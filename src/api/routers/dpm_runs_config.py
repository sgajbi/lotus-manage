import os
from typing import cast

from src.core.dpm_runs.repository import DpmRunRepository
from src.infrastructure.dpm_runs import (
    PostgresDpmRunRepository,
)


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 1 else default


def env_non_negative_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


def env_csv_set(name: str, default: set[str]) -> set[str]:
    value = os.getenv(name)
    if value is None:
        return set(default)
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    return parsed or set(default)


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


def build_repository() -> DpmRunRepository:
    _ = supportability_store_backend_name()
    dsn = supportability_postgres_dsn()
    if not dsn:
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED")
    try:
        return cast(DpmRunRepository, PostgresDpmRunRepository(dsn=dsn))
    except RuntimeError:
        raise
    except _postgres_connection_exception_types() as exc:
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED") from exc
