import os

from fastapi import HTTPException, status

from src.core.common.capabilities import psycopg_error_type


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def assert_feature_enabled(*, name: str, default: bool, detail: str) -> None:
    if not env_flag(name, default):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


def normalize_backend_init_error(*, detail: str, required_detail: str, fallback_detail: str) -> str:
    if detail == required_detail:
        return detail
    return fallback_detail


def postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [
        ConnectionError,
        OSError,
        TimeoutError,
        TypeError,
        ValueError,
    ]
    error_type = psycopg_error_type()
    if error_type is not None:
        types.append(error_type)
    return tuple(types)
